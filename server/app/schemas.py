"""What the page sends. Responses are plain dictionaries built in service.py."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Level = Field(ge=1, le=5)


class ChildIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    grade: int | None = Field(default=None, ge=1, le=12)
    family_id: int | None = None          # none: the first family


class ChildPatch(BaseModel):
    """Only the fields sent are changed."""
    first_name: str | None = Field(default=None, min_length=1, max_length=40)
    grade: int | None = Field(default=None, ge=1, le=12)
    contest: str | None = None
    focus: str | None = None
    daily_goal: int | None = Field(default=None, ge=1, le=200)
    weekly_goal: int | None = Field(default=None, ge=1, le=1000)
    placement: dict | None = None
    settings: dict | None = None


class ProblemIn(BaseModel):
    skill: str
    level: int = Level
    contest: str | None = None
    grade: int | None = Field(default=None, ge=1, le=12)
    answer_kind: Literal["choice", "typed"] = "choice"
    question: str = Field(min_length=1)
    choices: list[str] | None = None
    answer_index: int | None = None
    accepted_answers: list[str] | None = None
    solution: str | None = None
    hints: list[str] = []
    figure: dict | None = None
    choice_figures: list[dict] | None = None
    written_by: str | None = None
    check_status: Literal["unchecked", "passed", "failed"] = "unchecked"

    @model_validator(mode="after")
    def has_a_key(self):
        if self.answer_kind == "choice":
            if not self.choices or self.answer_index is None or not 0 <= self.answer_index < len(self.choices):
                raise ValueError("a multiple-choice problem needs choices and an answer_index that points at one")
        elif not self.accepted_answers:
            raise ValueError("a typed-answer problem needs at least one accepted answer")
        return self


class AnswerIn(BaseModel):
    """A practice, placement or retry answer. Mock test answers go to the mock test routes.
    Whether it is right is worked out by the server from the problem's key."""
    problem_id: int
    mode: Literal["placement", "practice", "retry"]
    level: int = Level                    # the level it was asked at
    chosen_index: int | None = None
    typed_answer: str | None = None
    hints_used: int = Field(default=0, ge=0, le=10)
    seconds: int | None = Field(default=None, ge=0)
    practice_session_id: int | None = None


class AnswerPatch(BaseModel):
    """What he adds after answering: why he missed it, a note, or how a retry went."""
    trouble_reason: Literal["read", "start", "slip", "guess"] | None = None
    note: str | None = Field(default=None, max_length=500)
    retries: int | None = Field(default=None, ge=0, le=10)
    fixed_on_retry: bool | None = None


class PracticeIn(BaseModel):
    kind: Literal["placement", "daily", "topic"]
    focus: str | None = None
    goal: int | None = Field(default=None, ge=1, le=200)
    planned: list[str] = []


class PracticePatch(BaseModel):
    position: int | None = Field(default=None, ge=0)
    current_problem_id: int | None = None
    planned: list[str] | None = None
    status: Literal["open", "done"] | None = None


class MockItemIn(BaseModel):
    problem_id: int
    points: float = Field(gt=0, le=10)
    label: str | None = None


class MockIn(BaseModel):
    contest: str
    grade: int | None = Field(default=None, ge=1, le=12)
    size: Literal["short", "full"] = "full"
    minutes: int = Field(ge=1, le=240)
    unit: str = "point"
    items: list[MockItemIn] = Field(min_length=1, max_length=60)


class MockAnswerIn(BaseModel):
    chosen_index: int | None = None       # none clears the answer
    typed_answer: str | None = None


class SkillLevelIn(BaseModel):
    level: int = Level
