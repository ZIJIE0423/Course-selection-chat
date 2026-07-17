from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/capabilities")
def get_capabilities():
    return {
        "version": "1",
        "modules": {
            "course_planning": settings.FEATURE_COURSE_PLANNING,
            "academic_history_import": settings.FEATURE_ACADEMIC_HISTORY,
            "schedule_conflict": settings.FEATURE_SCHEDULE_CONFLICT,
            "course_feedback": settings.FEATURE_COURSE_FEEDBACK,
            "student_review_rag": settings.FEATURE_STUDENT_REVIEW_RAG,
        },
        "academic_history": {
            "supported_formats": ["csv", "tsv", "xlsx", "xlsm", "json", "txt", "md", "pdf"],
            "image_ocr_configured": bool(settings.HISTORY_OCR_ENDPOINT),
            "default_completion_status": "assumed_passed",
            "max_upload_mb": settings.MAX_HISTORY_UPLOAD_MB,
        },
        "integration": {
            "course_offering_snapshot": True,
            "programme_version_import": True,
        },
    }
