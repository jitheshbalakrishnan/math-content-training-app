"""The database schema.

Every row that belongs to a child carries child_id, so adding a sibling is a new row in
children. Problems belong to no child: one child never sees the same problem twice, but a
sibling can get a problem another child already answered.

Status-like columns are plain text with a CHECK constraint, so adding a value is a small
migration. Skill ids refer to skill_map.json, which stays a file in the repo.
"""
from datetime import date, datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index,
                        ForeignKeyConstraint, Integer, Numeric, SmallInteger, Text, UniqueConstraint, func, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(), primary_key=True)


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def one_of(column: str, *values: str) -> CheckConstraint:
    return CheckConstraint(f"{column} IN ({', '.join(repr(v) for v in values)})", name=f"{column}_valid")


def level_range() -> CheckConstraint:
    return CheckConstraint("level BETWEEN 1 AND 5", name="level_range")


# ---------- who ----------

class Family(Base):
    __tablename__ = "families"
    id: Mapped[int] = pk()
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created()


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (UniqueConstraint("family_id", "first_name", name="children_family_name_key"),
                      CheckConstraint("daily_goal > 0 AND weekly_goal > 0", name="goals_positive"))
    id: Mapped[int] = pk()
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(Text)
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    contest: Mapped[str | None] = mapped_column(Text)              # a contest key, or 'both' for all of them
    focus: Mapped[str | None] = mapped_column(Text)                # a topic or skill id he chose to practice
    daily_goal: Mapped[int] = mapped_column(SmallInteger, server_default="10")
    weekly_goal: Mapped[int] = mapped_column(SmallInteger, server_default="50")
    placement: Mapped[dict] = mapped_column(JSONB, server_default="{}")   # {queue: [skill ids], i, done}
    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}")    # {tier, verify}
    created_at: Mapped[datetime] = created()


class ChildContest(Base):
    """Last year's score per contest: the baseline he is trying to beat."""
    __tablename__ = "child_contests"
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), primary_key=True)
    contest: Mapped[str] = mapped_column(Text, primary_key=True)
    last_year_score: Mapped[float | None] = mapped_column(Numeric(6, 1))
    last_year_max: Mapped[float | None] = mapped_column(Numeric(6, 1))
    note: Mapped[str | None] = mapped_column(Text)


class CustomTopic(Base):
    """Topics a parent added on the Parents page."""
    __tablename__ = "custom_topics"
    __table_args__ = (UniqueConstraint("family_id", "skill_id", name="custom_topics_family_skill_key"),)
    id: Mapped[int] = pk()
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(Text)                    # custom.<id>, unique within a family
    name: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    contests: Mapped[list] = mapped_column(JSONB, server_default="[]")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created()


# ---------- problems and answers ----------

class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        one_of("source", "generated", "past_paper"),
        one_of("answer_kind", "choice", "typed"),
        one_of("check_status", "unchecked", "passed", "failed"),
        one_of("status", "draft", "verified", "rejected", "retired"),
        level_range(),
        CheckConstraint("answer_kind <> 'choice' OR COALESCE(jsonb_typeof(choices) = 'array' AND answer_index >= 0 "
                        "AND answer_index < jsonb_array_length(choices), false)", name="choice_has_key"),
        CheckConstraint("answer_kind <> 'typed' OR COALESCE(jsonb_typeof(accepted_answers) = 'array' "
                        "AND jsonb_array_length(accepted_answers) > 0, false)", name="typed_has_answers"),
        Index("problems_pick", "skill", "level", "status"),
    )
    id: Mapped[int] = pk()
    skill: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(SmallInteger)
    contest: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[int | None] = mapped_column(SmallInteger)        # for grade-specific papers such as IMC
    source: Mapped[str] = mapped_column(Text, server_default="generated")
    source_year: Mapped[int | None] = mapped_column(SmallInteger)  # past papers only
    source_number: Mapped[int | None] = mapped_column(SmallInteger)
    answer_kind: Mapped[str] = mapped_column(Text, server_default="choice")
    question: Mapped[str] = mapped_column(Text)
    choices: Mapped[list | None] = mapped_column(JSONB)             # multiple choice only
    answer_index: Mapped[int | None] = mapped_column(SmallInteger)
    accepted_answers: Mapped[list | None] = mapped_column(JSONB)    # typed answers: every accepted form
    solution: Mapped[str | None] = mapped_column(Text)
    hints: Mapped[list] = mapped_column(JSONB, server_default="[]")
    figure: Mapped[dict | None] = mapped_column(JSONB)              # figure data, drawn by code
    choice_figures: Mapped[list | None] = mapped_column(JSONB)
    figure_image: Mapped[str | None] = mapped_column(Text)          # a cropped picture from a past paper
    points: Mapped[int | None] = mapped_column(SmallInteger)        # its value on the real paper, if known
    written_by: Mapped[str | None] = mapped_column(Text)            # the model, or 'import'
    check_status: Mapped[str] = mapped_column(Text, server_default="unchecked")
    status: Mapped[str] = mapped_column(Text, server_default="draft")
    created_at: Mapped[datetime] = created()


