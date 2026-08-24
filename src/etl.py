"""Raw CSV -> staging -> curated ETL, using pandas for transformation and
SQLAlchemy for the warehouse write — the same shape this pipeline would
have on Spark/Databricks, just at a scale that runs in a few seconds
locally and in CI.

Layers:
  raw       data/raw/*.csv                      — untouched source extract
  staging   *_staging tables                    — typed, 1:1 with raw
  curated   patient_encounter_summary            — one row per patient,
                                                    aggregated + business
                                                    rules applied
"""

from __future__ import annotations

import pathlib

import pandas as pd
from sqlalchemy import Engine

RAW_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"


def _load_raw() -> dict[str, pd.DataFrame]:
    return {
        "patients": pd.read_csv(RAW_DIR / "patients.csv", dtype=str),
        "encounters": pd.read_csv(RAW_DIR / "encounters.csv", dtype=str),
        "conditions": pd.read_csv(RAW_DIR / "conditions.csv", dtype=str),
    }


def load_to_staging(engine: Engine) -> dict[str, pd.DataFrame]:
    """Write raw CSVs into `<name>_staging` tables, unmodified (typed as
    strings, matching the raw extract) so staging is always a faithful,
    queryable copy of what was actually received."""
    raw = _load_raw()
    for name, df in raw.items():
        df.to_sql(f"{name}_staging", engine, if_exists="replace", index=False)
    return raw


def build_curated(engine: Engine, staging: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Aggregate staging into a curated patient_encounter_summary table:
    one row per patient with encounter counts and most recent visit."""
    patients = staging["patients"].copy()
    encounters = staging["encounters"].copy()
    conditions = staging["conditions"].copy()

    encounters["encounter_date"] = pd.to_datetime(encounters["encounter_date"], errors="coerce")

    encounter_stats = (
        encounters.groupby("patient_id")
        .agg(
            encounter_count=("encounter_id", "count"),
            most_recent_encounter=("encounter_date", "max"),
        )
        .reset_index()
    )

    condition_counts = (
        conditions.merge(encounters[["encounter_id", "patient_id"]], on="encounter_id", how="left")
        .groupby("patient_id")
        .agg(condition_count=("condition_id", "count"))
        .reset_index()
    )

    curated = (
        patients.merge(encounter_stats, on="patient_id", how="left")
        .merge(condition_counts, on="patient_id", how="left")
    )
    curated["encounter_count"] = curated["encounter_count"].fillna(0).astype(int)
    curated["condition_count"] = curated["condition_count"].fillna(0).astype(int)
    curated["most_recent_encounter"] = curated["most_recent_encounter"].astype(str)

    curated.to_sql("patient_encounter_summary", engine, if_exists="replace", index=False)
    return curated


def run_pipeline(engine: Engine) -> dict[str, pd.DataFrame]:
    """Run the full raw -> staging -> curated pipeline and return every
    layer's DataFrame, keyed for convenient use by the quality checks."""
    staging = load_to_staging(engine)
    curated = build_curated(engine, staging)
    return {**staging, "patient_encounter_summary": curated}
