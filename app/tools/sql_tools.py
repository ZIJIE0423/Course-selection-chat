import re

from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.mysql import SessionLocal
from app.models.course import Course, Programme, CourseRequirement
from app.models.planning import CourseOffering, CourseOfferingSnapshot


M1_FACT_KEYWORDS = (
    "课程名称", "叫什么", "多少学分", "学分", "课程类别", "类别", "开课学院",
    "学院", "院系", "校区", "授课教师", "老师", "容量", "余量", "学期",
)


def normalize_course_query(query: str) -> str:
    for prefix in ("请基于已收录的选课资料回答：", "选课咨询：", "我想确认一下，", "仅依据可验证来源说明："):
        if query.startswith(prefix):
            return query[len(prefix):].strip()
    return query


def classify_m1_structured_query(query: str) -> str:
    """Classify the bounded M1 fact-query surface without an LLM or RAG."""
    normalized = normalize_course_query(query)
    has_identifier = bool(re.search(r"\b(?:SYN|MISS)\d{3}\b", normalized, re.IGNORECASE))
    has_named_course = bool(re.search(r"《[^》]+》", normalized))
    if (has_identifier or has_named_course) and any(
        keyword in normalized for keyword in M1_FACT_KEYWORDS
    ):
        return "mysql_query"
    return "unsupported"


def extract_m1_course_lookup(query: str) -> dict[str, str] | None:
    """Extract the exact synthetic course code or quoted name used by M1 eval."""
    normalized = normalize_course_query(query)
    code_match = re.search(r"\b((?:SYN|MISS)\d{3})\b", normalized, re.IGNORECASE)
    if code_match:
        return {"course_code": code_match.group(1).upper()}
    name_match = re.search(r"《([^》]+)》", normalized)
    if name_match:
        return {"course_name": name_match.group(1).strip()}
    return None


def search_active_course_offerings(
    db: Session,
    *,
    tenant_id: str,
    course_code: str | None = None,
    course_name: str | None = None,
) -> list[dict]:
    """Return structured facts from the tenant's active offering snapshot."""
    if bool(course_code) == bool(course_name):
        raise ValueError("provide exactly one of course_code or course_name")

    query = (
        db.query(CourseOffering, CourseOfferingSnapshot)
        .join(CourseOfferingSnapshot, CourseOffering.snapshot_id == CourseOfferingSnapshot.id)
        .filter(
            CourseOfferingSnapshot.tenant_id == tenant_id,
            CourseOfferingSnapshot.status == "active",
        )
    )
    if course_code:
        query = query.filter(CourseOffering.course_code == course_code)
    else:
        query = query.filter(CourseOffering.course_name == course_name)

    records = []
    for offering, snapshot in query.order_by(CourseOffering.external_offering_id).all():
        records.append({
            "offering_id": offering.id,
            "course_code": offering.course_code,
            "course_name": offering.course_name,
            "credits": offering.credits,
            "course_category": offering.course_category,
            "department": offering.department,
            "campus": offering.campus,
            "teacher_name": offering.teacher_name,
            "capacity": offering.capacity,
            "remaining_capacity": offering.remaining_capacity,
            "semester": snapshot.semester,
            "evidence": {
                "source_type": "official_structured_snapshot",
                "tenant_id": snapshot.tenant_id,
                "snapshot_id": snapshot.external_snapshot_id,
                "snapshot_db_id": snapshot.id,
                "generated_at": snapshot.generated_at.isoformat(),
                "source_updated_at": (
                    offering.source_updated_at.isoformat()
                    if offering.source_updated_at else None
                ),
                "record_id": offering.external_offering_id,
            },
        })
    return records

def _execute_query(query_func):
    """辅助函数：管理数据库 session"""
    db = SessionLocal()
    try:
        return query_func(db)
    except Exception as e:
        print(f"Database query error: {e}")
        return None
    finally:
        db.close()

def search_course_by_code(course_code: str):
    """通过课程代码精确查询课程"""
    def query(db: Session):
        course = db.query(Course).filter(Course.code == course_code).first()
        if course:
            return {
                "code": course.code,
                "name": course.name,
                "credit": course.credit,
                "semester": course.semester,
                "department": course.department,
                "teachers": course.teachers,
                "course_level": course.course_level
            }
        return None
    return _execute_query(query)

def search_course_by_name(keyword: str):
    """通过课程名称模糊查询课程"""
    def query(db: Session):
        courses = db.query(Course).filter(Course.name.ilike(f"%{keyword}%")).all()
        return [{
            "code": c.code,
            "name": c.name,
            "credit": c.credit,
            "department": c.department,
            "teachers": c.teachers
        } for c in courses]
    return _execute_query(query)

def get_course_detail(course_code: str):
    """获取课程详细信息"""
    def query(db: Session):
        course = db.query(Course).filter(Course.code == course_code).first()
        if course:
            return {
                "code": course.code,
                "name": course.name,
                "credit": course.credit,
                "semester": course.semester,
                "department": course.department,
                "teachers": course.teachers,
                "course_level": course.course_level,
                "description": course.description,
                "objectives": course.objectives
            }
        return None
    return _execute_query(query)

def get_courses_by_semester(semester: str):
    """查询指定学期的课程"""
    def query(db: Session):
        courses = db.query(Course).filter(Course.semester.ilike(f"%{semester}%")).all()
        return [{"code": c.code, "name": c.name, "semester": c.semester} for c in courses]
    return _execute_query(query)

def get_courses_by_department(department: str):
    """查询指定院系的课程"""
    def query(db: Session):
        courses = db.query(Course).filter(Course.department.ilike(f"%{department}%")).all()
        return [{"code": c.code, "name": c.name, "department": c.department} for c in courses]
    return _execute_query(query)

def get_programme_requirements(programme_name: str):
    """查询专业的课程要求"""
    def query(db: Session):
        reqs = db.query(CourseRequirement).filter(CourseRequirement.programme.ilike(f"%{programme_name}%")).all()
        return [{
            "programme": r.programme,
            "stage": r.stage,
            "type": r.requirement_type,
            "course_code": r.course_code,
            "credit_requirement": r.credit_requirement
        } for r in reqs]
    return _execute_query(query)
