"""Daily counts, the week and the streak, all worked out from answer times.

Days are calendar days in the family's time zone (APP_TIMEZONE), so a problem answered at
11 pm counts for that evening, not for the next day in UTC."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def local_day(ts: datetime, tz: ZoneInfo) -> date:
    return ts.astimezone(tz).date()


def streak(days: set[date], today: date) -> int:
    """Days in a row with practice, ending today, or yesterday if he has not practiced yet today."""
    count, d = 0, today
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        count += 1
        d -= timedelta(days=1)
    return count


def week(counts: dict[date, int], today: date) -> list[dict]:
    """Monday to Sunday of this week, each with how many problems were answered."""
    monday = today - timedelta(days=today.weekday())
    out = []
    for i, letter in enumerate("MTWTFSS"):
        d = monday + timedelta(days=i)
        out.append({"day": d.isoformat(), "letter": letter, "n": counts.get(d, 0), "today": d == today, "future": d > today})
    return out
