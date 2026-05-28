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
    
    async for event in workflow.astream_events(state, version="v2"):
        kind = event["event"]
        
        if kind == "on_chain_end" and event["name"] in ["router", "mysql_query", "rag_retrieve"]:
            outputs = event["data"].get("output", {})
            if "route" in outputs:
                route = outputs["route"]
            if "source_type" in outputs:
                source_type = outputs["source_type"]
            if "evidence" in outputs:
                evidence = outputs["evidence"]
                
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = chunk.content
            if content:
                print(content, end="", flush=True)
                
    print(f"\n[Metadata] Route: {route}, Source: {source_type}")
    if evidence and evidence != "无数据":
        print(f"[Evidence] {evidence[:100]}...")

async def main():
    queries = [
        "008301100001 是什么课？",
        "大学英语Ⅳ 的学分是多少？",
        "NOTEXIST999 有这门课吗？",
        "你们选课系统怎么用？"
    ]
    for q in queries:
        await test_chat(q)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
