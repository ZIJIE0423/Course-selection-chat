import re
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, BaseMessage
from app.agent.llm import get_llm
from app.agent.policies import get_system_prompt
from app.tools.sql_tools import (
    search_course_by_code, search_course_by_name, get_course_detail,
)
from app.tools.rag_tools import (
    retrieve_official_docs, retrieve_student_reviews,
    retrieve_notices, format_rag_evidence,
)


class AgentState(TypedDict):
    messages: list[BaseMessage]
    context: str
    route: str
    source_type: str
    evidence: str
    used_tools: list[str]


def _extract_course_code(text: str) -> str | None:
    matches = re.findall(r"[A-Za-z0-9]{5,}", text)
    return matches[0] if matches else None


def router_node(state: AgentState):
    question = state["messages"][-1].content

    notice_keywords = ["最新公告", "最近通知", "选课通知", "公告", "最新选课"]
    factual_keywords = ["学分", "学期", "院系", "必修", "选修", "先修要求"]
    policy_keywords = ["培养方案要求", "选课规则", "如何选课", "选课流程", "课程类型", "流程", "方案", "指导"]
    review_keywords = ["怎么样", "水不水", "作业多不多", "给分", "推荐哪个", "评价", "好不好"]

    has_notice = any(kw in question for kw in notice_keywords)
    has_factual = _extract_course_code(question) or any(kw in question for kw in factual_keywords)
    has_policy = any(kw in question for kw in policy_keywords)
    has_review = any(kw in question for kw in review_keywords)

    if has_notice:
        return {"route": "notice_rag"}
    if has_factual and has_review:
        return {"route": "hybrid_sql_rag"}
    elif has_review:
        return {"route": "student_review_rag"}
    elif has_policy:
        return {"route": "official_doc_rag"}
    elif has_factual:
        return {"route": "mysql"}

    return {"route": "official_doc_rag"}


def mysql_query_node(state: AgentState):
    question = state["messages"][-1].content
    code = _extract_course_code(question)

    result = None
    if code:
        result = get_course_detail(code) or search_course_by_code(code)

    if not result:
        clean_q = re.sub(r"[^\w\s\u4e00-\u9fa5ⅣⅢⅡⅠ]", "", question)
        for stop_word in [
            "是什么", "是多少", "多少", "有哪些", "的", "课程", "学分", "学期",
            "吗", "有", "这门课", "怎么", "样", "什么", "课", "评价", "好不好", "水不水",
        ]:
            clean_q = clean_q.replace(stop_word, "")
        clean_q = clean_q.strip()
        if clean_q:
            result = search_course_by_name(clean_q)

    if result:
        context = f"【MySQL检索结果】: {json.dumps(result, ensure_ascii=False)}"
        return {
            "context": context,
            "source_type": "official_structured_db",
            "evidence": json.dumps(result, ensure_ascii=False),
            "used_tools": ["mysql_query"],
        }
    return {
        "context": "【MySQL检索结果】: 数据库中未找到相关课程信息。",
        "source_type": "official_structured_db",
        "evidence": "无数据",
        "used_tools": ["mysql_query"],
    }


def official_doc_rag_node(state: AgentState):
    question = state["messages"][-1].content
    docs = retrieve_official_docs(question)
    evidence = format_rag_evidence(docs)
    context = f"【官方文档检索结果】:\n{evidence}"
    return {
        "context": context,
        "source_type": "official_document_rag",
        "evidence": evidence,
        "used_tools": ["retrieve_official_docs"],
    }


def student_review_rag_node(state: AgentState):
    question = state["messages"][-1].content
    docs = retrieve_student_reviews(question)
    evidence = format_rag_evidence(docs)
    context = f"【学生评价检索结果】:\n{evidence}"
    return {
        "context": context,
        "source_type": "student_review_rag",
        "evidence": evidence,
        "used_tools": ["retrieve_student_reviews"],
    }


def notice_rag_node(state: AgentState):
    question = state["messages"][-1].content
    docs = retrieve_notices(question)
    if docs:
        evidence = format_rag_evidence(docs)
        context = f"【最新公告检索结果】:\n{evidence}"
    else:
        evidence = "无数据"
        context = "当前知识库未检索到最新公告，请以教务系统通知为准。"
    return {
        "context": context,
        "source_type": "official_notice_rag",
        "evidence": evidence,
        "used_tools": ["retrieve_notices"],
    }


def hybrid_sql_rag_node(state: AgentState):
    sql_result = mysql_query_node(state)
    rag_result = student_review_rag_node(state)
    context = f"{sql_result['context']}\n\n{rag_result['context']}"
    evidence = f"SQL Evidence:\n{sql_result['evidence']}\n\nRAG Evidence:\n{rag_result['evidence']}"
    return {
        "context": context,
        "source_type": "hybrid",
        "evidence": evidence,
        "used_tools": ["mysql_query", "retrieve_student_reviews"],
    }


def generate_node(state: AgentState):
    llm = get_llm()
    sys_prompt = get_system_prompt()

    context = state.get("context", "")

    prompt = sys_prompt + "\n\n参考上下文：\n" + context
    if "未检索到" in context or "未找到" in context:
        prompt += "\n\n注意：必须明确说明当前知识库未检索到足够依据，不可编造。"
    if "当前知识库未检索到最新公告" in context:
        prompt += "\n\n注意：请明确告知用户当前知识库未检索到最新公告，请以教务系统通知为准。"

    messages = [{"role": "system", "content": prompt}]
    messages.extend(state["messages"])

    response = llm.invoke(messages)
    return {"messages": [response]}


def build_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("mysql_query", mysql_query_node)
    workflow.add_node("official_doc_rag", official_doc_rag_node)
    workflow.add_node("student_review_rag", student_review_rag_node)
    workflow.add_node("hybrid_sql_rag", hybrid_sql_rag_node)
    workflow.add_node("notice_rag", notice_rag_node)
    workflow.add_node("generate", generate_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        lambda state: state["route"],
        {
            "mysql": "mysql_query",
            "official_doc_rag": "official_doc_rag",
            "student_review_rag": "student_review_rag",
            "hybrid_sql_rag": "hybrid_sql_rag",
            "notice_rag": "notice_rag",
        },
    )

    for node in ["mysql_query", "official_doc_rag", "student_review_rag", "hybrid_sql_rag", "notice_rag"]:
        workflow.add_edge(node, "generate")

    workflow.add_edge("generate", END)

    return workflow.compile()
