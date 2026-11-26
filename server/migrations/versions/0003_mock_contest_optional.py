"""Old test results exported from the hosted app do not say which contest they were for.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE mock_tests ALTER COLUMN contest DROP NOT NULL")


def downgrade() -> None:
    op.execute("UPDATE mock_tests SET contest = 'unknown' WHERE contest IS NULL")
    op.execute("ALTER TABLE mock_tests ALTER COLUMN contest SET NOT NULL")
