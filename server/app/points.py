"""Reward points. They never change his level or which problems he gets."""


def points_for(level: int, correct: bool, guessed: bool = False, fixed_on_retry: bool = False) -> int:
    """Right first time earns the problem's level; right on a retry earns 1; anything else 0.
    A correct guess earns nothing, so the guess button stays honest about guessing."""
    if correct and not guessed:
        return max(1, min(5, level))
    if fixed_on_retry:
        return 1
    return 0
