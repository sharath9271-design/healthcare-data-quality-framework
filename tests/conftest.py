from __future__ import annotations

import pathlib
import tempfile

import pytest
from sqlalchemy import create_engine

from src.etl import run_pipeline


@pytest.fixture(scope="session")
def tmp_engine():
    """A throwaway SQLite warehouse, isolated from data/warehouse.db, so
    the test suite never depends on (or pollutes) a local dev run."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = pathlib.Path(tmp_dir) / "test_warehouse.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        yield engine
        engine.dispose()


@pytest.fixture(scope="session")
def pipeline_layers(tmp_engine):
    """Run the real ETL pipeline once per test session against the
    committed synthetic data/raw/*.csv, and hand every layer's DataFrame
    to tests that want to validate against realistic (if fabricated) data."""
    return run_pipeline(tmp_engine)
