"""Generate deterministic, non-production M1 fixtures without reading real data."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

DATASET_VERSION = "m1-synthetic-course-data-v1"
COURSE_TITLES = ("学术写作", "数据分析导论", "海洋文化", "创新方法", "信息伦理", "科学传播")
CAMPUSES = ("崂山校区", "鱼山校区", "西海岸校区")


def build_snapshot(course_count: int = 160) -> dict:
    courses = []
    for index in range(course_count):
        code = f"SYN{index + 1:03d}"
        courses.append({
            "external_offering_id": f"synthetic-section-{index + 1:03d}",
            "course_code": code,
            "course_name": f"{COURSE_TITLES[index % len(COURSE_TITLES)]}（模拟{index + 1:03d}）",
            "credits": 1.0 + (index % 3) * 0.5,
            "course_category": "通识选修" if index % 2 == 0 else "专业选修",
            "department": f"模拟学院{index % 4 + 1}",
            "campus": CAMPUSES[index % len(CAMPUSES)],
            "teacher_name": f"教师_{index % 12 + 1:02d}",
            "schedules": [{"weekday": index % 5 + 1, "periods": [index % 6 + 1, index % 6 + 2], "weeks": "1-16", "location": f"模拟教学楼 {100 + index}"}],
            "capacity": 40 + (index % 5) * 10,
            "remaining_capacity": index % 21,
            "source_updated_at": "2026-07-19T00:00:00+00:00",
            "extra": {"synthetic": True, "data_classification": "synthetic"},
        })
    return {"tenant_id": "weouc-synthetic", "semester": "2026-2027-1", "snapshot_id": DATASET_VERSION, "generated_at": "2026-07-19T00:00:00+00:00", "courses": courses}


def write_dataset(output_dir: Path, course_count: int = 160) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(course_count)
    (output_dir / "course_offerings.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    programme = {"tenant_id": "weouc-synthetic", "programme_code": "SYN-CS-2026", "programme_name": "计算机科学培养方案（模拟）", "version_code": DATASET_VERSION, "rules": [{"rule_code": "SYN-GE-6", "rule_type": "credit_requirement", "course_category": "通识选修", "min_credits": 6, "metadata": {"synthetic": True}}]}
    (output_dir / "programme.json").write_text(json.dumps(programme, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("course_code", "course_name", "semester", "credits"))
        writer.writeheader()
        for course in snapshot["courses"][:6]:
            writer.writerow({"course_code": course["course_code"], "course_name": course["course_name"], "semester": "2025-2026-2", "credits": course["credits"]})
    manifest = {"dataset_version": DATASET_VERSION, "data_classification": "synthetic", "contains_real_data": False, "generated_at": datetime.now(timezone.utc).isoformat(), "files": ["course_offerings.json", "programme.json", "history.csv"], "prohibited_fields": ["student_id", "student_name", "phone", "email", "identity_number"]}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate privacy-safe M1 synthetic fixtures.")
    parser.add_argument("--output", type=Path, default=Path("demo_data/m1_synthetic"))
    parser.add_argument("--course-count", type=int, default=160)
    args = parser.parse_args()
    write_dataset(args.output, args.course_count)
    print(f"Generated {DATASET_VERSION} at {args.output}")


if __name__ == "__main__":
    main()
