from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.mysql import get_db
from app.models.planning import AcademicHistoryImport, AcademicHistoryRecord
from app.schemas.planning import (
    HistoryImportConfirmRequest,
    HistoryImportResponse,
    HistoryRecordView,
    ManualHistoryImportRequest,
)
from app.services.academic_history_service import (
    confirm_history_import,
    create_history_import,
    create_manual_history_import,
)
from app.services.history_parser import HistoryParseError

router = APIRouter()


def _record_view(record: AcademicHistoryRecord) -> HistoryRecordView:
    return HistoryRecordView(
        id=record.id,
        course_code=record.course_code,
        course_name=record.course_name,
        semester=record.semester,
        credits=record.credits,
        completion_status=record.completion_status,
        status_source=record.status_source,
        match_confidence=record.match_confidence,
        matched_course_id=record.course_id,
        confirmed_by_user=record.confirmed_by_user,
    )


def _import_response(
    db: Session,
    import_record: AcademicHistoryImport,
    warnings: list[str] | None = None,
) -> HistoryImportResponse:
    records = db.query(AcademicHistoryRecord).filter(
        AcademicHistoryRecord.import_id == import_record.id
    ).order_by(AcademicHistoryRecord.id).all()
    return HistoryImportResponse(
        import_id=import_record.id,
        status=import_record.status,
        file_name=import_record.file_name,
        parser_name=import_record.parser_name,
        record_count=len(records),
        records=[_record_view(record) for record in records],
        warnings=warnings or [],
    )


@router.get("/records")
def list_history_records(
    tenant_id: str = Header(alias="X-Tenant-Id"),
    user_id: str = Header(alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    records = (
        db.query(AcademicHistoryRecord)
        .filter(
            AcademicHistoryRecord.tenant_id == tenant_id,
            AcademicHistoryRecord.user_id == user_id,
        )
        .order_by(
            AcademicHistoryRecord.updated_at.desc(),
            AcademicHistoryRecord.id.desc(),
        )
        .all()
    )
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "record_count": len(records),
        "records": [_record_view(record).model_dump() for record in records],
    }


@router.post("/imports", response_model=HistoryImportResponse)
async def upload_history_timetable(
    file: UploadFile = File(...),
    tenant_id: str = Header(alias="X-Tenant-Id"),
    user_id: str = Header(alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    content = await file.read()
    max_bytes = settings.MAX_HISTORY_UPLOAD_MB * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_HISTORY_UPLOAD_MB} MB limit",
        )
    try:
        import_record, warnings, _ = create_history_import(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            file_name=file.filename or "history-upload",
            content=content,
        )
    except HistoryParseError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _import_response(db, import_record, warnings)


@router.post("/imports/manual", response_model=HistoryImportResponse)
def create_manual_import(
    payload: ManualHistoryImportRequest,
    db: Session = Depends(get_db),
):
    import_record = create_manual_history_import(
        db,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        records=payload.records,
    )
    return _import_response(
        db,
        import_record,
        ["All manually entered courses are temporarily treated as assumed_passed"],
    )


@router.get("/imports/{import_id}", response_model=HistoryImportResponse)
def get_history_import(import_id: str, db: Session = Depends(get_db)):
    import_record = db.query(AcademicHistoryImport).filter(
        AcademicHistoryImport.id == import_id
    ).first()
    if not import_record:
        raise HTTPException(status_code=404, detail="History import not found")
    return _import_response(db, import_record)


@router.post("/imports/{import_id}/confirm", response_model=HistoryImportResponse)
def confirm_import(
    import_id: str,
    payload: HistoryImportConfirmRequest,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    user_id: str = Header(alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    import_record = (
        db.query(AcademicHistoryImport)
        .filter(
            AcademicHistoryImport.id == import_id,
            AcademicHistoryImport.tenant_id == tenant_id,
            AcademicHistoryImport.user_id == user_id,
        )
        .first()
    )
    if not import_record:
        raise HTTPException(status_code=404, detail="History import not found")
    try:
        confirm_history_import(db, import_record, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _import_response(db, import_record)
