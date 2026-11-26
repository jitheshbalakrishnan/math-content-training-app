"""Marking. The server decides whether an answer is right; the page never tells it.

Typed answers (MOEMS, IMC) accept equal forms: 1/2, 0.5 and .50 match; "12 cm" matches 12;
capitals, spaces and thousands separators are ignored."""
import re
from fractions import Fraction


def _number(text: str) -> Fraction | None:
    t = re.sub(r"\s*/\s*", "/", text.replace(",", "").strip())     # "3 / 4" -> "3/4"; other spaces stay
    m = re.fullmatch(r"(-?\d+)\s+(\d+)/(\d+)", t)               # a mixed number such as 2 1/2 (space required)
    if m and int(m.group(3)):
        whole, num, den = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return whole + (Fraction(num, den) if whole >= 0 else -Fraction(num, den))
    m = re.fullmatch(r"(-?\d*\.?\d+)(?:/(-?\d*\.?\d+))?%?", t)
    if not m:
        return None
    try:
        value = Fraction(m.group(1)) / (Fraction(m.group(2)) if m.group(2) else 1)
    except ZeroDivisionError:
        return None
    return value / 100 if t.endswith("%") else value


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().replace(",", ""))


def _leading_number(text: str) -> Fraction | None:
    """The number in an answer followed by words only: '12 cm' -> 12, '1568 chocolate frogs' -> 1568."""
    m = re.match(r"\s*\$?(-?\d[\d,]*(?:\.\d+)?(?:\s+\d+/\d+|/\d+)?)\s*[a-zA-Z²³°$%. ]*$", text)
    return _number(m.group(1)) if m else None


def typed_matches(given: str, accepted: list[str]) -> bool:
    if not given or not given.strip():
        return False
    g_num = _number(given) if _number(given) is not None else _leading_number(given)
    for a in accepted:
        if _plain(given) == _plain(a):
            return True
        a_num = _number(a) if _number(a) is not None else _leading_number(a)
        if g_num is not None and a_num is not None and g_num == a_num:
            return True
    return False


def is_correct(problem: dict, chosen_index: int | None = None, typed: str | None = None) -> bool:
    if problem["answer_kind"] == "typed":
        return typed_matches(typed or "", problem.get("accepted_answers") or [])
    return chosen_index is not None and chosen_index == problem.get("answer_index")
