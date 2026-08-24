"""Unit tests for the check functions themselves, using small hand-built
DataFrames rather than the generated dataset — these pin down each
check's pass/fail logic in isolation, independent of what the synthetic
data generator happens to produce."""

from __future__ import annotations

import pandas as pd

from src.quality_checks import (
    check_encounter_after_birth,
    check_not_null,
    check_referential_integrity,
    check_row_count_reconciliation,
    check_schema,
    check_unique,
    check_valid_enum,
)


def test_check_schema_passes_when_all_columns_present():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = check_schema(df, ["a", "b"], table="t")
    assert result.passed


def test_check_schema_fails_and_lists_missing_columns():
    df = pd.DataFrame({"a": [1]})
    result = check_schema(df, ["a", "b"], table="t")
    assert not result.passed
    assert result.failing_examples == ["b"]


def test_check_not_null_detects_blank_and_missing_values():
    df = pd.DataFrame({"birth_date": ["1990-01-01", "", None]})
    result = check_not_null(df, "birth_date", table="patients")
    assert not result.passed
    assert result.failing_count == 2


def test_check_not_null_passes_when_column_is_fully_populated():
    df = pd.DataFrame({"birth_date": ["1990-01-01", "2000-05-05"]})
    result = check_not_null(df, "birth_date", table="patients")
    assert result.passed


def test_check_unique_detects_duplicates():
    df = pd.DataFrame({"id": ["a", "b", "b", "c"]})
    result = check_unique(df, "id", table="t")
    assert not result.passed
    assert result.failing_examples == ["b"]


def test_check_referential_integrity_finds_orphans():
    parent = pd.DataFrame({"patient_id": ["p1", "p2"]})
    child = pd.DataFrame({"encounter_id": ["e1", "e2"], "patient_id": ["p1", "does-not-exist"]})
    result = check_referential_integrity(child, "patient_id", parent, "patient_id", relationship="child->parent")
    assert not result.passed
    assert result.failing_examples == ["does-not-exist"]


def test_check_referential_integrity_passes_when_all_keys_resolve():
    parent = pd.DataFrame({"patient_id": ["p1", "p2"]})
    child = pd.DataFrame({"encounter_id": ["e1"], "patient_id": ["p1"]})
    result = check_referential_integrity(child, "patient_id", parent, "patient_id", relationship="child->parent")
    assert result.passed


def test_check_valid_enum_flags_unexpected_values():
    df = pd.DataFrame({"gender": ["female", "male", "M"]})
    result = check_valid_enum(df, "gender", {"female", "male", "other", "unknown"}, table="patients")
    assert not result.passed
    assert result.failing_examples == ["M"]


def test_check_row_count_reconciliation_detects_mismatch():
    source = pd.DataFrame({"id": [1, 2, 3]})
    target = pd.DataFrame({"id": [1, 2]})
    result = check_row_count_reconciliation(source, target, relationship="a->b")
    assert not result.passed
    assert result.failing_count == 1


def test_check_encounter_after_birth_flags_impossible_dates():
    patients = pd.DataFrame({"patient_id": ["p1"], "birth_date": ["2020-01-01"]})
    encounters = pd.DataFrame(
        {"encounter_id": ["e1"], "patient_id": ["p1"], "encounter_date": ["2010-01-01"]}
    )
    result = check_encounter_after_birth(encounters, patients)
    assert not result.passed
    assert result.failing_examples == ["e1"]


def test_check_encounter_after_birth_passes_for_valid_dates():
    patients = pd.DataFrame({"patient_id": ["p1"], "birth_date": ["2000-01-01"]})
    encounters = pd.DataFrame(
        {"encounter_id": ["e1"], "patient_id": ["p1"], "encounter_date": ["2020-01-01"]}
    )
    result = check_encounter_after_birth(encounters, patients)
    assert result.passed
