"""End-to-end tests: run the real ETL against the committed synthetic
data/raw/*.csv and confirm the checks catch the specific, known problems
seeded into that dataset by generate_synthetic_data.py (one missing
birth_date, one invalid gender code, one orphaned encounter, one
duplicate encounter_id). This is what proves the framework actually
detects real problems, not just problems constructed for a unit test.
"""

from __future__ import annotations

from src.quality_checks import (
    check_encounter_after_birth,
    check_not_null,
    check_referential_integrity,
    check_row_count_reconciliation,
    check_unique,
    check_valid_enum,
)


def test_curated_table_has_one_row_per_patient(pipeline_layers):
    patients = pipeline_layers["patients"]
    curated = pipeline_layers["patient_encounter_summary"]
    assert len(curated) == len(patients)


def test_row_count_reconciliation_passes_patients_to_curated(pipeline_layers):
    result = check_row_count_reconciliation(
        pipeline_layers["patients"], pipeline_layers["patient_encounter_summary"], relationship="patients -> curated"
    )
    assert result.passed


def test_seeded_missing_birth_date_is_caught(pipeline_layers):
    result = check_not_null(pipeline_layers["patients"], "birth_date", table="patients")
    assert not result.passed
    assert result.failing_count == 1


def test_seeded_invalid_gender_code_is_caught(pipeline_layers):
    result = check_valid_enum(
        pipeline_layers["patients"], "gender", {"female", "male", "other", "unknown"}, table="patients"
    )
    assert not result.passed
    assert "M" in result.failing_examples


def test_seeded_orphaned_encounter_is_caught(pipeline_layers):
    result = check_referential_integrity(
        pipeline_layers["encounters"],
        "patient_id",
        pipeline_layers["patients"],
        "patient_id",
        relationship="encounters -> patients",
    )
    assert not result.passed
    assert result.failing_count == 1


def test_seeded_duplicate_encounter_id_is_caught(pipeline_layers):
    result = check_unique(pipeline_layers["encounters"], "encounter_id", table="encounters")
    assert not result.passed
    assert result.failing_count == 1


def test_all_encounters_occur_after_patient_birth_once_missing_row_excluded(pipeline_layers):
    # The one patient with a missing birth_date is naturally excluded by
    # the inner merge inside this check, so this isolates the
    # date-ordering rule from the missing-birth-date problem above.
    result = check_encounter_after_birth(pipeline_layers["encounters"], pipeline_layers["patients"])
    assert result.passed
