"""Turn a list of CheckResults into a JSON report, and keep an append-only
history log that the Streamlit dashboard reads to show pass-rate trends
over time."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

from src.quality_checks import CheckResult

REPORTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "reports"
HISTORY_PATH = REPORTS_DIR / "quality_report_history.jsonl"
LATEST_PATH = REPORTS_DIR / "latest_quality_report.json"


def build_report(results: list[CheckResult]) -> dict:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks_passed": passed,
        "checks_total": total,
        "pass_rate": round(passed / total, 4) if total else 1.0,
        "results": [r.to_dict() for r in results],
    }


def write_report(report: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_PATH.write_text(json.dumps(report, indent=2))
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(report) + "\n")


def print_summary(report: dict) -> None:
    print(f"\nData quality report — {report['generated_at']}")
    print(f"  {report['checks_passed']}/{report['checks_total']} checks passed ({report['pass_rate']:.0%})\n")
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['name']} — {result['details']}")
