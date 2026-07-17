import hashlib
import json

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.planning import (
    CourseOffering,
    CourseOfferingSnapshot,
    ProgrammeRule,
    ProgrammeVersion,
)
from app.schemas.planning import CourseOfferingSnapshotImport, ProgrammeVersionImport


class SnapshotConflictError(ValueError):
    pass


def _canonical_checksum(payload: CourseOfferingSnapshotImport) -> str:
    data = payload.model_dump(mode="json")
    data["courses"] = sorted(
        data["courses"],
        key=lambda item: (
            item.get("external_offering_id") or "",
            item["course_code"],
            item.get("teacher_name") or "",
        ),
    )
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _offering_external_id(course: dict) -> str:
    if course.get("external_offering_id"):
        return course["external_offering_id"]
    identity = {
        "course_code": course["course_code"],
        "teacher_name": course.get("teacher_name") or "",
        "campus": course.get("campus") or "",
        "schedules": course.get("schedules") or [],
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{course['course_code']}:{digest}"


def import_course_offering_snapshot(
    db: Session,
    payload: CourseOfferingSnapshotImport,
) -> tuple[CourseOfferingSnapshot, bool]:
    checksum = _canonical_checksum(payload)
    existing = (
        db.query(CourseOfferingSnapshot)
        .filter(
            CourseOfferingSnapshot.tenant_id == payload.tenant_id,
            CourseOfferingSnapshot.external_snapshot_id == payload.snapshot_id,
        )
        .first()
    )
    if existing:
        if existing.checksum != checksum:
            raise SnapshotConflictError(
                "snapshot_id already exists with different content; use a new snapshot_id"
            )
        return existing, True

    (
        db.query(CourseOfferingSnapshot)
        .filter(
            CourseOfferingSnapshot.tenant_id == payload.tenant_id,
            CourseOfferingSnapshot.semester == payload.semester,
            CourseOfferingSnapshot.status == "active",
        )
        .update({CourseOfferingSnapshot.status: "superseded"}, synchronize_session=False)
    )

    snapshot = CourseOfferingSnapshot(
        tenant_id=payload.tenant_id,
        semester=payload.semester,
        external_snapshot_id=payload.snapshot_id,
        generated_at=payload.generated_at,
        checksum=checksum,
        status="active",
        record_count=len(payload.courses),
    )
    db.add(snapshot)
    db.flush()

    for input_course in payload.courses:
        course_data = input_course.model_dump(mode="json")
        canonical_course = (
            db.query(Course).filter(Course.code == input_course.course_code).first()
        )
        if not canonical_course:
            canonical_course = Course(
                code=input_course.course_code,
                name=input_course.course_name,
                credit=input_course.credits,
                department=input_course.department,
                data_source=f"snapshot:{payload.snapshot_id}",
            )
            db.add(canonical_course)
            db.flush()
        else:
            canonical_course.name = input_course.course_name
            if input_course.credits is not None:
                canonical_course.credit = input_course.credits
            if input_course.department:
                canonical_course.department = input_course.department

        offering = CourseOffering(
            snapshot_id=snapshot.id,
            external_offering_id=_offering_external_id(course_data),
            course_id=canonical_course.id,
            course_code=input_course.course_code,
            course_name=input_course.course_name,
            credits=input_course.credits,
            course_category=input_course.course_category,
            department=input_course.department,
            campus=input_course.campus,
            teacher_name=input_course.teacher_name,
            schedule_json=json.dumps(course_data["schedules"], ensure_ascii=False),
            capacity=input_course.capacity,
            remaining_capacity=input_course.remaining_capacity,
            source_updated_at=input_course.source_updated_at,
            extra_data=json.dumps(input_course.extra, ensure_ascii=False),
        )
        db.add(offering)

    db.commit()
    db.refresh(snapshot)
    return snapshot, False


def import_programme_version(db: Session, payload: ProgrammeVersionImport) -> ProgrammeVersion:
    programme = (
        db.query(ProgrammeVersion)
        .filter(
            ProgrammeVersion.tenant_id == payload.tenant_id,
            ProgrammeVersion.programme_code == payload.programme_code,
            ProgrammeVersion.version_code == payload.version_code,
        )
        .first()
    )
    if not programme:
        programme = ProgrammeVersion(
            tenant_id=payload.tenant_id,
            programme_code=payload.programme_code,
            version_code=payload.version_code,
            programme_name=payload.programme_name,
        )
        db.add(programme)
        db.flush()

    programme.programme_name = payload.programme_name
    programme.applicable_grades = json.dumps(payload.applicable_grades, ensure_ascii=False)
    programme.issuing_unit = payload.issuing_unit
    programme.published_at = payload.published_at
    programme.source_reference = payload.source_reference
    programme.status = "active"

    db.query(ProgrammeRule).filter(
        ProgrammeRule.programme_version_id == programme.id
    ).delete(synchronize_session=False)
    for rule in payload.rules:
        db.add(
            ProgrammeRule(
                programme_version_id=programme.id,
                rule_code=rule.rule_code,
                rule_type=rule.rule_type,
                course_code=rule.course_code,
                course_category=rule.course_category,
                min_credits=rule.min_credits,
                required=rule.required,
                priority=rule.priority,
                rule_metadata=json.dumps(rule.metadata, ensure_ascii=False),
            )
        )
    db.commit()
    db.refresh(programme)
    return programme
