"""Generate a small, fully synthetic raw dataset to exercise the pipeline.

Every name, date, and identifier here is fabricated by Faker with a fixed
seed — nothing in this repository is drawn from a real patient, real
encounter, or real health system. The seed makes the "raw" layer
reproducible so ETL and data-quality results are stable across runs.

Run directly to (re)write the CSVs under data/raw/:

    python -m src.generate_synthetic_data
"""

from __future__ import annotations

import csv
import pathlib
import random
import uuid
from datetime import date, timedelta

from faker import Faker

SEED = 20260824
RAW_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"

CONDITIONS_CATALOG = [
    ("44054006", "Type 2 diabetes mellitus"),
    ("38341003", "Hypertension"),
    ("195967001", "Asthma"),
    ("13645005", "Chronic obstructive pulmonary disease"),
    ("35489007", "Depressive disorder"),
    ("53741008", "Coronary arteriosclerosis"),
]

ENCOUNTER_TYPES = ["outpatient", "inpatient", "emergency", "telehealth", "wellness"]


def _random_birthdate(rng: random.Random) -> date:
    start = date(1935, 1, 1)
    end = date(2015, 12, 31)
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))


def generate_patients(fake: Faker, rng: random.Random, n: int) -> list[dict]:
    patients = []
    for _ in range(n):
        birthdate = _random_birthdate(rng)
        patients.append(
            {
                "patient_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "gender": rng.choice(["female", "male", "other", "unknown"]),
                "birth_date": birthdate.isoformat(),
                "state": fake.state_abbr(),
            }
        )
    # Deliberately introduce a couple of realistic data-quality problems so
    # the check suite below has something real to catch.
    patients[2]["birth_date"] = ""  # missing birth date
    patients[5]["gender"] = "M"      # invalid enum value (should be lowercase full word)
    return patients


def generate_encounters(fake: Faker, rng: random.Random, patients: list[dict], n: int) -> list[dict]:
    encounters = []
    patient_ids = [p["patient_id"] for p in patients]
    for _ in range(n):
        patient_id = rng.choice(patient_ids)
        encounter_date = fake.date_between(start_date="-3y", end_date="today")
        encounters.append(
            {
                "encounter_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "patient_id": patient_id,
                "encounter_type": rng.choice(ENCOUNTER_TYPES),
                "encounter_date": encounter_date.isoformat(),
                "provider": fake.last_name() + ", MD",
            }
        )
    # Inject an orphaned encounter (references a patient that doesn't exist)
    # and a duplicate encounter_id, both classic referential-integrity bugs.
    encounters[7]["patient_id"] = "does-not-exist-0000"
    encounters[10]["encounter_id"] = encounters[9]["encounter_id"]
    return encounters


def generate_conditions(rng: random.Random, encounters: list[dict], n: int) -> list[dict]:
    conditions = []
    encounter_ids = [e["encounter_id"] for e in encounters]
    for _ in range(n):
        code, description = rng.choice(CONDITIONS_CATALOG)
        conditions.append(
            {
                "condition_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "encounter_id": rng.choice(encounter_ids),
                "snomed_code": code,
                "description": description,
            }
        )
    return conditions


def _write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    fake = Faker()
    Faker.seed(SEED)
    rng = random.Random(SEED)

    patients = generate_patients(fake, rng, n=60)
    encounters = generate_encounters(fake, rng, patients, n=150)
    conditions = generate_conditions(rng, encounters, n=90)

    _write_csv(RAW_DIR / "patients.csv", patients)
    _write_csv(RAW_DIR / "encounters.csv", encounters)
    _write_csv(RAW_DIR / "conditions.csv", conditions)

    print(f"Wrote {len(patients)} patients, {len(encounters)} encounters, {len(conditions)} conditions to {RAW_DIR}")


if __name__ == "__main__":
    main()
