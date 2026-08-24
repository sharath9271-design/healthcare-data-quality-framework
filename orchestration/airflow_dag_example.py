"""Illustrative Airflow DAG — NOT executed by this repo's CI.

This repo's pipeline.py is deliberately orchestration-agnostic: it's a
plain Python entrypoint that any scheduler can call. This file shows the
shape that call takes in a production Airflow deployment, running the
same pipeline.py against a real warehouse (WAREHOUSE_URL pointed at
Snowflake or Databricks) on a daily schedule instead of the local SQLite
default used for tests and CI.

Requires `apache-airflow` in whatever environment actually runs it; it is
intentionally not a dependency of this repo.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="healthcare_data_quality_pipeline",
    description="Nightly ETL + data-quality checks for the patient/encounter warehouse",
    schedule="0 3 * * *",  # 03:00 UTC daily
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2},
    tags=["data-quality", "healthcare"],
) as dag:
    run_pipeline = BashOperator(
        task_id="run_etl_and_quality_checks",
        bash_command="python /opt/healthcare-data-quality-framework/pipeline.py",
        env={"WAREHOUSE_URL": "{{ var.value.warehouse_url }}"},
    )
