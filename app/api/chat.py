from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
from langchain_core.messages import HumanMessage
from app.agent.workflow import build_workflow
from app.memory.need_summary import process_and_save_needs
import json

router = APIRouter()
workflow = build_workflow()

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

async def stream_agent_response(query: str, session_id: str):
    """流式处理 LangGraph Agent 响应"""
    state = {"messages": [HumanMessage(content=query)]}
    
    route = "unknown"
    source_type = "unknown"
    evidence = ""
    used_tools = []
    full_answer = ""
    
    # 异步执行 workflow，流式获取节点更新
    async for event in workflow.astream_events(state, version="v2"):
        kind = event["event"]
        
        # 捕获状态更新事件，获取路由和来源等信息
        if kind == "on_chain_end" and event["name"] in ["router", "mysql_query", "official_doc_rag", "student_review_rag", "hybrid_sql_rag"]:
            outputs = event["data"].get("output", {})
            if "route" in outputs:
                route = outputs["route"]
            if "source_type" in outputs:
                source_type = outputs["source_type"]
            if "evidence" in outputs:
                evidence = outputs["evidence"]
            if "used_tools" in outputs:
                used_tools = outputs["used_tools"]
                
            # 发送状态提示
            status_msg = ""
            if event["name"] == "router":
                status_msg = "正在识别问题类型..."
            elif event["name"] == "mysql_query":
                status_msg = "正在查询课程结构化数据库..."
            elif event["name"] == "official_doc_rag":
                status_msg = "正在检索官方文档..."
            elif event["name"] == "student_review_rag":
                status_msg = "正在检索学生评价..."
            elif event["name"] == "hybrid_sql_rag":
                status_msg = "正在查询课程库并检索学生评价..."
                
            if status_msg:
                yield f"data: {json.dumps({'type': 'status', 'content': status_msg}, ensure_ascii=False)}\n\n"
        
        # 捕获 LLM 节点的生成事件
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            
            content = chunk.content
            if content:
                full_answer += content
                response_data = {
                    "type": "answer",
                    "content": content,
                    "route": route,
                    "source_type": source_type,
                    "evidence": evidence,
                    "used_tools": used_tools,
                    "confidence": 0.9 # 默认置信度，可根据实际计算
                }
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
    
    # 在对话流结束时，调用记录和沉淀逻辑 (同步执行)
    need_summary_saved = process_and_save_needs(
        session_id=session_id,
        user_query=query,
        answer=full_answer,
        route=route,
        source_type=source_type,
        used_tools=used_tools,
        evidence_summary=evidence[:500] if evidence else ""
    )
    
    # 返回最后的标识
    meta_data = {
        "type": "meta",
        "need_summary_saved": need_summary_saved
    }
    yield f"data: {json.dumps(meta_data, ensure_ascii=False)}\n\n"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    return StreamingResponse(
        stream_agent_response(request.query, session_id),
        media_type="text/event-stream"
    )
