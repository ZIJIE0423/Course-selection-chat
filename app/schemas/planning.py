from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ScheduleSlotInput(BaseModel):
    weekday: int = Field(ge=1, le=7)
    periods: list[int] = Field(default_factory=list)
    weeks: str | None = None
    location: str | None = None

    @field_validator("periods")
    @classmethod
    def validate_periods(cls, value: list[int]) -> list[int]:
        if any(period <= 0 for period in value):
            raise ValueError("periods must contain positive integers")
        return sorted(set(value))


class CourseOfferingInput(BaseModel):
    external_offering_id: str | None = None
    course_code: str = Field(min_length=1, max_length=50)
    course_name: str = Field(min_length=1, max_length=255)
    credits: float | None = Field(default=None, ge=0)
    course_category: str | None = None
    department: str | None = None
    campus: str | None = None
    teacher_name: str | None = None
    schedules: list[ScheduleSlotInput] = Field(default_factory=list)
    capacity: int | None = Field(default=None, ge=0)
    remaining_capacity: int | None = Field(default=None, ge=0)
    source_updated_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_capacity(self):
        if (
            self.capacity is not None
            and self.remaining_capacity is not None
            and self.remaining_capacity > self.capacity
        ):
            raise ValueError("remaining_capacity cannot exceed capacity")
        return self


