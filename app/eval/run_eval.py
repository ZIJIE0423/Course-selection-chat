import json
import os
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from langchain_core.messages import HumanMessage
from app.agent.workflow import build_workflow
from app.eval.metrics import calculate_all_metrics
from app.eval.eval_report import generate_markdown_report

workflow = build_workflow()

async def run_single_case(test_case):
    query = test_case["query"]
    state = {"messages": [HumanMessage(content=query)]}
    
    route = "unknown"
    source_type = "unknown"
    used_tools = []
    full_answer = ""
    
    async for event in workflow.astream_events(state, version="v2"):
        kind = event["event"]
        
        if kind == "on_chain_end" and event["name"] in ["router", "mysql_query", "official_doc_rag", "student_review_rag", "hybrid_sql_rag"]:
            outputs = event["data"].get("output", {})
            if "route" in outputs:
                route = outputs["route"]
            if "source_type" in outputs:
                source_type = outputs["source_type"]
            if "used_tools" in outputs:
                used_tools = outputs["used_tools"]
                
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                full_answer += chunk.content

    result = {
        "query": query,
        "expected_route": test_case["expected_route"],
        "predicted_route": route,
        "expected_source_type": test_case["expected_source_type"],
        "predicted_source_type": source_type,
        "gold_answer_keywords": test_case["gold_answer_keywords"],
        "should_abstain": test_case["should_abstain"],
        "gold_evidence_type": test_case["gold_evidence_type"],
        "answer": full_answer,
        "used_tools": used_tools
    }
    return result

async def main():
    eval_dir = project_root / 'app' / 'eval'
    out_dir = project_root / 'eval_outputs'
    os.makedirs(out_dir, exist_ok=True)
    
    cases_path = eval_dir / 'test_cases.jsonl'
    results_path = out_dir / 'eval_results.json'
    report_path = out_dir / 'eval_summary.md'
    
    test_cases = []
    with open(cases_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))
                
    print(f"Loaded {len(test_cases)} test cases. Running evaluation...")
    
    results = []
    for i, tc in enumerate(test_cases):
        print(f"[{i+1}/{len(test_cases)}] Evaluating: {tc['query']}")
        res = await run_single_case(tc)
        results.append(res)
        
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("\nCalculating metrics...")
    metrics = calculate_all_metrics(results)
    
    print("Generating report...")
    generate_markdown_report(metrics, results, report_path)
    
    print(f"Evaluation complete. Report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
