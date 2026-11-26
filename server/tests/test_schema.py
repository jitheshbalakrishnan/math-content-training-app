"""Checks against a real, empty scratch database. Skipped unless TEST_DATABASE_URL is set:

    createdb math_trainer_test
    TEST_DATABASE_URL=postgresql+psycopg:///math_trainer_test uv run pytest

Each run drops and recreates the tables in that database, so never point it at math_trainer.
"""
import os
import shutil
import subprocess
from pathlib import Path

import sys

import pytest

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")
SERVER = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVER), str(SERVER / "scripts")]


@pytest.fixture(scope="module")
def engine():
    sa = pytest.importorskip("sqlalchemy")
    eng = sa.create_engine(URL)
    if eng.url.database == "math_trainer":
        pytest.fail("TEST_DATABASE_URL points at the real database; use an empty scratch one")
    os.environ["DATABASE_URL"] = URL
    with eng.begin() as c:
        c.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    subprocess.run(["alembic", "upgrade", "head"], cwd=SERVER, check=True, env=os.environ)
    yield eng
    eng.dispose()


def test_migration_matches_the_models(engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    with engine.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"app/models.py and the migration disagree: {diff}"


def test_import_runs_and_refuses_a_second_time(engine):
    if not shutil.which("psql"):
        pytest.skip("psql is not installed")
    from import_state import build

    sql = build(SERVER / "tests" / "fixtures" / "sample_export", "Sam", 5, "Family")
    libpq = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    run = lambda: subprocess.run(["psql", libpq, "-q"], input=sql, text=True, capture_output=True, check=True).stdout
    assert "Imported Sam" in run()
    assert "already in the database" in run()
    with engine.connect() as c:
        assert c.exec_driver_sql("SELECT sum(points) FROM answers").scalar() == 9
