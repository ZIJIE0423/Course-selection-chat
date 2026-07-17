from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.mysql import get_db
from app.models.planning import CourseOfferingSnapshot, ProgrammeRule
from app.schemas.planning import (
    CourseOfferingSnapshotImport,
    CourseOfferingSnapshotResponse,
    ProgrammeVersionImport,
)
from app.services.course_data_service import (
    SnapshotConflictError,
    import_course_offering_snapshot,
    import_programme_version,
)

router = APIRouter()


def verify_integration_token(
    x_integration_token: str | None = Header(default=None, alias="X-Integration-Token"),
):
    if settings.INTEGRATION_TOKEN and x_integration_token != settings.INTEGRATION_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid integration token")


@router.post(
    "/course-offering-snapshots",
    response_model=CourseOfferingSnapshotResponse,
    dependencies=[Depends(verify_integration_token)],
)
def create_course_offering_snapshot(
    payload: CourseOfferingSnapshotImport,
    db: Session = Depends(get_db),
):
    try:
        snapshot, replay = import_course_offering_snapshot(db, payload)
    except SnapshotConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CourseOfferingSnapshotResponse(
        snapshot_db_id=snapshot.id,
        snapshot_id=snapshot.external_snapshot_id,
        semester=snapshot.semester,
        record_count=snapshot.record_count,
        checksum=snapshot.checksum,
        idempotent_replay=replay,
    )


@router.get(
    "/course-offering-snapshots/{snapshot_id}",
    dependencies=[Depends(verify_integration_token)],
)
def get_course_offering_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(CourseOfferingSnapshot).filter(CourseOfferingSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {
        "snapshot_db_id": snapshot.id,
        "snapshot_id": snapshot.external_snapshot_id,
        "tenant_id": snapshot.tenant_id,
        "semester": snapshot.semester,
        "status": snapshot.status,
        "record_count": snapshot.record_count,
        "generated_at": snapshot.generated_at,
        "imported_at": snapshot.imported_at,
    }


@router.post(
    "/programme-versions",
    dependencies=[Depends(verify_integration_token)],
)
def create_programme_version(
    payload: ProgrammeVersionImport,
    db: Session = Depends(get_db),
):
    programme = import_programme_version(db, payload)
    rule_count = db.query(ProgrammeRule).filter(
        ProgrammeRule.programme_version_id == programme.id
    ).count()
    return {
        "programme_version_id": programme.id,
        "programme_code": programme.programme_code,
        "version_code": programme.version_code,
        "rule_count": rule_count,
    }