class ProblemCheck(Base):
    __tablename__ = "problem_checks"
    id: Mapped[int] = pk()
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    check: Mapped[str] = mapped_column(Text)                        # e.g. blind_solve, arithmetic
    model: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(Text)                      # agree, disagree, error
    answer_given: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = created()


class ProblemFlag(Base):
    """A problem someone thinks is wrong: the child's button, a pattern, or the reviewer."""
    __tablename__ = "problem_flags"
    __table_args__ = (one_of("raised_by", "child", "pattern", "reviewer", "parent"),
                      CheckConstraint("resolution IS NULL OR resolution IN ('bad_problem', 'fine')", name="resolution_valid"))
    id: Mapped[int] = pk()
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    raised_by: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()


class PracticeSession(Base):
    """An untimed set. current_problem_id is what lets him pick up where he left off."""
    __tablename__ = "practice_sessions"
    __table_args__ = (one_of("kind", "placement", "daily", "topic"), one_of("status", "open", "done"),
                      Index("practice_open", "child_id", "status"),
                      UniqueConstraint("id", "child_id", name="practice_sessions_id_child_key"),
                      Index("practice_one_open", "child_id", unique=True, postgresql_where=text("status = 'open'")))
    id: Mapped[int] = pk()
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    focus: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[int | None] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    planned: Mapped[list] = mapped_column(JSONB, server_default="[]")
    current_problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(Text, server_default="open")
    started_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MockTest(Base):
    """No pause: leaving for more than two minutes (last_seen_at) abandons the test.
    ends_at never moves, so the clock keeps running through the grace period."""
    __tablename__ = "mock_tests"
    __table_args__ = (one_of("status", "preparing", "in_progress", "finished", "abandoned"),
                      CheckConstraint("ends_at IS NULL OR started_at IS NULL OR ends_at > started_at", name="clock_order"),
                      UniqueConstraint("id", "child_id", name="mock_tests_id_child_key"),
                      Index("mock_one_live", "child_id", unique=True,
                            postgresql_where=text("status IN ('preparing', 'in_progress')")))
    id: Mapped[int] = pk()
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    contest: Mapped[str | None] = mapped_column(Text)              # NULL for old results that did not record it
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    size: Mapped[str] = mapped_column(Text, server_default="full")
    status: Mapped[str] = mapped_column(Text, server_default="preparing")
    minutes: Mapped[int | None] = mapped_column(SmallInteger)
    unit: Mapped[str] = mapped_column(Text, server_default="point")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    questions: Mapped[int | None] = mapped_column(SmallInteger)
    correct: Mapped[int | None] = mapped_column(SmallInteger)
    score: Mapped[float | None] = mapped_column(Numeric(6, 1))
    max_score: Mapped[float | None] = mapped_column(Numeric(6, 1))
    seconds_used: Mapped[int | None] = mapped_column(Integer)


