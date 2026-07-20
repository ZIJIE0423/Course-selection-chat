import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agent.course_planning_agent import CoursePlanningAgent
from app.models.planning import (
    AcademicHistoryRecord,
    CourseOffering,
    CourseOfferingSnapshot,
    PlanningSession,
    ProgrammeRule,
    ProgrammeVersion,
)
from app.schemas.planning import (
    ParsedRequirements,
    PlanningConfirmRequest,
    PlanningSessionCreate,
    RecommendationCard,
    RecommendationResponse,
    RequirementItem,
)


class PlanningValidationError(ValueError):
    pass


EVIDENCE_MAX_AGE_DAYS = 180


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _age_days(value: datetime) -> int:
    return max(0, (datetime.now(timezone.utc) - _as_utc(value)).days)


def _offering_evidence(snapshot: CourseOfferingSnapshot, offering: CourseOffering) -> dict:
    """Build a machine-readable evidence record for a recommendation card.

    M1 only permits recommendations based on the structured offering snapshot.
    Missing timestamps are exposed as incomplete evidence instead of being
    silently treated as current data.
    """
    reference_time = offering.source_updated_at or snapshot.generated_at
    age_days = _age_days(reference_time)
    completeness = "complete" if offering.source_updated_at else "partial"
    freshness = "current" if age_days <= EVIDENCE_MAX_AGE_DAYS else "stale"
    return {
        "type": "course_offering_snapshot",
        "source_tier": "official_structured_snapshot",
        "snapshot_id": snapshot.external_snapshot_id,
        "semester": snapshot.semester,
        "generated_at": snapshot.generated_at.isoformat(),
        "source_updated_at": (
            offering.source_updated_at.isoformat() if offering.source_updated_at else None
        ),
        "field_completeness": completeness,
        "freshness": freshness,
        "age_days": age_days,
        "conflict_status": "not_detected",
    }


def _required_offering_fields(constraints: list[RequirementItem]) -> set[str]:
    """Return fields that must be present before a recommendation is safe.

    Capacity and source time are baseline evidence: without them the service
    cannot establish that a displayed section is currently selectable.  Other
    fields become mandatory when the user made them a hard constraint.
    """
    required = {"course_code", "course_name", "remaining_capacity", "source_updated_at"}
    for item in constraints:
        if item.type in {"campus", "course_category", "teacher_name", "credits"}:
            required.add(item.type)
        elif item.type in {"weekday", "avoid_period"}:
            required.add("schedule_json")
    return required


