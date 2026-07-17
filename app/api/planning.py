from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.mysql import get_db
from app.models.planning import (
    CourseOfferingSnapshot,
    PlanningSession,
    ProgrammeVersion,
    StudentProfile,
)
from app.schemas.planning import (
    HistoryStatusConfirmRequest,
    PlanningConfirmRequest,
    PlanningSessionCreate,
    PlanningSessionView,
    RecommendationResponse,
)
from app.services.academic_history_service import update_history_record_status
from app.services.planning_service import (
    PlanningValidationError,
    create_planning_session,
    recommend_courses,
)

router = APIRouter()


@router.get("/context")
def get_planning_context(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Return the active data versions required to start a planning session.

    The H5 must not persist database primary keys as configuration.  It asks
    for the current context before every new browser session, so a newly
    imported course snapshot is picked up without a frontend deployment.
    """
    snapshot = (
        db.query(CourseOfferingSnapshot)
        .filter(
            CourseOfferingSnapshot.tenant_id == tenant_id,
            CourseOfferingSnapshot.status == "active",
        )
        .order_by(
            CourseOfferingSnapshot.generated_at.desc(),
            CourseOfferingSnapshot.id.desc(),
        )
        .first()
    )

    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.user_id == user_id,
        )
        .first()
    )
    programme = None
    programme_confirmed = False
    if profile and profile.programme_version_id:
        programme = (
            db.query(ProgrammeVersion)
            .filter(
                ProgrammeVersion.id == profile.programme_version_id,
                ProgrammeVersion.tenant_id == tenant_id,
                ProgrammeVersion.status == "active",
            )
            .first()
        )
        programme_confirmed = bool(programme and profile.programme_confirmed_at)

    # Demo/local fallback: until the H5 profile endpoint is connected, use the
    # newest active programme but make its unconfirmed state explicit.
    if programme is None:
        programme = (
            db.query(ProgrammeVersion)
            .filter(
                ProgrammeVersion.tenant_id == tenant_id,
                ProgrammeVersion.status == "active",
            )
            .order_by(ProgrammeVersion.id.desc())
            .first()
        )

    missing = []
    if snapshot is None:
        missing.append("course_offering_snapshot")
    if programme is None:
        missing.append("programme_version")

    return {
        "available": not missing,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "missing": missing,
        "snapshot": (
            {
                "id": snapshot.id,
                "snapshot_id": snapshot.external_snapshot_id,
                "semester": snapshot.semester,
                "generated_at": snapshot.generated_at.isoformat(),
                "record_count": snapshot.record_count,
            }
            if snapshot
            else None
        ),
        "programme": (
            {
                "id": programme.id,
                "programme_code": programme.programme_code,
                "programme_name": programme.programme_name,
                "version_code": programme.version_code,
                "confirmed": programme_confirmed,
            }
            if programme
            else None
        ),
    }


@router.post("/sessions", response_model=PlanningSessionView)
def create_session(payload: PlanningSessionCreate, db: Session = Depends(get_db)):
    try:
        session, requirements = create_planning_session(db, payload)
    except PlanningValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlanningSessionView(
        session_id=session.id,
        state=session.state,
        requirements=requirements,
    )


@router.post(
    "/sessions/{session_id}/requirements/confirm",
    response_model=RecommendationResponse,
)
def confirm_requirements(
    session_id: str,
    payload: PlanningConfirmRequest,
    db: Session = Depends(get_db),
):
    session = db.query(PlanningSession).filter(PlanningSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found")
    try:
        return recommend_courses(db, session, payload)
    except PlanningValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/history-corrections/confirm")
def confirm_history_correction(
    payload: HistoryStatusConfirmRequest,
    db: Session = Depends(get_db),
):
    try:
        record = update_history_record_status(
            db,
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            record_id=payload.record_id,
            status=payload.status,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "record_id": record.id,
        "course_name": record.course_name,
        "completion_status": record.completion_status,
        "status_source": record.status_source,
    }
