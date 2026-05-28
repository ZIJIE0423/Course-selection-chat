import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from langchain_core.messages import HumanMessage
from app.agent.workflow import build_workflow

workflow = build_workflow()

async def test_chat(query: str):
    print(f"\n[{query}]")
    state = {"messages": [HumanMessage(content=query)]}
    
    route = "unknown"
    source_type = "unknown"
    evidence = ""
    used_tools = []
    
    async for event in workflow.astream_events(state, version="v2"):
        kind = event["event"]
        
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
                
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = chunk.content
            if content:
                print(content, end="", flush=True)
                
    print(f"\n\n[Metadata] Route: {route}, Source: {source_type}, Tools: {used_tools}")
    if evidence and evidence != "无数据" and "暂未实现" not in evidence:
        print(f"[Evidence Snippet] {evidence[:150]}...")

async def main():
    queries = [
        "选课流程是什么？",
        "培养方案里公共基础课有哪些？",
        "张圆圆的大学英语怎么样？",
        "大学英语IV 哪个老师评价比较好？",
        "这门课作业多不多？",
        "不存在的课程评价如何？",
        "大学英语Ⅲ的学分是多少？这门课水不水？"
    ]
    for q in queries:
        await test_chat(q)
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())