def _missing_evidence_fields(
    offering: CourseOffering,
    required_fields: set[str],
) -> list[str]:
    missing = []
    for field in sorted(required_fields):
        value = getattr(offering, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def _validate_recommendation_evidence(
    db: Session,
    snapshot: CourseOfferingSnapshot,
    offerings: list[CourseOffering],
    constraints: list[RequirementItem],
) -> None:
    """Fail closed when active structured evidence cannot support planning.

    This gate intentionally rejects the whole request rather than silently
    dropping questionable rows.  A partial candidate set would make a hard
    constraint look satisfied while hiding courses whose evidence is unsafe.
    """
    active_snapshot_count = (
        db.query(CourseOfferingSnapshot)
        .filter(
            CourseOfferingSnapshot.tenant_id == snapshot.tenant_id,
            CourseOfferingSnapshot.semester == snapshot.semester,
            CourseOfferingSnapshot.status == "active",
        )
        .count()
    )
    if active_snapshot_count != 1:
        raise PlanningValidationError("证据冲突：同一学期存在多个活动开课快照，已拒绝生成推荐")
    if _age_days(snapshot.generated_at) > EVIDENCE_MAX_AGE_DAYS:
        raise PlanningValidationError("证据已过期：活动开课快照超过 180 天，已拒绝生成推荐")

    required_fields = _required_offering_fields(constraints)
    seen_signatures: set[tuple[str, str, str, str]] = set()
    for offering in offerings:
        if offering.source_updated_at is None:
            raise PlanningValidationError(
                f"证据关键字段缺失：课程 {offering.course_code} 未提供 source_updated_at，已拒绝生成推荐"
            )
        if _age_days(offering.source_updated_at) > EVIDENCE_MAX_AGE_DAYS:
            raise PlanningValidationError(
                f"证据已过期：课程 {offering.course_code} 的来源更新时间超过 180 天，已拒绝生成推荐"
            )
        missing_fields = _missing_evidence_fields(offering, required_fields)
        if missing_fields:
            raise PlanningValidationError(
                f"证据关键字段缺失：课程 {offering.course_code} 缺少 {', '.join(missing_fields)}，已拒绝生成推荐"
            )
        signature = (
            offering.course_code,
            offering.teacher_name or "",
            offering.campus or "",
            offering.schedule_json or "[]",
        )
        if signature in seen_signatures:
            raise PlanningValidationError(
                f"证据存在多条歧义记录：课程 {offering.course_code} 的班次信息无法唯一确定，已拒绝生成推荐"
            )
        seen_signatures.add(signature)


def create_planning_session(
    db: Session,
    payload: PlanningSessionCreate,
) -> tuple[PlanningSession, ParsedRequirements]:
    snapshot = db.query(CourseOfferingSnapshot).filter(
        CourseOfferingSnapshot.id == payload.snapshot_id,
        CourseOfferingSnapshot.tenant_id == payload.tenant_id,
        CourseOfferingSnapshot.status == "active",
    ).first()
    if not snapshot:
        raise PlanningValidationError("Active course offering snapshot not found")

    if payload.programme_version_id is not None:
        programme = db.query(ProgrammeVersion).filter(
            ProgrammeVersion.id == payload.programme_version_id,
            ProgrammeVersion.tenant_id == payload.tenant_id,
            ProgrammeVersion.status == "active",
        ).first()
        if not programme:
            raise PlanningValidationError("Active programme version not found")

    requirements = CoursePlanningAgent().parse(
        db,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        query=payload.query,
        has_programme=payload.programme_version_id is not None,
    )
    state_by_action = {
        "confirm_requirements": "awaiting_confirmation",
        "confirm_history": "awaiting_history_confirmation",
        "clarify": "awaiting_clarification",
        "execute": "ready",
        "reject": "rejected",
    }
    session = PlanningSession(
        id=str(uuid.uuid4()),
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        snapshot_id=payload.snapshot_id,
        programme_version_id=payload.programme_version_id,
        raw_query=payload.query,
        requirements_json=requirements.model_dump_json(),
        state=state_by_action[requirements.next_action],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, requirements


def _contains(actual: str | None, expected) -> bool:
    return str(expected).lower() in (actual or "").lower()


def _schedule_has_weekday(schedules: list[dict], weekday: int) -> bool:
    return any(slot.get("weekday") == weekday for slot in schedules)


def _schedule_has_period(schedules: list[dict], period: int) -> bool:
    return any(period in (slot.get("periods") or []) for slot in schedules)


def _matches_constraint(offering: CourseOffering, schedules: list[dict], item: RequirementItem) -> bool:
    if item.type == "campus":
        return _contains(offering.campus, item.value)
    if item.type == "course_category":
        return _contains(offering.course_category, item.value)
    if item.type == "teacher_name":
        return _contains(offering.teacher_name, item.value)
    if item.type == "weekday":
        return _schedule_has_weekday(schedules, int(item.value))
    if item.type == "course_code":
        return offering.course_code == str(item.value)
    if item.type == "credits":
        if offering.credits is None:
            return False
        if item.operator == "lte":
            return offering.credits <= float(item.value)
        if item.operator == "gte":
            return offering.credits >= float(item.value)
        return offering.credits == float(item.value)
    if item.type == "avoid_period":
        return not _schedule_has_period(schedules, int(item.value))
    raise PlanningValidationError(f"Unsupported confirmed constraint type: {item.type}")


def _preference_score(
    offering: CourseOffering,
    schedules: list[dict],
    item: RequirementItem,
) -> tuple[float, str | None]:
    if item.type == "avoid_period":
        matched = not _schedule_has_period(schedules, int(item.value))
        return (8.0 if matched else 0.0, "避开不希望的时间段" if matched else None)
    if item.type in {"campus", "course_category", "teacher_name", "weekday", "credits"}:
        matched = _matches_constraint(offering, schedules, item)
        return (5.0 if matched else 0.0, f"符合偏好：{item.type}" if matched else None)
    return 0.0, None


def recommend_courses(
    db: Session,
    session: PlanningSession,
    payload: PlanningConfirmRequest,
) -> RecommendationResponse:
    if session.state not in {"awaiting_confirmation", "ready", "completed"}:
        raise PlanningValidationError(f"Planning session cannot execute from state '{session.state}'")

    snapshot = db.query(CourseOfferingSnapshot).filter(
        CourseOfferingSnapshot.id == session.snapshot_id,
        CourseOfferingSnapshot.tenant_id == session.tenant_id,
        CourseOfferingSnapshot.status == "active",
    ).first()
    if not snapshot:
        raise PlanningValidationError("Course offering snapshot is no longer active")

    completed_records = db.query(AcademicHistoryRecord).filter(
        AcademicHistoryRecord.tenant_id == session.tenant_id,
        AcademicHistoryRecord.user_id == session.user_id,
        AcademicHistoryRecord.completion_status.in_(["assumed_passed", "passed"]),
    ).all()
    completed_codes = {record.course_code for record in completed_records if record.course_code}
    completed_names = {record.course_name.strip().lower() for record in completed_records}

    rules = []
    if session.programme_version_id:
        rules = db.query(ProgrammeRule).filter(
            ProgrammeRule.programme_version_id == session.programme_version_id
        ).all()
    required_codes = {rule.course_code for rule in rules if rule.rule_type == "required" and rule.course_code}
    pool_codes = {
        rule.course_code for rule in rules if rule.rule_type == "elective_pool" and rule.course_code
    }
    pool_categories = {
        rule.course_category
        for rule in rules
        if rule.rule_type == "elective_pool" and rule.course_category
    }

    warnings = []
    if session.programme_version_id and not rules:
        warnings.append("该培养方案尚无结构化规则，结果仅按已修课程和已确认条件筛选")
    if session.programme_version_id and rules and not (pool_codes or pool_categories):
        warnings.append("培养方案没有配置选修池规则，未对非必修课程做方案范围裁剪")

    previous = ParsedRequirements.model_validate_json(session.requirements_json)
    for unsupported in previous.unsupported_preferences:
        warnings.append(f"第一阶段未启用 {unsupported} 数据，未将该偏好用于排序")

    offerings = db.query(CourseOffering).filter(
        CourseOffering.snapshot_id == session.snapshot_id
    ).all()
    _validate_recommendation_evidence(db, snapshot, offerings, payload.constraints)
    cards: list[RecommendationCard] = []
    for offering in offerings:
        if offering.course_code in completed_codes or offering.course_name.strip().lower() in completed_names:
            continue
        if offering.remaining_capacity is not None and offering.remaining_capacity <= 0:
            continue
        if pool_codes or pool_categories:
            in_programme_scope = (
                offering.course_code in required_codes
                or offering.course_code in pool_codes
                or offering.course_category in pool_categories
            )
            if not in_programme_scope:
                continue

        try:
            schedules = json.loads(offering.schedule_json or "[]")
        except (TypeError, json.JSONDecodeError):
            schedules = []
        if not isinstance(schedules, list):
            schedules = []
        if not all(_matches_constraint(offering, schedules, item) for item in payload.constraints):
            continue

        score = 0.0
        reasons = ["未在已修课程中"]
        if offering.course_code in required_codes:
            score += 100.0
            reasons.append("培养方案中的未完成必修课程")
        elif offering.course_code in pool_codes or offering.course_category in pool_categories:
            score += 20.0
            reasons.append("属于培养方案允许的选修范围")
        if offering.remaining_capacity is not None:
            score += min(10.0, offering.remaining_capacity / 10.0)
            reasons.append("当前仍有余量")
        for preference in payload.preferences:
            preference_score, reason = _preference_score(offering, schedules, preference)
            score += preference_score
            if reason:
                reasons.append(reason)

        card_warnings = []
        evidence = _offering_evidence(snapshot, offering)
        cards.append(
            RecommendationCard(
                offering_id=offering.id,
                course_code=offering.course_code,
                course_name=offering.course_name,
                credits=offering.credits,
                course_category=offering.course_category,
                campus=offering.campus,
                teacher_name=offering.teacher_name,
                schedules=schedules,
                score=round(score, 2),
                match_reasons=reasons,
                warnings=card_warnings,
                evidence=[evidence],
            )
        )

    cards.sort(key=lambda card: (-card.score, card.course_code, card.offering_id))
    confirmed_requirements = previous.model_copy(
        update={
            "constraints": payload.constraints,
            "preferences": payload.preferences,
            "next_action": "execute",
        }
    )
    session.requirements_json = confirmed_requirements.model_dump_json()
    session.state = "completed"
    db.commit()
    return RecommendationResponse(
        planning_session_id=session.id,
        snapshot_id=session.snapshot_id,
        total_candidates=len(cards),
        recommendations=cards[:20],
        warnings=warnings,
    )
