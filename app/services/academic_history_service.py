import hashlib
import re
import uuid
from dataclasses import asdict
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.planning import AcademicHistoryImport, AcademicHistoryRecord
from app.schemas.planning import HistoryImportConfirmRequest, ManualHistoryRecord
from app.services.history_parser import ParsedCourse, parse_history_file


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fffⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]", "", value.lower())


def _match_courses(db: Session, parsed: list[ParsedCourse]) -> list[dict]:
    courses = db.query(Course).all()
    by_code = {course.code.strip().lower(): course for course in courses if course.code}
    by_name = {_normalise_name(course.name): course for course in courses if course.name}
    matched = []
    for record in parsed:
        course = None
        confidence = 0.0
        if record.course_code:
            course = by_code.get(record.course_code.strip().lower())
            if course:
                confidence = 1.0
        normalised_name = _normalise_name(record.course_name)
        if not course and normalised_name in by_name:
            course = by_name[normalised_name]
            confidence = 0.98
        if not course and normalised_name:
            candidates = [
                (SequenceMatcher(None, normalised_name, name).ratio(), candidate)
                for name, candidate in by_name.items()
            ]
            if candidates:
                best_score, best_course = max(candidates, key=lambda item: item[0])
                if best_score >= 0.72:
                    course = best_course
                    confidence = round(best_score, 4)
        matched.append(
            {
                **asdict(record),
                "course_id": course.id if course else None,
                "matched_code": course.code if course and not record.course_code else record.course_code,
                "matched_name": course.name if course and confidence >= 0.9 else record.course_name,
                "match_confidence": confidence,
            }
        )
    return matched


def _persist_import(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    file_name: str,
    file_type: str,
    file_sha256: str,
    parser_name: str,
    parsed: list[ParsedCourse],
) -> AcademicHistoryImport:
    matched_records = _match_courses(db, parsed)
    import_record = AcademicHistoryImport(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        file_name=file_name,
        file_type=file_type,
        file_sha256=file_sha256,
        parser_name=parser_name,
        status="needs_confirmation",
        record_count=len(matched_records),
    )
    db.add(import_record)
    db.flush()

    seen: set[tuple] = set()
    actual_count = 0
    for item in matched_records:
        identity = (
            (item.get("matched_code") or "").lower(),
            _normalise_name(item["matched_name"]),
            item.get("semester") or "",
        )
        if identity in seen:
            continue
        seen.add(identity)
        db.add(
            AcademicHistoryRecord(
                import_id=import_record.id,
                tenant_id=tenant_id,
                user_id=user_id,
                course_id=item["course_id"],
                course_code=item.get("matched_code"),
                course_name=item["matched_name"],
                semester=item.get("semester"),
                credits=item.get("credits"),
                completion_status="assumed_passed",
                status_source="historical_timetable_default",
                match_confidence=item["match_confidence"],
                confirmed_by_user=False,
            )
        )
        actual_count += 1
    import_record.record_count = actual_count
    db.commit()
    db.refresh(import_record)
    return import_record


def create_history_import(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    file_name: str,
    content: bytes,
) -> tuple[AcademicHistoryImport, list[str], bool]:
    digest = hashlib.sha256(content).hexdigest()
    existing = (
        db.query(AcademicHistoryImport)
        .filter(
            AcademicHistoryImport.tenant_id == tenant_id,
            AcademicHistoryImport.user_id == user_id,
            AcademicHistoryImport.file_sha256 == digest,
            AcademicHistoryImport.status != "failed",
        )
        .order_by(AcademicHistoryImport.created_at.desc())
        .first()
    )
    if existing:
        return existing, ["The same file was already imported"], True

    parser_name, parsed, warnings = parse_history_file(file_name, content)
    import_record = _persist_import(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        file_name=file_name,
        file_type=file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown",
        file_sha256=digest,
        parser_name=parser_name,
        parsed=parsed,
    )
    low_confidence = db.query(AcademicHistoryRecord).filter(
        AcademicHistoryRecord.import_id == import_record.id,
        AcademicHistoryRecord.match_confidence < 0.9,
    ).count()
    if low_confidence:
        warnings.append(f"{low_confidence} course records need manual confirmation")
    warnings.append("All imported courses are temporarily treated as assumed_passed")
    return import_record, warnings, False


def create_manual_history_import(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    records: list[ManualHistoryRecord],
) -> AcademicHistoryImport:
    parsed = [
        ParsedCourse(
            course_code=item.course_code,
            course_name=item.course_name,
            semester=item.semester,
            credits=item.credits,
        )
        for item in records
    ]
    digest = hashlib.sha256(
        repr([(item.course_code, item.course_name, item.semester, item.credits) for item in records]).encode()
    ).hexdigest()
    return _persist_import(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        file_name="manual-entry.json",
        file_type="manual",
        file_sha256=digest,
        parser_name="manual_entry_v1",
        parsed=parsed,
    )


def confirm_history_import(
    db: Session,
    import_record: AcademicHistoryImport,
    payload: HistoryImportConfirmRequest,
) -> AcademicHistoryImport:
    records = db.query(AcademicHistoryRecord).filter(
        AcademicHistoryRecord.import_id == import_record.id
    ).all()
    by_id = {record.id: record for record in records}
    for correction in payload.corrections:
        record = by_id.get(correction.record_id)
        if not record:
            raise ValueError(f"Record {correction.record_id} does not belong to this import")
        if correction.course_code is not None:
            record.course_code = correction.course_code
        if correction.course_name is not None:
            record.course_name = correction.course_name
        if correction.semester is not None:
            record.semester = correction.semester
        if correction.credits is not None:
            record.credits = correction.credits
        if correction.completion_status is not None:
            record.completion_status = correction.completion_status
            record.status_source = "user_confirmation"
        record.confirmed_by_user = True

    for record in records:
        record.confirmed_by_user = True
    import_record.status = "confirmed"
    import_record.confirmed_at = datetime.now()
    db.commit()
    db.refresh(import_record)
    return import_record


def update_history_record_status(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    record_id: int,
    status: str,
) -> AcademicHistoryRecord:
    record = (
        db.query(AcademicHistoryRecord)
        .filter(
            AcademicHistoryRecord.id == record_id,
            AcademicHistoryRecord.tenant_id == tenant_id,
            AcademicHistoryRecord.user_id == user_id,
        )
        .first()
    )
    if not record:
        raise ValueError("History record not found")
    record.completion_status = status
    record.status_source = "natural_language_user_confirmation"
    record.confirmed_by_user = True
    db.commit()
    db.refresh(record)
    return record
