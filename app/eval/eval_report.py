"""Markdown reporting for M1 acceptance evaluation."""

from __future__ import annotations

from datetime import datetime

from app.eval.metrics import M1_THRESHOLDS


LABELS = {
    "qualified_evidence_fact_accuracy": "合格证据事实准确率",
    "risk_evidence_safe_refusal_rate": "风险证据安全拒答率",
    "recommendation_hard_constraint_satisfaction_rate": "推荐硬约束满足率",
    "official_evidence_coverage": "官方结构化证据覆盖率",
    "execution_success_rate": "评测执行成功率",
}


def generate_markdown_report(metrics, status, results, output_path):
    lines = [
        "# M1 结构化数据与安全规划验收报告", "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**总测试样例数**: {len(results)}",
        f"**合格证据事实样例**: {metrics['qualified_fact_case_count']}",
        f"**风险证据拒答样例**: {metrics['risk_refusal_case_count']}",
        f"**推荐硬约束样例**: {metrics['recommendation_case_count']}",
        "**评测边界**: 结构化课程快照和规划服务；不调用 RAG、LLM 或外部网络。", "",
        "## 验收指标", "",
        "| 指标 | 结果 | 门槛 | 状态 |", "|---|---:|---:|---|",
    ]
    for name, label in LABELS.items():
        threshold = M1_THRESHOLDS[name]
        lines.append(f"| {label} | {metrics[name]:.2%} | ≥ {threshold:.0%} | {'通过' if status[name] else '未通过'} |")
    lines.extend([f"| SQL/规划执行延迟 P95 | {metrics['latency_p95_ms']:.3f} ms | 信息项 | — |", "", "## 场景分布", ""])
    scenarios = {}
    for result in results:
        scenarios[result["scenario"]] = scenarios.get(result["scenario"], 0) + 1
    for scenario, count in sorted(scenarios.items()):
        lines.append(f"- {scenario}: {count}")
    lines.extend(["", "## 失败案例", ""])
    failures = [r for r in results if r.get("error") or not r.get("case_passed")]
    if not failures:
        lines.append("无。所有 M1 事实、风险拒答和硬约束用例均满足验收条件。")
    else:
        for result in failures[:20]:
            lines.extend([f"- {result['case_id']}：{result['query']}", f"  - 结果：{result.get('outcome')}", f"  - 错误：{result.get('error', '预期与实际不一致')}"])
    lines.extend(["", "## 口径说明", "", "合格证据事实准确率仅统计具备完整、未过期官方结构化证据的 70 条事实查询。风险证据安全拒答率覆盖查无记录、过期快照、关键字段缺失、活动快照冲突和多记录歧义共 105 条用例；任何返回推荐卡片均判失败。推荐硬约束满足率覆盖 25 条推荐用例，任一卡片违反已确认硬约束即判失败。", ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
