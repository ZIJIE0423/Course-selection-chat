"""Generate the deterministic M1 acceptance set, including safety gates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.scripts.generate_synthetic_m1_data import build_snapshot


DATASET_VERSION = "m1-structured-sql-v3"
TENANT_ID = "weouc-synthetic"
FIELD_QUERIES = {
    "course_name": "查询课程代码 {code} 的课程名称",
    "credits": "课程代码 {code} 多少学分？",
    "course_category": "课程代码 {code} 属于什么课程类别？",
    "department": "课程代码 {code} 的开课学院是什么？",
    "campus": "课程代码 {code} 在哪个校区？",
    "teacher_name": "课程代码 {code} 的授课教师是谁？",
    "capacity": "课程代码 {code} 的课程容量是多少？",
    "remaining_capacity": "课程代码 {code} 还有多少余量？",
    "semester": "课程代码 {code} 是哪个学期开课？",
}
NAME_FIELD_QUERIES = {
    "credits": "《{name}》多少学分？",
    "department": "《{name}》由哪个学院开设？",
    "campus": "《{name}》在哪个校区？",
    "teacher_name": "《{name}》的老师是谁？",
    "remaining_capacity": "《{name}》还有多少余量？",
}


def _base_case(index: int, scenario: str, query: str) -> dict:
    return {
        "case_id": f"M1-SQL-{index + 1:03d}",
        "dataset_version": DATASET_VERSION,
        "scenario": scenario,
        "data_classification": "synthetic_evaluation",
        "query": query,
        "tenant_id": TENANT_ID,
    }


def _found_case(index: int, course: dict, *, by_name: bool) -> dict:
    templates = NAME_FIELD_QUERIES if by_name else FIELD_QUERIES
    field = tuple(templates)[index % len(templates)]
    case = _base_case(
        index,
        "structured_course_fact",
        templates[field].format(code=course["course_code"], name=course["course_name"]),
    )
    case.update({
        "lookup": {"course_name": course["course_name"]} if by_name else {"course_code": course["course_code"]},
        "requested_field": field,
        "expected_value": "2026-2027-1" if field == "semester" else course[field],
        "expected_route": "mysql_query",
        "expected_source_type": "official_structured_snapshot",
        "expected_tools": ["mysql_query"],
        "should_abstain": False,
        "expected_outcome": "fact_answer",
    })
    return case


def _missing_case(index: int) -> dict:
    code = f"MISS{index + 1:03d}"
    case = _base_case(index, "structured_missing_record", f"课程代码 {code} 多少学分？")
    case.update({
        "lookup": {"course_code": code}, "requested_field": "credits", "expected_value": None,
        "expected_route": "mysql_query", "expected_source_type": "official_structured_snapshot",
        "expected_tools": ["mysql_query"], "should_abstain": True,
        "expected_outcome": "safe_refusal",
    })
    return case


def _risk_case(index: int, scenario: str, fixture: str) -> dict:
    labels = {
        "stale_snapshot": "活动快照已超过时效，推荐通识选修课",
        "critical_field_missing": "按硬约束推荐课程，但证据关键字段缺失",
        "active_snapshot_conflict": "活动快照存在冲突时推荐课程",
        "ambiguous_offering": "班次存在多条歧义记录时推荐课程",
    }
    case = _base_case(index, scenario, f"{labels[scenario]}（验收样例 {index + 1}）")
    case.update({"fixture": fixture, "expected_outcome": "safe_refusal", "should_abstain": True})
    return case


def _hard_constraint_case(index: int, fixture: str) -> dict:
    case = _base_case(index, "recommendation_hard_constraint", f"按 {fixture} 硬约束推荐课程（验收样例 {index + 1}）")
    case.update({"fixture": fixture, "expected_outcome": "recommendation", "should_abstain": False})
    return case


def build_test_cases(size: int = 200) -> list[dict]:
    """Build 200 independent cases covering facts, safety refusal and planning."""
    if size != 200:
        raise ValueError("M1 acceptance dataset is fixed at 200 cases")
    snapshot = build_snapshot(70)
    cases = [
        _found_case(index, course, by_name=index >= 35)
        for index, course in enumerate(snapshot["courses"])
    ]
    cases.extend(_missing_case(index) for index in range(70, 90))
    cases.extend(_risk_case(index, "stale_snapshot", "stale") for index in range(90, 115))
    missing_fixtures = ("missing_source_updated_at", "missing_remaining_capacity", "missing_campus", "missing_credits", "missing_schedule")
    cases.extend(_risk_case(index, "critical_field_missing", missing_fixtures[(index - 115) % len(missing_fixtures)]) for index in range(115, 140))
    cases.extend(_risk_case(index, "active_snapshot_conflict", "active_conflict") for index in range(140, 160))
    cases.extend(_risk_case(index, "ambiguous_offering", "ambiguous") for index in range(160, 175))
    constraint_fixtures = ("campus", "credits", "course_category", "weekday", "teacher_name")
    cases.extend(_hard_constraint_case(index, constraint_fixtures[(index - 175) % len(constraint_fixtures)]) for index in range(175, 200))
    return cases


def write_test_cases(output: Path, size: int = 200) -> Counter:
    cases = build_test_cases(size)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases), encoding="utf-8")
    return Counter(case["scenario"] for case in cases)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SQL-only M1 acceptance cases")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("app/eval/test_cases.jsonl"))
    args = parser.parse_args()
    distribution = write_test_cases(args.output, args.size)
    print(f"Generated {args.size} {DATASET_VERSION} cases at {args.output}.")
    print(f"Scenario distribution: {dict(sorted(distribution.items()))}")


if __name__ == "__main__":
    main()
