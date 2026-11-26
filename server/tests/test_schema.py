"""The migrations against the models, and the import against a real database.
Skipped unless TEST_DATABASE_URL is set; see conftest.py."""
import shutil
import subprocess

import pytest

from conftest import SERVER


def test_migration_matches_the_models(engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    with engine.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"app/models.py and the migrations disagree: {diff}"


def test_import_runs_and_refuses_a_second_time(clean):
    if not shutil.which("psql"):
        pytest.skip("psql is not installed")
    from import_state import build

    sql = build(SERVER / "tests" / "fixtures" / "sample_export", "Sam", 5, "Family")
    libpq = clean.url.set(drivername="postgresql").render_as_string(hide_password=False)
    run = lambda: subprocess.run(["psql", libpq, "-q"], input=sql, text=True, capture_output=True, check=True).stdout
    assert "Imported Sam" in run()
    assert "already in the database" in run()
    with clean.connect() as c:
        assert c.exec_driver_sql("SELECT sum(points) FROM answers").scalar() == 9
