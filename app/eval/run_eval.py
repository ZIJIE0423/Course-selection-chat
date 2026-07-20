"""Run the reproducible SQL-only M1 acceptance evaluation."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.database.mysql import Base
from app.eval.eval_report import generate_markdown_report
from app.eval.metrics import acceptance_status, calculate_all_metrics
from app.models.planning import CourseOffering, CourseOfferingSnapshot, PlanningSession
from app.schemas.planning import (
    CourseOfferingSnapshotImport,
    ParsedRequirements,
    PlanningConfirmRequest,
    RequirementItem,
)
from app.scripts.generate_synthetic_m1_data import build_snapshot
from app.services.course_data_service import import_course_offering_snapshot
from app.services.planning_service import PlanningValidationError, recommend_courses
from app.tools.sql_tools import classify_m1_structured_query, extract_m1_course_lookup, search_active_course_offerings


EVIDENCE_FIELDS = {"source_type", "tenant_id", "snapshot_id", "snapshot_db_id", "generated_at", "source_updated_at", "record_id"}


def _values_equal(actual, expected) -> bool:
    return abs(float(actual) - expected) < 1e-9 if isinstance(expected, float) and actual is not None else actual == expected


def create_evaluation_session(course_count: int = 3):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    payload = CourseOfferingSnapshotImport.model_validate(build_snapshot(course_count))
    snapshot, _ = import_course_offering_snapshot(db, payload)
    return db, engine, snapshot


def _fact_case(db, test_case: dict) -> dict:
    route = classify_m1_structured_query(test_case["query"])
    lookup = extract_m1_course_lookup(test_case["query"])
    records = search_active_course_offerings(db, tenant_id=test_case["tenant_id"], **lookup) if route == "mysql_query" and lookup else []
    record = records[0] if len(records) == 1 else None
    evidence = record.get("evidence", {}) if record else {}
    actual_value = record.get(test_case["requested_field"]) if record else None
    safe_refusal = record is None
    fact_correct = record is not None and _values_equal(actual_value, test_case["expected_value"])
    return {
        "outcome": "safe_refusal" if safe_refusal else "fact_answer",
        "safe_refusal": safe_refusal,
        "fact_correct": fact_correct,
        "hard_constraints_satisfied": None,
        "evidence_valid": bool(record) and EVIDENCE_FIELDS.issubset(evidence) and all(evidence.get(field) is not None for field in EVIDENCE_FIELDS) and evidence.get("source_type") == "official_structured_snapshot",
        "predicted_route": route, "extracted_lookup": lookup, "match_count": len(records), "actual_value": actual_value,
    }


def _constraint_for(fixture: str) -> list[RequirementItem]:
    values = {
        "campus": ("campus", "鱼山校区"), "credits": ("credits", 1.5),
        "course_category": ("course_category", "专业选修"), "weekday": ("weekday", 2),
        "teacher_name": ("teacher_name", "教师_02"), "missing_campus": ("campus", "鱼山校区"),
        "missing_credits": ("credits", 1.0), "missing_schedule": ("weekday", 1),
    }
    if fixture not in values:
        return []
    kind, value = values[fixture]
    return [RequirementItem(type=kind, operator="lte" if kind == "credits" else "eq", value=value)]


def _apply_fixture(db, snapshot, fixture: str) -> None:
    now = datetime.now(timezone.utc)
    if fixture == "stale":
        snapshot.generated_at = now - timedelta(days=181)
        for offering in db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id):
            offering.source_updated_at = now - timedelta(days=181)
    elif fixture == "missing_source_updated_at":
        db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first().source_updated_at = None
    elif fixture == "missing_remaining_capacity":
        db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first().remaining_capacity = None
    elif fixture == "missing_campus":
        db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first().campus = None
    elif fixture == "missing_credits":
        db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first().credits = None
    elif fixture == "missing_schedule":
        db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first().schedule_json = ""
    elif fixture == "active_conflict":
        conflict = CourseOfferingSnapshot(tenant_id=snapshot.tenant_id, semester=snapshot.semester, external_snapshot_id=f"conflict-{uuid.uuid4()}", generated_at=now, checksum="conflict", status="active", record_count=0)
        db.add(conflict)
    elif fixture == "ambiguous":
        original = db.query(CourseOffering).filter(CourseOffering.snapshot_id == snapshot.id).first()
        db.add(CourseOffering(snapshot_id=snapshot.id, external_offering_id=f"ambiguous-{uuid.uuid4()}", course_id=original.course_id, course_code=original.course_code, course_name=original.course_name, credits=original.credits, course_category=original.course_category, department=original.department, campus=original.campus, teacher_name=original.teacher_name, schedule_json=original.schedule_json, capacity=original.capacity, remaining_capacity=original.remaining_capacity, source_updated_at=original.source_updated_at, extra_data=original.extra_data))
    db.commit()


def _card_satisfies(card, constraint: RequirementItem) -> bool:
    if constraint.type == "campus": return constraint.value in (card.campus or "")
    if constraint.type == "course_category": return constraint.value in (card.course_category or "")
    if constraint.type == "teacher_name": return constraint.value in (card.teacher_name or "")
    if constraint.type == "credits": return card.credits is not None and card.credits <= float(constraint.value)
    if constraint.type == "weekday": return any(slot.get("weekday") == int(constraint.value) for slot in card.schedules)
    return False


def _planning_case(test_case: dict) -> dict:
    db, engine, snapshot = create_evaluation_session()
    try:
        fixture = test_case["fixture"]
        _apply_fixture(db, snapshot, fixture)
        constraints = _constraint_for(fixture)
        session = PlanningSession(id=str(uuid.uuid4()), tenant_id=snapshot.tenant_id, user_id="eval-user", snapshot_id=snapshot.id, raw_query=test_case["query"], requirements_json=ParsedRequirements(intent="course_recommendation", next_action="execute").model_dump_json(), state="ready")
        db.add(session)
        db.commit()
        try:
            response = recommend_courses(db, session, PlanningConfirmRequest(constraints=constraints, preferences=[]))
        except PlanningValidationError as exc:
            return {"outcome": "safe_refusal", "safe_refusal": True, "fact_correct": None, "hard_constraints_satisfied": None, "evidence_valid": None, "refusal_reason": str(exc)}
        hard_constraints_satisfied = bool(response.recommendations) and all(_card_satisfies(card, constraint) for card in response.recommendations for constraint in constraints)
        return {"outcome": "recommendation", "safe_refusal": False, "fact_correct": None, "hard_constraints_satisfied": hard_constraints_satisfied, "evidence_valid": None, "candidate_count": response.total_candidates}
    finally:
        db.close()
        engine.dispose()


def run_single_case(fact_db, test_case: dict) -> dict:
    started = time.perf_counter()
    result = {"case_id": test_case["case_id"], "query": test_case["query"], "scenario": test_case["scenario"], "expected_outcome": test_case["expected_outcome"]}
    try:
        result.update(_fact_case(fact_db, test_case) if test_case["scenario"] in {"structured_course_fact", "structured_missing_record"} else _planning_case(test_case))
        result["case_passed"] = result["outcome"] == test_case["expected_outcome"] and (test_case["scenario"] != "recommendation_hard_constraint" or result.get("hard_constraints_satisfied") is True)
    except Exception as exc:
        result.update({"outcome": "error", "safe_refusal": False, "fact_correct": False, "hard_constraints_satisfied": False, "evidence_valid": False, "case_passed": False, "error": f"{type(exc).__name__}: {exc}"})
    result["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SQL-only M1 acceptance evaluation")
    parser.add_argument("--cases", type=Path, default=project_root / "app/eval/test_cases.jsonl")
    parser.add_argument("--output-dir", type=Path, default=project_root / "eval_outputs")
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    fact_db, engine, _ = create_evaluation_session(70)
    try:
        results = [run_single_case(fact_db, case) for case in cases]
    finally:
        fact_db.close(); engine.dispose()
    metrics = calculate_all_metrics(results)
    status = acceptance_status(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "eval_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_markdown_report(metrics, status, results, args.output_dir / "eval_summary.md")
    print(json.dumps({"metrics": metrics, "acceptance": status}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(status.values()) else 1)


if __name__ == "__main__":
    main()
