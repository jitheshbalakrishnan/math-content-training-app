"""Rules the database enforces itself: ranges, answer keys, one open set and one live test per child.

Revision ID: 0002
Revises: 0001
"""
from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UNDO = """
ALTER TABLE mock_tests DROP CONSTRAINT clock_order;
DROP INDEX answers_one_per_mock_problem;
ALTER TABLE mock_test_items DROP CONSTRAINT mock_items_problem_key;
DROP INDEX mock_one_live;
DROP INDEX practice_one_open;
ALTER TABLE custom_topics DROP CONSTRAINT custom_topics_family_skill_key;
ALTER TABLE custom_topics ADD CONSTRAINT custom_topics_skill_id_key UNIQUE (skill_id);
ALTER TABLE children DROP CONSTRAINT children_family_name_key;
ALTER TABLE answers DROP CONSTRAINT mock_link;
ALTER TABLE problems DROP CONSTRAINT typed_has_answers;
ALTER TABLE problems DROP CONSTRAINT choice_has_key;
ALTER TABLE children DROP CONSTRAINT goals_positive;
ALTER TABLE skill_progress DROP CONSTRAINT level_range;
ALTER TABLE answers DROP CONSTRAINT points_range;
ALTER TABLE answers DROP CONSTRAINT level_range;
ALTER TABLE problems DROP CONSTRAINT level_range;
"""


def upgrade() -> None:
    op.execute((Path(__file__).parents[1] / "sql" / "0002_integrity.sql").read_text())


def downgrade() -> None:
    op.execute(UNDO)
