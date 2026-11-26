"""Levels per skill, the same rule as the page (src/js/03-leveling.js):
two clean rights in a row go up a level, two wrongs in a row go down. A guess counts as wrong.
A right answer that needed a hint is neither: it resets both runs."""

NEW_SKILL = {"level": 3, "up": 0, "down": 0, "attempts": 0, "correct": 0, "reasons": {}, "recent": []}


def apply_result(before: dict, correct: bool, guessed: bool = False, hints: int = 0, reason: str | None = None) -> dict:
    """Return the skill's state after one answer. `before` is not changed."""
    st = {**NEW_SKILL, **before, "reasons": dict(before.get("reasons") or {}), "recent": list(before.get("recent") or [])}
    wrong = not correct or guessed
    clean = correct and not guessed and hints == 0
    st["attempts"] += 1
    if not wrong:
        st["correct"] += 1
    if clean:
        st["up"] += 1
        st["down"] = 0
        if st["up"] >= 2 and st["level"] < 5:
            st["level"] += 1
            st["up"] = 0
    elif wrong:
        st["down"] += 1
        st["up"] = 0
        if st["down"] >= 2 and st["level"] > 1:
            st["level"] -= 1
            st["down"] = 0
    else:
        st["up"] = 0
        st["down"] = 0
    if wrong and reason:
        st["reasons"][reason] = st["reasons"].get(reason, 0) + 1
    return st


def remember(st: dict, question: str) -> dict:
    """Keep the last three questions for a skill, so the writer avoids repeating itself."""
    return {**st, "recent": (list(st.get("recent") or []) + [question[:160]])[-3:]}
