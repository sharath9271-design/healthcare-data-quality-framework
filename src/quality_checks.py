"""A small, dependency-free data-quality rule engine.

Each check takes DataFrame(s) and returns a CheckResult. Checks never
raise on a data problem — they report it — so a full run always produces
a complete picture of the data's health rather than stopping at the
first failure. Deciding which failures are build-breaking is left to the
caller (see pipeline.py and tests/test_quality_checks.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str
    failing_count: int = 0
    failing_examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "failing_count": self.failing_count,
            "failing_examples": self.failing_examples[:5],
        }


def check_schema(df: pd.DataFrame, expected_columns: list[str], *, table: str) -> CheckResult:
    missing = [c for c in expected_columns if c not in df.columns]
    passed = not missing
    return CheckResult(
        name=f"schema:{table}",
        passed=passed,
        details="all expected columns present" if passed else f"missing columns: {missing}",
        failing_count=len(missing),
        failing_examples=missing,
    )


def check_not_null(df: pd.DataFrame, column: str, *, table: str) -> CheckResult:
    missing_mask = df[column].isna() | (df[column].astype(str).str.strip() == "")
    failing_ids = df.loc[missing_mask].index.astype(str).tolist()
    passed = bool(missing_mask.sum() == 0)
    return CheckResult(
        name=f"not_null:{table}.{column}",
        passed=passed,
        details=f"{missing_mask.sum()} of {len(df)} rows have a blank {column}",
        failing_count=int(missing_mask.sum()),
        failing_examples=failing_ids,
    )


def check_unique(df: pd.DataFrame, column: str, *, table: str) -> CheckResult:
    dupes = df[df.duplicated(subset=[column], keep=False)][column].tolist()
    passed = len(dupes) == 0
    return CheckResult(
        name=f"unique:{table}.{column}",
        passed=passed,
        details=f"{len(set(dupes))} duplicate {column} value(s)" if dupes else f"all {column} values unique",
        failing_count=len(set(dupes)),
        failing_examples=sorted(set(dupes)),
    )


def check_referential_integrity(
    child_df: pd.DataFrame,
    child_key: str,
    parent_df: pd.DataFrame,
    parent_key: str,
    *,
    relationship: str,
) -> CheckResult:
    valid_parents = set(parent_df[parent_key])
    orphans = child_df[~child_df[child_key].isin(valid_parents)][child_key].tolist()
    passed = len(orphans) == 0
    return CheckResult(
        name=f"referential_integrity:{relationship}",
        passed=passed,
        details=f"{len(orphans)} row(s) reference a {child_key} not present in the parent table"
        if orphans
        else "all foreign keys resolve",
        failing_count=len(orphans),
        failing_examples=orphans,
    )


def check_valid_enum(df: pd.DataFrame, column: str, allowed: set[str], *, table: str) -> CheckResult:
    invalid = df[~df[column].isin(allowed) & df[column].notna() & (df[column].astype(str).str.strip() != "")]
    values = sorted(invalid[column].unique().tolist())
    passed = len(values) == 0
    return CheckResult(
        name=f"valid_enum:{table}.{column}",
        passed=passed,
        details=f"unexpected values {values} (allowed: {sorted(allowed)})" if values else "all values in allowed set",
        failing_count=len(invalid),
        failing_examples=values,
    )


def check_row_count_reconciliation(
    source_df: pd.DataFrame, target_df: pd.DataFrame, *, relationship: str
) -> CheckResult:
    passed = len(source_df) == len(target_df)
    return CheckResult(
        name=f"row_count_reconciliation:{relationship}",
        passed=passed,
        details=f"source={len(source_df)} rows, target={len(target_df)} rows",
        failing_count=abs(len(source_df) - len(target_df)),
    )


def check_encounter_after_birth(
    encounters: pd.DataFrame, patients: pd.DataFrame
) -> CheckResult:
    merged = encounters.merge(patients[["patient_id", "birth_date"]], on="patient_id", how="inner")
    merged["encounter_date"] = pd.to_datetime(merged["encounter_date"], errors="coerce")
    merged["birth_date"] = pd.to_datetime(merged["birth_date"], errors="coerce")
    comparable = merged.dropna(subset=["encounter_date", "birth_date"])
    violations = comparable[comparable["encounter_date"] < comparable["birth_date"]]
    passed = len(violations) == 0
    return CheckResult(
        name="business_rule:encounter_date_after_birth_date",
        passed=passed,
        details=f"{len(violations)} encounter(s) dated before the patient's birth date"
        if len(violations)
        else "all encounters occur on/after the patient's birth date",
        failing_count=len(violations),
        failing_examples=violations["encounter_id"].tolist() if len(violations) else [],
    )
