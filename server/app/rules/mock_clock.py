"""The mock test clock. A test cannot be paused: the page reports in every few seconds, and if
it has been gone for more than two minutes the test is abandoned and not scored. The clock
keeps running through those two minutes, because the end time never moves."""
from datetime import datetime, timedelta

GRACE = timedelta(minutes=2)


def check(status: str, ends_at: datetime | None, last_seen_at: datetime | None, now: datetime) -> str:
    """What a test in progress should become now: 'in_progress', 'time_up' (score it) or 'abandoned'."""
    if status != "in_progress" or ends_at is None:
        return status
    # Only time before the end counts as being away: returning after the clock ran out
    # within two minutes of last being seen still gets the test scored.
    away = min(now, ends_at) - last_seen_at if last_seen_at else timedelta(0)
    if away > GRACE:
        return "abandoned"
    if now >= ends_at:
        return "time_up"
    return "in_progress"
