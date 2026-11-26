import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.points import points_for  # noqa: E402


def test_right_first_time_earns_the_level():
    assert [points_for(lv, True) for lv in range(1, 6)] == [1, 2, 3, 4, 5]


def test_retry_earns_one_and_a_miss_earns_nothing():
    assert points_for(5, False, fixed_on_retry=True) == 1
    assert points_for(5, False) == 0


def test_a_right_guess_earns_nothing():
    assert points_for(4, True, guessed=True) == 0
