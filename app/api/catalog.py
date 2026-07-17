import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.mysql import get_db
from app.models.course import Course
from app.models.planning import (
    AcademicHistoryRecord,
    CourseOffering,
    CourseOfferingSnapshot,
    ProgrammeRule,
    ProgrammeVersion,
    StudentProfile,
)

router = APIRouter()


def _json_value(raw: str | None, fallback):
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return fallback


@router.get("/offerings/{offering_id}")
def get_course_offering_detail(
    offering_id: int,
    tenant_id: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
):
    result = (
        db.query(CourseOffering, CourseOfferingSnapshot)
        .join(CourseOfferingSnapshot, CourseOffering.snapshot_id == CourseOfferingSnapshot.id)
        .filter(
            CourseOffering.id == offering_id,
            CourseOfferingSnapshot.tenant_id == tenant_id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Course offering not found")
    offering, snapshot = result
    canonical = (
        db.query(Course).filter(Course.id == offering.course_id).first()
        if offering.course_id
        else None
    )

    programme = None
    relationship = {"type": "unbound", "label": "尚未绑定培养方案", "matched_rule": None}
    if user_id:
        profile = (
            db.query(StudentProfile)
            .filter(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.user_id == user_id,
            )
            .first()
        )
        if profile and profile.programme_version_id:
            programme = (
                db.query(ProgrammeVersion)
                .filter(
                    ProgrammeVersion.id == profile.programme_version_id,
                    ProgrammeVersion.tenant_id == tenant_id,
                    ProgrammeVersion.status == "active",
                )
                .first()
            )
        if programme:
            rules = db.query(ProgrammeRule).filter(
                ProgrammeRule.programme_version_id == programme.id
            ).all()
            required = next(
                (
                    rule
                    for rule in rules
                    if rule.rule_type == "required" and rule.course_code == offering.course_code
                ),
                None,
            )
            elective = next(
                (
                    rule
                    for rule in rules
                    if rule.rule_type == "elective_pool"
                    and (
                        rule.course_code == offering.course_code
                        or (
                            rule.course_category
                            and rule.course_category == offering.course_category
                        )
                    )
                ),
                None,
            )
            if required:
                relationship = {
                    "type": "required",
                    "label": "培养方案必修课程",
                    "matched_rule": required.rule_code,
                }
            elif elective:
                relationship = {
                    "type": "elective_pool",
                    "label": "属于培养方案允许的选修范围",
                    "matched_rule": elective.rule_code,
                }
            else:
                relationship = {
                    "type": "outside_scope",
                    "label": "未匹配到培养方案课程范围",
                    "matched_rule": None,
                }

    history = None
    if user_id:
        history_record = (
            db.query(AcademicHistoryRecord)
            .filter(
                AcademicHistoryRecord.tenant_id == tenant_id,
                AcademicHistoryRecord.user_id == user_id,
                (
                    (AcademicHistoryRecord.course_code == offering.course_code)
                    | (AcademicHistoryRecord.course_name == offering.course_name)
                ),
            )
            .order_by(AcademicHistoryRecord.updated_at.desc())
            .first()
        )
        if history_record:
            history = {
                "record_id": history_record.id,
                "completion_status": history_record.completion_status,
                "confirmed_by_user": history_record.confirmed_by_user,
            }

    extra = _json_value(offering.extra_data, {})
    return {
        "offering_id": offering.id,
        "external_offering_id": offering.external_offering_id,
        "course_code": offering.course_code,
        "course_name": offering.course_name,
        "credits": offering.credits,
        "course_category": offering.course_category,
        "department": offering.department or (canonical.department if canonical else None),
        "teacher_name": offering.teacher_name,
        "campus": offering.campus,
        "schedules": _json_value(offering.schedule_json, []),
        "capacity": offering.capacity,
        "remaining_capacity": offering.remaining_capacity,
        "source_updated_at": (
            offering.source_updated_at.isoformat() if offering.source_updated_at else None
        ),
        "description": canonical.description if canonical else None,
        "objectives": canonical.objectives if canonical else None,
        "extra": extra,
        "snapshot": {
            "id": snapshot.id,
            "snapshot_id": snapshot.external_snapshot_id,
            "semester": snapshot.semester,
            "status": snapshot.status,
            "generated_at": snapshot.generated_at.isoformat(),
        },
        "programme": (
            {
                "id": programme.id,
                "programme_name": programme.programme_name,
                "version_code": programme.version_code,
            }
            if programme
            else None
        ),
        "programme_relationship": relationship,
        "history": history,
    }
