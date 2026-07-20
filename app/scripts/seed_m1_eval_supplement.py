"""Idempotently import the synthetic M1 evaluation supplement into SQLite."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from app.database.mysql import Base, SessionLocal, engine
from app.models.course import Course


def main() -> None:
    source = project_root / "demo_data" / "m1_synthetic" / "eval_supplement_courses.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in payload["courses"]:
            course = db.query(Course).filter(Course.code == item["code"]).first()
            if course is None:
                course = Course(code=item["code"])
                db.add(course)
            for field, value in item.items():
                setattr(course, field, value)
            course.data_source = payload["dataset_version"]
        db.commit()
        print(f"Imported {len(payload['courses'])} synthetic M1 supplement courses.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
