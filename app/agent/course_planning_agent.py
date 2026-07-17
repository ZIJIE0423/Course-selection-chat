import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.planning import AcademicHistoryRecord
from app.schemas.planning import (
    HistoryCorrectionCandidate,
    ParsedRequirements,
    RequirementItem,
)


WEEKDAYS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "日": 7,
    "天": 7,
}


class CoursePlanningAgent:
    """Parse natural language into a deterministic planning contract.

    A configured model may be added behind this contract later. The first
    standardized release deliberately keeps a deterministic parser as the
    default and validates every output through ``ParsedRequirements``.
    """

    def parse(
        self,
        db: Session,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        has_programme: bool,
    ) -> ParsedRequirements:
        correction_candidates = self._history_corrections(
            db, tenant_id=tenant_id, user_id=user_id, query=query
        )
        if correction_candidates:
            return ParsedRequirements(
                intent="history_correction",
                history_correction_candidates=correction_candidates,
                next_action="confirm_history",
            )

        constraints: list[RequirementItem] = []
        preferences: list[RequirementItem] = []
        unsupported: list[str] = []

        campus_match = re.search(r"([\u4e00-\u9fff]{2,10})校区", query)
        if campus_match:
            campus_name = campus_match.group(1)
            campus_name = re.sub(
                r"^.*(?:周|星期)[一二三四五六日天](?:上午|下午|晚上)?",
                "",
                campus_name,
            )
            campus_name = re.sub(r"^(?:推荐|筛选|选择|想去|想在|在)", "", campus_name)
            constraints.append(
                RequirementItem(
                    type="campus",
                    value=f"{campus_name}校区",
                    source_text=campus_match.group(0),
                )
            )

        weekday_match = re.search(r"(?:周|星期)([一二三四五六日天])", query)
        if weekday_match:
            constraints.append(
                RequirementItem(
                    type="weekday",
                    value=WEEKDAYS[weekday_match.group(1)],
                    source_text=weekday_match.group(0),
                )
            )

        categories = [
            "通识选修",
            "专业选修",
            "公共基础",
            "专业基础",
            "必修",
            "限选",
            "选修",
        ]
        for category in categories:
            if category in query:
                constraints.append(
                    RequirementItem(
                        type="course_category",
                        operator="contains",
                        value=category,
                        source_text=category,
                    )
                )
                break

        credit_max = re.search(r"(?:不超过|最多|小于等于)\s*(\d+(?:\.\d+)?)\s*学分", query)
        credit_min = re.search(r"(?:至少|不少于|大于等于)\s*(\d+(?:\.\d+)?)\s*学分", query)
        if credit_max:
            constraints.append(
                RequirementItem(
                    type="credits",
                    operator="lte",
                    value=float(credit_max.group(1)),
                    source_text=credit_max.group(0),
                )
            )
        if credit_min:
            constraints.append(
                RequirementItem(
                    type="credits",
                    operator="gte",
                    value=float(credit_min.group(1)),
                    source_text=credit_min.group(0),
                )
            )

        teacher_match = re.search(r"([\u4e00-\u9fff]{2,4})老师", query)
        if teacher_match:
            constraints.append(
                RequirementItem(
                    type="teacher_name",
                    operator="contains",
                    value=teacher_match.group(1),
                    source_text=teacher_match.group(0),
                )
            )

        if any(keyword in query for keyword in ["不要早八", "不想早八", "避开早八"]):
            preferences.append(
                RequirementItem(type="avoid_period", operator="neq", value=1, source_text="早八")
            )
        if any(keyword in query for keyword in ["作业少", "作业较少", "轻松", "水课"]):
            unsupported.append("workload")
        if any(keyword in query for keyword in ["非闭卷", "不要闭卷", "论文考核", "无考试"]):
            unsupported.append("assessment_method")

        if any(keyword in query for keyword in ["推荐", "筛选", "选什么", "可以选", "可选课程"]):
            intent = "course_recommendation"
        elif any(keyword in query for keyword in ["培养方案", "毕业要求", "学分要求"]):
            intent = "programme_question"
        elif any(keyword in query for keyword in ["是什么课", "多少学分", "谁教"]):
            intent = "course_fact"
        else:
            intent = "unknown"

        missing = []
        if intent == "course_recommendation" and not has_programme:
            missing.append("programme_version_id")

        if missing:
            next_action = "clarify"
        elif intent == "course_recommendation":
            next_action = "confirm_requirements"
        elif intent in {"course_fact", "programme_question"}:
            next_action = "execute"
        else:
            next_action = "clarify"

        return ParsedRequirements(
            intent=intent,
            constraints=constraints,
            preferences=preferences,
            missing_fields=missing,
            unsupported_preferences=sorted(set(unsupported)),
            next_action=next_action,
        )

    def _history_corrections(
        self,
        db: Session,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
    ) -> list[HistoryCorrectionCandidate]:
        status = None
        if any(keyword in query for keyword in ["没过", "未通过", "挂了", "挂科"]):
            status = "failed"
        elif any(keyword in query for keyword in ["退课", "退掉", "撤课"]):
            status = "withdrawn"
        elif "重修" in query:
            status = "retaking"
        elif any(keyword in query for keyword in ["通过了", "过了"]):
            status = "passed"
        if not status:
            return []

        records = (
            db.query(AcademicHistoryRecord)
            .filter(
                AcademicHistoryRecord.tenant_id == tenant_id,
                AcademicHistoryRecord.user_id == user_id,
            )
            .all()
        )
        scored = []
        for record in records:
            if record.course_name in query or (record.course_code and record.course_code in query):
                score = 1.0
            else:
                score = SequenceMatcher(None, record.course_name, query).ratio()
            if score >= 0.35:
                scored.append((score, record))
        if not scored:
            return []
        best_score = max(score for score, _ in scored)
        return [
            HistoryCorrectionCandidate(
                record_id=record.id,
                course_name=record.course_name,
                current_status=record.completion_status,
                proposed_status=status,
            )
            for score, record in scored
            if score >= max(0.35, best_score - 0.1)
        ][:3]
