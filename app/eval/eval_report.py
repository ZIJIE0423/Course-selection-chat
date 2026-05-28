import json
import os
from datetime import datetime

def generate_markdown_report(metrics, results, output_path):
    total = len(results)
    
    # Categorize by expected route
    route_stats = {}
    for r in results:
        route = r["expected_route"]
        if route not in route_stats:
            route_stats[route] = {"total": 0, "correct_route": 0, "keyword_hit": 0.0}
        route_stats[route]["total"] += 1
        if r["predicted_route"] == route:
            route_stats[route]["correct_route"] += 1
        
        kw = r["gold_answer_keywords"]
        hit = sum(1 for k in kw if k in r["answer"]) / len(kw) if kw else 1.0
        route_stats[route]["keyword_hit"] += hit
        
    for route in route_stats:
        route_stats[route]["keyword_hit_avg"] = route_stats[route]["keyword_hit"] / route_stats[route]["total"]
        
    failed_cases = [r for r in results if r["predicted_route"] != r["expected_route"] or (
        r["should_abstain"] != any(kw in r["answer"] for kw in ["未找到", "未检索到", "不足", "没有找到"])
    )]

    md = f"""# 选课系统评测报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**总测试样例数**: {total}

## 1. 全量核心指标得分
- **路由分类准确率 (route_accuracy)**: {metrics['route_accuracy']:.2%}
- **数据源类型匹配准确率 (source_type_accuracy)**: {metrics['source_type_accuracy']:.2%}
- **拒答逻辑准确率 (abstain_accuracy)**: {metrics['abstain_accuracy']:.2%}
- **证据引用覆盖率 (citation_coverage)**: {metrics['citation_coverage']:.2%}
- **幻觉检测标识率 (hallucination_flag)**: {metrics['hallucination_flag']:.2%}
- **核心关键词命中比率 (keyword_hit_rate)**: {metrics['keyword_hit_rate']:.2%}
- **工具调用准确率 (tool_usage_accuracy)**: {metrics['tool_usage_accuracy']:.2%}

*(注：faithfulness_score 与 context_precision_score 为预留 RAGAS 字段，暂未计算)*

## 2. 不同问题类型的细分表现
"""
    for route, stat in route_stats.items():
        md += f"### {route}\n"
        md += f"- 测试数量: {stat['total']}\n"
        md += f"- 路由准确率: {stat['correct_route'] / stat['total']:.2%}\n"
        md += f"- 关键词命中率: {stat['keyword_hit_avg']:.2%}\n\n"
        
    md += "## 3. 失败案例梳理\n\n"
    if not failed_cases:
        md += "恭喜，所有重点指标测试均符合预期！\n"
    else:
        for i, fc in enumerate(failed_cases[:10]):
            md += f"**案例 {i+1}**:\n"
            md += f"- **问题**: {fc['query']}\n"
            md += f"- **预期路由**: {fc['expected_route']} | **实际路由**: {fc['predicted_route']}\n"
            md += f"- **预期应拒答**: {fc['should_abstain']}\n"
            md += f"- **系统回答**: {fc['answer'][:150]}...\n\n"
            
    md += """## 4. 针对性优化建议
1. 对于路由错误的案例，可优化 `app/agent/workflow.py` 中的关键词正则或引入大模型意图识别。
2. 对于幻觉现象，可继续强化 `policies.py` 中的 prompt，严格要求在无证据时回复“未找到”。
3. 可进一步细化数据清洗，提高关键词的命中率。
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
