import csv
import json

from app.scripts.generate_synthetic_m1_data import DATASET_VERSION, write_dataset


def test_synthetic_dataset_has_versioned_non_pii_contract(tmp_path):
    write_dataset(tmp_path, course_count=30)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    snapshot = json.loads((tmp_path / "course_offerings.json").read_text(encoding="utf-8"))
    with (tmp_path / "history.csv").open(encoding="utf-8") as handle:
        history = list(csv.DictReader(handle))

    assert manifest["dataset_version"] == DATASET_VERSION
    assert manifest["contains_real_data"] is False
    assert len(snapshot["courses"]) == 30
    assert len(history) == 6
    serialized = json.dumps({"snapshot": snapshot, "history": history}, ensure_ascii=False)
    assert "student_id" not in serialized
    assert "student_name" not in serialized


def test_default_dataset_is_large_enough_for_m1_fact_evaluation(tmp_path):
    write_dataset(tmp_path)
    snapshot = json.loads((tmp_path / "course_offerings.json").read_text(encoding="utf-8"))
    assert len(snapshot["courses"]) == 160
    assert len({course["course_code"] for course in snapshot["courses"]}) == 160
    assert len({course["course_name"] for course in snapshot["courses"]}) == 160
