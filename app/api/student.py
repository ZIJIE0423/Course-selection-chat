import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.mysql import get_db
from app.models.planning import ProgrammeVersion, StudentProfile
from app.schemas.planning import (
    ProgrammeOptionView,
    StudentProfileUpsert,
    StudentProfileView,
)

router = APIRouter()


def _normalise_grade(value: str) -> str:
    return value.strip().removesuffix("级")


def _programme_grades(programme: ProgrammeVersion) -> list[str]:
    try:
        values = json.loads(programme.applicable_grades or "[]")
    except json.JSONDecodeError:
        return []
    return [str(value) for value in values]


def _profile_view(profile: StudentProfile, programme: ProgrammeVersion) -> StudentProfileView:
    return StudentProfileView(
        tenant_id=profile.tenant_id,
        user_id=profile.user_id,
        grade=profile.grade or "",
        department=profile.department or "",
        major=profile.major or "",
        programme_version_id=programme.id,
        programme_name=programme.programme_name,
        programme_version_code=programme.version_code,
        programme_confirmed_at=profile.programme_confirmed_at,
    )


@router.get("/programmes", response_model=list[ProgrammeOptionView])
def list_programmes(
    tenant_id: str,
    grade: str | None = None,
    major: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
):
    programmes = (
        db.query(ProgrammeVersion)
        .filter(
            ProgrammeVersion.tenant_id == tenant_id,
            ProgrammeVersion.status == "active",
        )
        .order_by(ProgrammeVersion.id.desc())
        .all()
    )
    normalised_grade = _normalise_grade(grade) if grade else None
    if normalised_grade:
        programmes = [
            programme
            for programme in programmes
            if not _programme_grades(programme)
            or normalised_grade in {_normalise_grade(item) for item in _programme_grades(programme)}
        ]
    if major:
        matching = [programme for programme in programmes if major in programme.programme_name]
        if matching:
            programmes = matching
    return [
        ProgrammeOptionView(
            id=programme.id,
            programme_code=programme.programme_code,
            programme_name=programme.programme_name,
            version_code=programme.version_code,
            applicable_grades=_programme_grades(programme),
            issuing_unit=programme.issuing_unit,
            published_at=programme.published_at,
        )
        for programme in programmes
    ]


@router.get("/profile", response_model=StudentProfileView)
def get_profile(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.user_id == user_id,
        )
        .first()
    )
    if not profile or not profile.programme_version_id:
        raise HTTPException(status_code=404, detail="Student profile not found")
    programme = (
        db.query(ProgrammeVersion)
        .filter(
            ProgrammeVersion.id == profile.programme_version_id,
            ProgrammeVersion.tenant_id == tenant_id,
            ProgrammeVersion.status == "active",
        )
        .first()
    )
    if not programme:
        raise HTTPException(status_code=409, detail="Bound programme version is not active")
    return _profile_view(profile, programme)


@router.put("/profile", response_model=StudentProfileView)
def save_profile(
    payload: StudentProfileUpsert,
    db: Session = Depends(get_db),
):
    programme = (
        db.query(ProgrammeVersion)
        .filter(
            ProgrammeVersion.id == payload.programme_version_id,
            ProgrammeVersion.tenant_id == payload.tenant_id,
            ProgrammeVersion.status == "active",
        )
        .first()
    )
    if not programme:
        raise HTTPException(status_code=400, detail="Active programme version not found")

    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.tenant_id == payload.tenant_id,
            StudentProfile.user_id == payload.user_id,
        )
        .first()
    )
    if not profile:
        profile = StudentProfile(tenant_id=payload.tenant_id, user_id=payload.user_id)
        db.add(profile)

    profile.grade = payload.grade
    profile.department = payload.department
    profile.major = payload.major
    profile.programme_version_id = programme.id
    profile.programme_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return _profile_view(profile, programme)