class CourseOfferingSnapshotImport(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    semester: str = Field(min_length=1, max_length=100)
    snapshot_id: str = Field(min_length=1, max_length=150)
    generated_at: datetime
    courses: list[CourseOfferingInput] = Field(min_length=1)


class CourseOfferingSnapshotResponse(BaseModel):
    snapshot_db_id: int
    snapshot_id: str
    semester: str
    record_count: int
    checksum: str
    idempotent_replay: bool = False


class ProgrammeRuleInput(BaseModel):
    rule_code: str = Field(min_length=1, max_length=100)
    rule_type: Literal["required", "elective_pool", "credit_requirement"]
    course_code: str | None = None
    course_category: str | None = None
    min_credits: float | None = Field(default=None, ge=0)
    required: bool = False
    priority: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.rule_type in {"required", "elective_pool"} and not (
            self.course_code or self.course_category
        ):
            raise ValueError("required/elective_pool rules need course_code or course_category")
        if self.rule_type == "credit_requirement" and not self.course_category:
            raise ValueError("credit_requirement rules need course_category")
        return self


class ProgrammeVersionImport(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    programme_code: str = Field(min_length=1, max_length=100)
    programme_name: str = Field(min_length=1, max_length=255)
    version_code: str = Field(min_length=1, max_length=100)
    applicable_grades: list[str] = Field(default_factory=list)
    issuing_unit: str | None = None
    published_at: datetime | None = None
    source_reference: str | None = None
    rules: list[ProgrammeRuleInput] = Field(default_factory=list)


class ProgrammeOptionView(BaseModel):
    id: int
    programme_code: str
    programme_name: str
    version_code: str
    applicable_grades: list[str]
    issuing_unit: str | None
    published_at: datetime | None


class StudentProfileUpsert(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=50)
    department: str = Field(min_length=1, max_length=255)
    major: str = Field(min_length=1, max_length=255)
    programme_version_id: int


class StudentProfileView(BaseModel):
    tenant_id: str
    user_id: str
    grade: str
    department: str
    major: str
    programme_version_id: int
    programme_name: str
    programme_version_code: str
    programme_confirmed_at: datetime | None


class HistoryRecordView(BaseModel):
    id: int
    course_code: str | None
    course_name: str
    semester: str | None
    credits: float | None
    completion_status: str
    status_source: str
    match_confidence: float
    matched_course_id: int | None
    confirmed_by_user: bool


class HistoryImportResponse(BaseModel):
    import_id: str
    status: str
    file_name: str
    parser_name: str
    record_count: int
    records: list[HistoryRecordView]
    warnings: list[str] = Field(default_factory=list)


class HistoryRecordCorrection(BaseModel):
    record_id: int
    course_code: str | None = None
    course_name: str | None = None
    semester: str | None = None
    credits: float | None = Field(default=None, ge=0)
    completion_status: Literal[
        "assumed_passed", "passed", "failed", "withdrawn", "retaking", "unknown"
    ] | None = None


class HistoryImportConfirmRequest(BaseModel):
    corrections: list[HistoryRecordCorrection] = Field(default_factory=list)


class ManualHistoryRecord(BaseModel):
    course_code: str | None = None
    course_name: str = Field(min_length=1, max_length=255)
    semester: str | None = None
    credits: float | None = Field(default=None, ge=0)


class ManualHistoryImportRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    records: list[ManualHistoryRecord] = Field(min_length=1)


class RequirementItem(BaseModel):
    type: str
    operator: Literal["eq", "neq", "in", "not_in", "gte", "lte", "contains"] = "eq"
    value: Any
    source_text: str | None = None

    @model_validator(mode="after")
    def validate_supported_requirement(self):
        supported_operators = {
            "campus": {"eq", "contains"},
            "course_category": {"eq", "contains"},
            "teacher_name": {"eq", "contains"},
            "weekday": {"eq"},
            "course_code": {"eq"},
            "credits": {"eq", "gte", "lte"},
            "avoid_period": {"neq"},
        }
        if self.type not in supported_operators:
            raise ValueError(f"unsupported requirement type: {self.type}")
        if self.operator not in supported_operators[self.type]:
            raise ValueError(
                f"operator '{self.operator}' is not supported for requirement type '{self.type}'"
            )
        if self.type in {"weekday", "avoid_period"}:
            try:
                numeric_value = int(self.value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{self.type} must be an integer") from exc
            if self.type == "weekday" and not 1 <= numeric_value <= 7:
                raise ValueError("weekday must be between 1 and 7")
            if self.type == "avoid_period" and numeric_value <= 0:
                raise ValueError("avoid_period must be positive")
            self.value = numeric_value
        elif self.type == "credits":
            try:
                numeric_value = float(self.value)
            except (TypeError, ValueError) as exc:
                raise ValueError("credits must be numeric") from exc
            if numeric_value < 0:
                raise ValueError("credits must be non-negative")
            self.value = numeric_value
        elif not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(f"{self.type} must be a non-empty string")
        return self


class HistoryCorrectionCandidate(BaseModel):
    record_id: int
    course_name: str
    current_status: str
    proposed_status: Literal["passed", "failed", "withdrawn", "retaking", "unknown"]


class ParsedRequirements(BaseModel):
    intent: Literal[
        "course_recommendation",
        "course_fact",
        "programme_question",
        "history_correction",
        "unknown",
    ]
    constraints: list[RequirementItem] = Field(default_factory=list)
    preferences: list[RequirementItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_preferences: list[str] = Field(default_factory=list)
    history_correction_candidates: list[HistoryCorrectionCandidate] = Field(default_factory=list)
    next_action: Literal["execute", "confirm_requirements", "confirm_history", "clarify", "reject"]


class PlanningSessionCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    snapshot_id: int
    programme_version_id: int | None = None
    query: str = Field(min_length=1, max_length=4000)


class PlanningSessionView(BaseModel):
    session_id: str
    state: str
    requirements: ParsedRequirements


class PlanningConfirmRequest(BaseModel):
    constraints: list[RequirementItem]
    preferences: list[RequirementItem] = Field(default_factory=list)


class HistoryStatusConfirmRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    record_id: int
    status: Literal["passed", "failed", "withdrawn", "retaking", "unknown"]


class RecommendationCard(BaseModel):
    offering_id: int
    course_code: str
    course_name: str
    credits: float | None
    course_category: str | None
    campus: str | None
    teacher_name: str | None
    schedules: list[dict[str, Any]]
    score: float
    match_reasons: list[str]
    warnings: list[str]
    evidence: list[dict[str, Any]]


class RecommendationResponse(BaseModel):
    planning_session_id: str
    snapshot_id: int
    total_candidates: int
    recommendations: list[RecommendationCard]
    warnings: list[str] = Field(default_factory=list)
