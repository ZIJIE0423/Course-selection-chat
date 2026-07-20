import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_m1_structured_suite_meets_acceptance_thresholds(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "app/eval/run_eval.py",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = (tmp_path / "eval_summary.md").read_text(encoding="utf-8")
    results = json.loads((tmp_path / "eval_results.json").read_text(encoding="utf-8"))
    assert len(results) == 200
    assert "合格证据事实准确率 | 100.00%" in report
    assert "风险证据安全拒答率 | 100.00%" in report
    assert "推荐硬约束满足率 | 100.00%" in report
    assert "官方结构化证据覆盖率 | 100.00%" in report
    assert all("error" not in result for result in results)
