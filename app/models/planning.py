from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.mysql import Base


class ProgrammeVersion(Base):
    __tablename__ = "programme_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "programme_code", "version_code", name="uq_programme_version"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    programme_code = Column(String(100), nullable=False, index=True)
    programme_name = Column(String(255), nullable=False)
    version_code = Column(String(100), nullable=False)
    applicable_grades = Column(Text, nullable=False, default="[]")
    issuing_unit = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    source_reference = Column(String(512), nullable=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class ProgrammeRule(Base):
    __tablename__ = "programme_rules"

    id = Column(Integer, primary_key=True)
    programme_version_id = Column(Integer, ForeignKey("programme_versions.id"), nullable=False, index=True)
    rule_code = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False, index=True)
    course_code = Column(String(50), nullable=True, index=True)
    course_category = Column(String(100), nullable=True, index=True)
    min_credits = Column(Float, nullable=True)
    required = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    rule_metadata = Column(Text, nullable=False, default="{}")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_student_profile_identity"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    grade = Column(String(50), nullable=True)
    department = Column(String(255), nullable=True)
    major = Column(String(255), nullable=True)
    programme_version_id = Column(Integer, ForeignKey("programme_versions.id"), nullable=True, index=True)
    programme_confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class CourseOfferingSnapshot(Base):
    __tablename__ = "course_offering_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_snapshot_id", name="uq_course_offering_snapshot"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    semester = Column(String(100), nullable=False, index=True)
    external_snapshot_id = Column(String(150), nullable=False)
    generated_at = Column(DateTime, nullable=False)
    checksum = Column(String(64), nullable=False)
    status = Column(String(30), nullable=False, default="active", index=True)
    record_count = Column(Integer, nullable=False, default=0)
    imported_at = Column(DateTime, nullable=False, default=func.now())


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "external_offering_id", name="uq_snapshot_offering"),
    )

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("course_offering_snapshots.id"), nullable=False, index=True)
    external_offering_id = Column(String(150), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    course_name = Column(String(255), nullable=False, index=True)
    credits = Column(Float, nullable=True)
    course_category = Column(String(100), nullable=True, index=True)
    department = Column(String(255), nullable=True)
    campus = Column(String(100), nullable=True, index=True)
    teacher_name = Column(String(255), nullable=True, index=True)
    schedule_json = Column(Text, nullable=False, default="[]")
    capacity = Column(Integer, nullable=True)
    remaining_capacity = Column(Integer, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    extra_data = Column(Text, nullable=False, default="{}")


class AcademicHistoryImport(Base):
    __tablename__ = "academic_history_imports"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(30), nullable=False)
    file_sha256 = Column(String(64), nullable=False, index=True)
    parser_name = Column(String(100), nullable=False)
    status = Column(String(40), nullable=False, default="processing", index=True)
    record_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    confirmed_at = Column(DateTime, nullable=True)


class AcademicHistoryRecord(Base):
    __tablename__ = "academic_history_records"

    id = Column(Integer, primary_key=True)
    import_id = Column(String(36), ForeignKey("academic_history_imports.id"), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    course_code = Column(String(50), nullable=True, index=True)
    course_name = Column(String(255), nullable=False, index=True)
    semester = Column(String(100), nullable=True)
    credits = Column(Float, nullable=True)
    completion_status = Column(String(40), nullable=False, default="assumed_passed", index=True)
    status_source = Column(String(80), nullable=False, default="historical_timetable_default")
    match_confidence = Column(Float, nullable=False, default=0.0)
    confirmed_by_user = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class PlanningSession(Base):
    __tablename__ = "planning_sessions"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("course_offering_snapshots.id"), nullable=False, index=True)
    programme_version_id = Column(Integer, ForeignKey("programme_versions.id"), nullable=True, index=True)
    raw_query = Column(Text, nullable=False)
    requirements_json = Column(Text, nullable=False, default="{}")
    state = Column(String(40), nullable=False, default="awaiting_confirmation", index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
