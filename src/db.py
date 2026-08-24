"""Database connection factory.

Defaults to a local SQLite file so the whole pipeline runs with zero
external setup. In production this framework is meant to point at a
Snowflake or Databricks SQL warehouse instead — because everything here
goes through SQLAlchemy, that's a connection-string change, not a rewrite:

    export WAREHOUSE_URL="snowflake://user:pass@account/DATABASE/SCHEMA?warehouse=WH"
    export WAREHOUSE_URL="databricks://token:<token>@<host>?http_path=<path>"

No code in etl.py or quality_checks.py changes either way.
"""

from __future__ import annotations

import os
import pathlib

from sqlalchemy import Engine, create_engine

DEFAULT_SQLITE_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "warehouse.db"


def get_engine(url: str | None = None) -> Engine:
    """Return a SQLAlchemy engine for the configured warehouse.

    Resolution order: explicit `url` argument > WAREHOUSE_URL env var >
    local SQLite file under data/warehouse.db.
    """
    resolved = url or os.environ.get("WAREHOUSE_URL") or f"sqlite:///{DEFAULT_SQLITE_PATH}"
    return create_engine(resolved, future=True)
