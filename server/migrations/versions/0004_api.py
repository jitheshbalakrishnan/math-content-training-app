"""For the API: the skill state before each answer, and one child per answer, set and test.

Revision ID: 0004
Revises: 0003
"""
from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute((Path(__file__).parents[1] / "sql" / "0004_api.sql").read_text())


def downgrade() -> None:
    op.execute("""
        ALTER TABLE answers DROP CONSTRAINT answers_mock_same_child;
        ALTER TABLE answers DROP CONSTRAINT answers_session_same_child;
        ALTER TABLE mock_tests DROP CONSTRAINT mock_tests_id_child_key;
        ALTER TABLE practice_sessions DROP CONSTRAINT practice_sessions_id_child_key;
        ALTER TABLE answers DROP COLUMN skill_before;
    """)