class MockTestItem(Base):
    """The paper itself. His answers go in answers."""
    __tablename__ = "mock_test_items"
    __table_args__ = (UniqueConstraint("mock_test_id", "problem_id", name="mock_items_problem_key"),)
    mock_test_id: Mapped[int] = mapped_column(ForeignKey("mock_tests.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    points: Mapped[float] = mapped_column(Numeric(4, 1))
    label: Mapped[str | None] = mapped_column(Text)


class Answer(Base):
    """One answered problem. Streaks and daily counts are computed from here, so there is
    no separate tally to drift. A mock test keeps only the final answer per question."""
    __tablename__ = "answers"
    __table_args__ = (one_of("mode", "placement", "practice", "retry", "mock"),
                      level_range(),
                      CheckConstraint("points BETWEEN 0 AND 5", name="points_range"),
                      CheckConstraint("mock_test_id IS NULL OR mode = 'mock'", name="mock_link"),
                      ForeignKeyConstraint(["practice_session_id", "child_id"], ["practice_sessions.id", "practice_sessions.child_id"],
                                           name="answers_session_same_child"),
                      ForeignKeyConstraint(["mock_test_id", "child_id"], ["mock_tests.id", "mock_tests.child_id"],
                                           name="answers_mock_same_child", ondelete="CASCADE"),
                      Index("answers_by_child", "child_id", "answered_at"),
                      Index("answers_seen", "child_id", "problem_id"),
                      Index("answers_one_per_mock_problem", "mock_test_id", "problem_id", unique=True,
                            postgresql_where=text("mock_test_id IS NOT NULL")))
    id: Mapped[int] = pk()
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    mode: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(SmallInteger)               # the level it was asked at
    practice_session_id: Mapped[int | None] = mapped_column(ForeignKey("practice_sessions.id", ondelete="SET NULL"))
    mock_test_id: Mapped[int | None] = mapped_column(ForeignKey("mock_tests.id", ondelete="CASCADE"))
    chosen_index: Mapped[int | None] = mapped_column(SmallInteger)  # null when left blank
    typed_answer: Mapped[str | None] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    trouble_reason: Mapped[str | None] = mapped_column(Text)        # read, start, slip, guess
    note: Mapped[str | None] = mapped_column(Text)
    hints_used: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    seconds: Mapped[int | None] = mapped_column(Integer)
    retries: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    fixed_on_retry: Mapped[bool] = mapped_column(Boolean, server_default="false")
    points: Mapped[int] = mapped_column(SmallInteger, server_default="0")   # reward points earned
    skill_before: Mapped[dict | None] = mapped_column(JSONB)       # the skill just before this answer, to redo a correction
    answered_at: Mapped[datetime] = created()


class SkillProgress(Base):
    __tablename__ = "skill_progress"
    __table_args__ = (level_range(),)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), primary_key=True)
    skill: Mapped[str] = mapped_column(Text, primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    up: Mapped[int] = mapped_column(SmallInteger, server_default="0")      # clean rights in a row
    down: Mapped[int] = mapped_column(SmallInteger, server_default="0")    # wrongs in a row
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    correct: Mapped[int] = mapped_column(Integer, server_default="0")
    reasons: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    recent: Mapped[list] = mapped_column(JSONB, server_default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------- agents ----------

class TutorMessage(Base):
    __tablename__ = "tutor_messages"
    __table_args__ = (one_of("role", "child", "tutor"),)
    id: Mapped[int] = pk()
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = created()


class AgentRun(Base):
    """One model call: cost and failures per agent and per child."""
    __tablename__ = "agent_runs"
    id: Mapped[int] = pk()
    agent: Mapped[str] = mapped_column(Text, index=True)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    seconds: Mapped[float | None] = mapped_column(Numeric(8, 2))
    ok: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = created()


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (one_of("kind", "weekly_summary", "review_findings"),)
    id: Mapped[int] = pk()
    child_id: Mapped[int | None] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    week_start: Mapped[date] = mapped_column(Date)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created()
