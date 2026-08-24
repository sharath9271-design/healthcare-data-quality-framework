#!/usr/bin/env python3
"""CLI entrypoint: run the ETL pipeline, run every data-quality check
against its output, write a JSON report, and exit non-zero if any check
failed — so `python pipeline.py` is a single command CI (or a human) can
run to get a pass/fail signal plus a full report.

Usage:
    python pipeline.py                 # run ETL + checks against data/raw
    python pipeline.py --regenerate    # also regenerate the synthetic raw data first
"""

from __future__ import annotations

import argparse
import sys

from src.db import get_engine
from src.etl import run_pipeline
from src.quality_checks import (
    check_encounter_after_birth,
    check_not_null,
    check_referential_integrity,
    check_row_count_reconciliation,
    check_schema,
    check_unique,
    check_valid_enum,
)
from src.report import build_report, print_summary, write_report


def run_all_checks(layers: dict) -> list:
    patients = layers["patients"]
    encounters = layers["encounters"]
    conditions = layers["conditions"]
    curated = layers["patient_encounter_summary"]

    results = [
        check_schema(patients, ["patient_id", "first_name", "last_name", "gender", "birth_date", "state"], table="patients"),
        check_schema(encounters, ["encounter_id", "patient_id", "encounter_type", "encounter_date", "provider"], table="encounters"),
        check_schema(conditions, ["condition_id", "encounter_id", "snomed_code", "description"], table="conditions"),
        check_not_null(patients, "birth_date", table="patients"),
        check_not_null(patients, "patient_id", table="patients"),
        check_unique(patients, "patient_id", table="patients"),
        check_unique(encounters, "encounter_id", table="encounters"),
        check_valid_enum(patients, "gender", {"female", "male", "other", "unknown"}, table="patients"),
        check_valid_enum(
            encounters, "encounter_type", {"outpatient", "inpatient", "emergency", "telehealth", "wellness"}, table="encounters"
        ),
        check_referential_integrity(
            encounters, "patient_id", patients, "patient_id", relationship="encounters -> patients"
        ),
        check_referential_integrity(
            conditions, "encounter_id", encounters, "encounter_id", relationship="conditions -> encounters"
        ),
        check_encounter_after_birth(encounters, patients),
        check_row_count_reconciliation(patients, curated, relationship="patients -> patient_encounter_summary"),
    ]
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true", help="regenerate synthetic raw data before running")
    args = parser.parse_args()

    if args.regenerate:
        from src.generate_synthetic_data import main as regenerate

        regenerate()

    engine = get_engine()
    layers = run_pipeline(engine)
    results = run_all_checks(layers)

    report = build_report(results)
    write_report(report)
    print_summary(report)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
