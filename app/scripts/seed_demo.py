import json
from datetime import datetime, timezone
from pathlib import Path

from app.database.mysql import Base, SessionLocal, engine
from app.models.planning import StudentProfile
from app.schemas.planning import CourseOfferingSnapshotImport, ProgrammeVersionImport
from app.services.course_data_service import (
    import_course_offering_snapshot,
    import_programme_version,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    demo_root = project_root / "demo_data"
    programme_payload = ProgrammeVersionImport.model_validate(
        _load_json(demo_root / "programme.json")
    )
    snapshot_payload = CourseOfferingSnapshotImport.model_validate(
        _load_json(demo_root / "course_offerings.json")
    )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        programme = import_programme_version(db, programme_payload)
        snapshot, replay = import_course_offering_snapshot(db, snapshot_payload)
        profile = (
            db.query(StudentProfile)
            .filter(
                StudentProfile.tenant_id == "weouc",
                StudentProfile.user_id == "student-1",
            )
            .first()
        )
        if not profile:
            profile = StudentProfile(tenant_id="weouc", user_id="student-1")
            db.add(profile)
        profile.grade = "2024级"
        profile.department = "信息科学与工程学部"
        profile.major = "计算机科学与技术"
        profile.programme_version_id = programme.id
        profile.programme_confirmed_at = datetime.now(timezone.utc)
        db.commit()
        print("Demo data ready")
        print(f"programme_version_id={programme.id}")
        print(f"snapshot_id={snapshot.id} replay={replay}")
        print("student=weouc/student-1")
        print("sample_history=demo_data/history.csv")
    finally:
        db.close()


if __name__ == "__main__":
    main()
