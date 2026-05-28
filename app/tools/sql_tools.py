from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.mysql import SessionLocal
from app.models.course import Course, Programme, CourseRequirement

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
