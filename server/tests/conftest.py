"""Shared set-up for the tests that need a real database (TEST_DATABASE_URL).

    createdb math_trainer_test
    TEST_DATABASE_URL=postgresql+psycopg:///math_trainer_test uv run pytest

The scratch database is wiped and migrated once per run, so never point it at math_trainer.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVER), str(SERVER / "scripts")]
URL = os.environ.get("TEST_DATABASE_URL")
if URL:
    os.environ["DATABASE_URL"] = URL      # before app.config is imported anywhere


@pytest.fixture(scope="session")
def engine():
    if not URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    sa = pytest.importorskip("sqlalchemy")
    eng = sa.create_engine(URL)
    if eng.url.database == "math_trainer":
        pytest.fail("TEST_DATABASE_URL points at the real database; use an empty scratch one")
    with eng.begin() as c:
        c.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    subprocess.run(["alembic", "upgrade", "head"], cwd=SERVER, check=True, env=os.environ)
    yield eng
    eng.dispose()


@pytest.fixture()
def clean(engine):
    """An empty database for each test that asks for it."""
    with engine.begin() as c:
        c.exec_driver_sql("TRUNCATE families, problems RESTART IDENTITY CASCADE")
    return engine
