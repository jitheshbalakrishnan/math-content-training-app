"""The rules the API relies on. Plain Python, no database."""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rules.answers import is_correct, typed_matches  # noqa: E402
from app.rules.leveling import NEW_SKILL, apply_result, remember  # noqa: E402
from app.rules.mock_clock import check  # noqa: E402
from app.rules.progress import local_day, streak, week  # noqa: E402


# ---------- leveling, as in src/js/03-leveling.js ----------

def run(answers, start=None):
    st = dict(start or NEW_SKILL)
    for a in answers:
        st = apply_result(st, **a)
    return st


def test_two_clean_rights_go_up_and_reset_the_run():
    st = run([{"correct": True}, {"correct": True}])
    assert (st["level"], st["up"], st["attempts"], st["correct"]) == (4, 0, 2, 2)


def test_two_wrongs_go_down():
    assert run([{"correct": False}, {"correct": False}])["level"] == 2


def test_a_guess_counts_as_wrong_even_when_right():
    st = run([{"correct": True, "guessed": True}, {"correct": True, "guessed": True}])
    assert (st["level"], st["correct"]) == (2, 0)


def test_a_right_answer_with_a_hint_resets_both_runs():
    st = run([{"correct": True}, {"correct": True, "hints": 1}, {"correct": True}])
    assert (st["level"], st["up"]) == (3, 1)


def test_levels_stop_at_1_and_5():
    assert run([{"correct": True}] * 10)["level"] == 5
    assert run([{"correct": False}] * 10)["level"] == 1


def test_reasons_are_counted_for_wrong_answers_only():
    st = run([{"correct": False, "reason": "slip"}, {"correct": True, "reason": "slip"}])
    assert st["reasons"] == {"slip": 1}


def test_the_before_state_is_not_changed():
    before = {**NEW_SKILL, "reasons": {"read": 1}}
    apply_result(before, correct=False, reason="slip")
    assert before == {**NEW_SKILL, "reasons": {"read": 1}}


def test_only_the_last_three_questions_are_kept():
    st = NEW_SKILL
    for q in "abcd":
        st = remember(st, q * 200)
    assert [len(q) for q in st["recent"]] == [160] * 3 and st["recent"][0][0] == "b"


# ---------- days, week and streak ----------

NY = ZoneInfo("America/New_York")


def test_a_late_evening_answer_counts_for_that_evening():
    assert local_day(datetime(2026, 11, 27, 3, 30, tzinfo=timezone.utc), NY) == date(2026, 11, 26)


def test_streak_ends_today_or_yesterday():
    today = date(2026, 11, 26)
    days = {today - timedelta(days=i) for i in (1, 2, 3)}
    assert streak(days, today) == 3                         # not practiced yet today
    assert streak(days | {today}, today) == 4
    assert streak({today - timedelta(days=2)}, today) == 0  # missed yesterday


def test_week_runs_monday_to_sunday():
    today = date(2026, 11, 26)                              # a Thursday
    w = week({today: 5, date(2026, 11, 23): 2}, today)
    assert [d["letter"] for d in w] == list("MTWTFSS")
    assert (w[0]["n"], w[3]["n"], w[3]["today"], w[4]["future"]) == (2, 5, True, True)


# ---------- the mock test clock ----------

T0 = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)
END = T0 + timedelta(minutes=75)


@pytest.mark.parametrize("last_seen, now, expected", [
    (T0 + timedelta(minutes=10), T0 + timedelta(minutes=11), "in_progress"),
    (T0 + timedelta(minutes=10), T0 + timedelta(minutes=12), "in_progress"),       # exactly two minutes away
    (T0 + timedelta(minutes=10), T0 + timedelta(minutes=12, seconds=1), "abandoned"),
    (END - timedelta(seconds=30), END + timedelta(hours=3), "time_up"),             # clock ran out while briefly away
    (END - timedelta(minutes=5), END + timedelta(minutes=1), "abandoned"),          # gone five minutes before the end
    (END - timedelta(seconds=1), END, "time_up"),
])
def test_grace_period(last_seen, now, expected):
    assert check("in_progress", END, last_seen, now) == expected


def test_only_a_running_test_changes():
    assert check("finished", END, T0, END + timedelta(days=1)) == "finished"
    assert check("preparing", None, None, END) == "preparing"


# ---------- marking ----------

@pytest.mark.parametrize("given, accepted", [
    ("12", ["12"]), (" 12 ", ["12"]), ("12 cm", ["12"]), ("12", ["12 cm"]), ("1/2", ["0.5"]), (".50", ["1/2"]),
    ("1,568", ["1568 chocolate frogs"]), ("2 1/2", ["5/2"]), ("50%", ["1/2"]), ("Monday", ["monday, january 25th", "Monday"]),
    ("-3", ["-3"]), ("x = 18", ["x = 18"]),
])
def test_equal_forms_are_accepted(given, accepted):
    assert typed_matches(given, accepted)


@pytest.mark.parametrize("given, accepted", [
    ("13", ["12"]), ("", ["12"]), ("1/0", ["0"]), ("12", []), ("-1 1/2", ["-1/2"]), ("120", ["12"]), ("1.2", ["12"]),
])
def test_different_answers_are_refused(given, accepted):
    assert not typed_matches(given, accepted)


def test_choice_marking_needs_the_key():
    p = {"answer_kind": "choice", "answer_index": 2}
    assert is_correct(p, 2) and not is_correct(p, 1) and not is_correct(p, None)
    assert is_correct({"answer_kind": "typed", "accepted_answers": ["0.5"]}, typed="1/2")


@pytest.mark.parametrize("given, accepted, ok", [
    ("$360", ["360"], True), ("72 square feet", ["72"], True), ("12 or 13", ["12"], False), ("2.5.1", ["2.5"], False),
])
def test_units_and_extra_text(given, accepted, ok):
    assert typed_matches(given, accepted) is ok


@pytest.mark.parametrize("given, accepted, ok", [
    ("12/3", ["4"], True), ("1 2/3", ["12/3"], False), ("1 2", ["12"], False), ("3 / 4", ["0.75"], True),
    ("10 1/2", ["21/2"], True),
])
def test_fractions_and_mixed_numbers_are_read_correctly(given, accepted, ok):
    assert typed_matches(given, accepted) is ok
