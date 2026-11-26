"""Initial schema, from migrations/sql/0001_initial.sql.

Revision ID: 0001
Revises:
"""
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = ["reports", "agent_runs", "tutor_messages", "skill_progress", "answers", "mock_test_items", "mock_tests",
          "practice_sessions", "problem_flags", "problem_checks", "problems", "custom_topics", "child_contests",
          "children", "families"]


def upgrade() -> None:
    op.execute((Path(__file__).parents[1] / "sql" / "0001_initial.sql").read_text())


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {t}")
