"""What the page sends. Responses are plain dictionaries built in service.py."""
from typing import ClassVar, Literal

from pydantic import BaseModel, Field, model_validator

Level = Field(ge=1, le=5)


class Patch(BaseModel):
    """A partial update: a field may be left out, but some may not be sent as null."""
    NOT_NULL: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def no_nulls(self):
        if bad := [f for f in self.NOT_NULL if f in self.model_fields_set and getattr(self, f) is None]:
            raise ValueError(f"{', '.join(bad)} cannot be null")
        return self


class ChildIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    grade: int | None = Field(default=None, ge=1, le=12)
    family_id: int | None = None          # none: the first family


class ChildPatch(Patch):
    """Only the fields sent are changed."""
    NOT_NULL = ("first_name", "daily_goal", "weekly_goal", "placement", "settings")
    first_name: str | None = Field(default=None, min_length=1, max_length=40)
    grade: int | None = Field(default=None, ge=1, le=12)
    contest: str | None = None
    focus: str | None = None
    daily_goal: int | None = Field(default=None, ge=1, le=200)
    weekly_goal: int | None = Field(default=None, ge=1, le=1000)
    placement: dict | None = None
    settings: dict | None = None          # the page's own choices: writer tier, answer check, next skill and retry

    @model_validator(mode="after")
    def small(self):
        import json
        for f in ("placement", "settings"):
            v = getattr(self, f)
            if v is not None and len(json.dumps(v)) > 20_000:
                raise ValueError(f"{f} is too large")
        return self


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
        elif not self.accepted_answers or any(not a.strip() for a in self.accepted_answers):
            raise ValueError("a typed-answer problem needs accepted answers, none of them blank")
        return self


class AnswerIn(BaseModel):
    """A practice, placement or retry answer. Mock test answers go to the mock test routes.
    Whether it is right, its level and its points all come from the stored problem."""
    problem_id: int
    mode: Literal["placement", "practice", "retry"]
    chosen_index: int | None = None
    typed_answer: str | None = None
    hints_used: int = Field(default=0, ge=0, le=10)
    seconds: int | None = Field(default=None, ge=0)
    practice_session_id: int | None = None


class AnswerPatch(BaseModel):
    """What he adds after answering: why he missed it, or a note. Null clears either."""
    trouble_reason: Literal["read", "start", "slip", "guess"] | None = None
    note: str | None = Field(default=None, max_length=500)


class RetryIn(BaseModel):
    """Another go at a missed problem. The server marks it."""
    chosen_index: int | None = None
    typed_answer: str | None = None


class PracticeIn(BaseModel):
    kind: Literal["placement", "daily", "topic"]
    focus: str | None = None
    goal: int | None = Field(default=None, ge=1, le=200)
    planned: list[str] = []


class PracticePatch(Patch):
    NOT_NULL = ("position", "planned", "status")
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


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=60_000)


class ClaudeIn(BaseModel):
    """One call for a live agent. The server picks the model from config/agents.toml."""
    agent: Literal["writer", "checker", "tutor"]
    messages: list[Turn] = Field(min_length=1, max_length=40)
    tier: Literal["quick", "default"] | None = None
    child_id: int | None = None


class TopicIn(BaseModel):
    """A topic a parent adds on the Parents page. The page makes the id."""
    skill_id: str = Field(pattern=r"^custom\.[a-z0-9]{1,20}$")
    name: str = Field(min_length=1, max_length=60)
    topic: str = Field(min_length=1, max_length=20)
    contests: list[str] = Field(default=[], max_length=10)
    note: str | None = Field(default=None, max_length=400)
