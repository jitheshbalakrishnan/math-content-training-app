"""Request checks. Needs only pydantic."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pydantic = pytest.importorskip("pydantic")
from app import schemas  # noqa: E402

ValidationError = pydantic.ValidationError
CHOICE = {"skill": "x", "level": 3, "question": "q", "choices": ["a", "b"], "answer_index": 1}


def test_a_choice_key_must_point_at_a_choice():
    schemas.ProblemIn(**CHOICE)
    for bad in ({"answer_index": 2}, {"answer_index": -1}, {"answer_index": None}, {"choices": []}, {"level": 6}):
        with pytest.raises(ValidationError):
            schemas.ProblemIn(**{**CHOICE, **bad})


@pytest.mark.parametrize("accepted", [[], [""], ["  "], ["12", " "]])
def test_typed_answers_cannot_be_blank(accepted):
    with pytest.raises(ValidationError):
        schemas.ProblemIn(skill="x", level=3, question="q", answer_kind="typed", accepted_answers=accepted)


def test_fields_may_be_left_out_but_not_sent_as_null():
    assert schemas.PracticePatch(position=2).model_dump(exclude_unset=True) == {"position": 2}
    assert schemas.ChildPatch(focus=None).model_dump(exclude_unset=True) == {"focus": None}   # clearing a focus is fine
    for model, field in ((schemas.PracticePatch, "position"), (schemas.PracticePatch, "status"),
                         (schemas.ChildPatch, "daily_goal"), (schemas.ChildPatch, "settings")):
        with pytest.raises(ValidationError, match="cannot be null"):
            model(**{field: None})


def test_the_page_cannot_set_level_points_or_a_retry_result():
    a = schemas.AnswerIn(problem_id=1, mode="practice", chosen_index=0, level=5, points=5)
    assert not hasattr(a, "level") and not hasattr(a, "points")
    patch = schemas.AnswerPatch(trouble_reason="guess", fixed_on_retry=True, retries=3)
    assert patch.model_dump(exclude_unset=True) == {"trouble_reason": "guess"}
