"""Streamlit dashboard over the quality-report history log.

Run locally after at least one `python pipeline.py` run has produced
reports/quality_report_history.jsonl:

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd
import streamlit as st

HISTORY_PATH = pathlib.Path(__file__).resolve().parents[1] / "reports" / "quality_report_history.jsonl"

st.set_page_config(page_title="Data Quality Dashboard", layout="wide")
st.title("Healthcare Data Quality Dashboard")

if not HISTORY_PATH.exists():
    st.info("No report history yet — run `python pipeline.py` at least once, then refresh this page.")
    st.stop()

runs = [json.loads(line) for line in HISTORY_PATH.read_text().splitlines() if line.strip()]
history_df = pd.DataFrame(
    [{"generated_at": r["generated_at"], "pass_rate": r["pass_rate"], "checks_passed": r["checks_passed"], "checks_total": r["checks_total"]} for r in runs]
)
history_df["generated_at"] = pd.to_datetime(history_df["generated_at"])

latest = runs[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Latest pass rate", f"{latest['pass_rate']:.0%}")
col2.metric("Checks passed", f"{latest['checks_passed']} / {latest['checks_total']}")
col3.metric("Total runs", len(runs))

st.subheader("Pass rate over time")
st.line_chart(history_df.set_index("generated_at")["pass_rate"])

st.subheader("Latest run — check-by-check")
latest_df = pd.DataFrame(latest["results"])
latest_df["status"] = latest_df["passed"].map({True: "PASS", False: "FAIL"})
st.dataframe(
    latest_df[["status", "name", "details", "failing_count"]],
    use_container_width=True,
    hide_index=True,
)

failing = latest_df[~latest_df["passed"]]
if len(failing):
    st.subheader(f"⚠ {len(failing)} check(s) currently failing")
    for _, row in failing.iterrows():
        with st.expander(row["name"]):
            st.write(row["details"])
            st.write("Examples:", row["failing_examples"])
