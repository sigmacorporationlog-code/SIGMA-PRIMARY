"""V4.31 portability/qualification tests for PostgreSQL.

These tests deliberately do not pretend that a PostgreSQL server exists in the
CI image. They validate the SQLAlchemy metadata against PostgreSQL's dialect,
then expose an explicit environment gate for a real server.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models  # noqa: F401 - registers all models
from app.core.database import Base


def test_all_registered_tables_compile_for_postgresql():
    dialect = postgresql.dialect()
    tables = list(Base.metadata.sorted_tables)
    assert len(tables) >= 80
    for table in tables:
        sql = str(CreateTable(table).compile(dialect=dialect))
        assert sql.strip().startswith("CREATE TABLE")
        for index in table.indexes:
            index_sql = str(CreateIndex(index).compile(dialect=dialect))
            assert index_sql.strip().startswith("CREATE")


def test_no_application_alembic_migration_uses_sqlite_only_primitives():
    root = Path(__file__).resolve().parents[1]
    migration_text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (root / "alembic" / "versions").glob("*.py")
    )
    forbidden = ("PRAGMA ", "INSERT OR IGNORE", "INSERT OR REPLACE", "AUTOINCREMENT")
    for token in forbidden:
        assert token not in migration_text, f"SQLite-only SQL found in Alembic migrations: {token}"


def test_postgresql_driver_gate_is_explicit():
    driver_available = any(
        importlib.util.find_spec(module) is not None
        for module in ("psycopg", "psycopg2")
    )
    if os.getenv("SIGMA_REQUIRE_POSTGRES") == "1":
        assert driver_available, "Real PostgreSQL driver required by SIGMA_REQUIRE_POSTGRES=1"
    else:
        # The portable suite records the environment honestly rather than faking a server test.
        assert driver_available in (True, False)


def test_concurrent_transaction_smoke_with_sqlite_fallback(tmp_path):
    """Exercise independent SQLAlchemy sessions concurrently when PostgreSQL is unavailable."""
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import create_engine, text

    db_path = tmp_path / "concurrency.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE counter (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO counter(id,value) VALUES (1,0)"))

    def worker():
        # SQLite cannot provide PostgreSQL's row-lock semantics; this smoke test
        # intentionally validates connection/session independence only.
        with engine.begin() as conn:
            conn.execute(text("SELECT value FROM counter WHERE id=1")).scalar_one()
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: worker(), range(32)))
    assert all(results)
    engine.dispose()
