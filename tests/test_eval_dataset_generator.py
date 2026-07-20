from __future__ import annotations

import json
from collections import Counter

import pytest

from generate_test_cases import DATASET_VERSION, build_test_cases, write_test_cases


def test_m1_dataset_is_synthetic_and_covers_all_acceptance_strata() -> None:
    cases = build_test_cases()
    distribution = Counter(case["scenario"] for case in cases)

    assert len(cases) == 200
    assert len({case["case_id"] for case in cases}) == 200
    assert len({case["query"] for case in cases}) == 200
    assert distribution == {
        "structured_course_fact": 70,
        "structured_missing_record": 20,
        "stale_snapshot": 25,
        "critical_field_missing": 25,
        "active_snapshot_conflict": 20,
        "ambiguous_offering": 15,
        "recommendation_hard_constraint": 25,
    }
    assert all(case["dataset_version"] == DATASET_VERSION for case in cases)
    assert all(case["data_classification"] == "synthetic_evaluation" for case in cases)
    assert all("rag" not in json.dumps(case).lower() for case in cases)


def test_writer_emits_jsonl(tmp_path) -> None:
    output = tmp_path / "test_cases.jsonl"
    distribution = write_test_cases(output)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 200
    assert sum(distribution.values()) == 200


def test_generator_rejects_non_acceptance_size() -> None:
    with pytest.raises(ValueError, match="fixed at 200"):
        build_test_cases(199)
