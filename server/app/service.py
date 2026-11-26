"""What the API does, one function per action. Each takes a database session and the current
time, so tests can set the clock. Raises Problem for anything the caller should see."""
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import TIMEZONE
from .models import (Answer, Child, Family, MockTest, MockTestItem, PracticeSession, Problem as ProblemRow,
                     SkillProgress)
from .points import points_for
from .rules.answers import is_correct
from .rules.leveling import NEW_SKILL, apply_result, remember
from .rules.mock_clock import check
from .rules.progress import local_day, streak, week
from . import schemas

TZ = ZoneInfo(TIMEZONE)
SKILL_FIELDS = ("level", "up", "down", "attempts", "correct", "reasons", "recent")


class Problem(Exception):
    """An error for the page: an HTTP status and a short message. keep=True saves what was already
    changed (a test found abandoned stays abandoned); otherwise everything is rolled back."""
    def __init__(self, status: int, message: str, keep: bool = False):
        super().__init__(message)
        self.status, self.message, self.keep = status, message, keep


def _get(db: Session, model, id_: int, what: str):
    row = db.get(model, id_)
    if row is None:
        raise Problem(404, f"No {what} {id_}.")
    return row


def _child(db: Session, child_id: int) -> Child:
    return _get(db, Child, child_id, "child")


def _problem_dict(p: ProblemRow) -> dict:
    return {"id": p.id, "skill": p.skill, "level": p.level, "contest": p.contest, "grade": p.grade,
            "answer_kind": p.answer_kind, "question": p.question, "choices": p.choices, "answer_index": p.answer_index,
            "accepted_answers": p.accepted_answers, "solution": p.solution, "hints": p.hints, "figure": p.figure,
            "choice_figures": p.choice_figures, "figure_image": p.figure_image, "check_status": p.check_status,
            "status": p.status, "source": p.source}


def _without_key(p: dict) -> dict:
    """A problem as shown during a mock test: no answer, no solution."""
    return {k: v for k, v in p.items() if k not in ("answer_index", "accepted_answers", "solution", "hints")}


def _skill_dict(sp: SkillProgress | None) -> dict:
    return {k: getattr(sp, k) for k in SKILL_FIELDS} if sp else dict(NEW_SKILL)


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


# ---------- children ----------

def list_children(db: Session) -> list[dict]:
    rows = db.scalars(select(Child).order_by(Child.id)).all()
    return [{"id": c.id, "first_name": c.first_name, "grade": c.grade, "family_id": c.family_id} for c in rows]


def create_child(db: Session, body: schemas.ChildIn) -> dict:
    family_id = body.family_id
    if family_id is None:
        family = db.scalars(select(Family).order_by(Family.id)).first()
        if family is None:
            family = Family(name="Family")
            db.add(family)
            db.flush()
        family_id = family.id
    else:
        _get(db, Family, family_id, "family")
    child = Child(family_id=family_id, first_name=body.first_name.strip(), grade=body.grade)
    db.add(child)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Problem(409, f"There is already a child called {body.first_name} in this family.")
    return {"id": child.id, "first_name": child.first_name, "grade": child.grade, "family_id": family_id}


def update_child(db: Session, child_id: int, body: schemas.ChildPatch) -> dict:
    child = _child(db, child_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k in ("daily_goal", "weekly_goal", "first_name") and v is None:
            raise Problem(422, f"{k} cannot be empty.")
        setattr(child, k, v.strip() if k == "first_name" else v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Problem(409, "Another child in this family already has that name.")
    return child_summary(db, child_id, datetime.now(TZ))


def child_summary(db: Session, child_id: int, now: datetime) -> dict:
    """Everything the home and progress screens need, in one call."""
    child = _child(db, child_id)
    skills = {sp.skill: _skill_dict(sp) for sp in db.scalars(select(SkillProgress).where(SkillProgress.child_id == child_id))}
    since = now - timedelta(days=400)        # enough for any streak worth showing
    rows = db.execute(select(Answer.answered_at, Answer.correct)
                      .where(Answer.child_id == child_id, Answer.answered_at >= since)).all()
    counts: dict = {}
    right_today = 0
    today = local_day(now, TZ)
    for at, correct in rows:
        d = local_day(at, TZ)
        counts[d] = counts.get(d, 0) + 1
        right_today += int(d == today and correct)
    points = db.scalar(select(func.coalesce(func.sum(Answer.points), 0)).where(Answer.child_id == child_id))
    best = db.scalars(select(MockTest).where(MockTest.child_id == child_id, MockTest.status == "finished",
                                             MockTest.max_score > 0)
                      .order_by((MockTest.score / MockTest.max_score).desc(), MockTest.finished_at.desc())).first()
    return {
        "id": child.id, "first_name": child.first_name, "grade": child.grade, "contest": child.contest,
        "focus": child.focus, "placement": child.placement, "settings": child.settings,
        "goals": {"day": child.daily_goal, "week": child.weekly_goal},
        "skills": skills,
        "today": {"n": counts.get(today, 0), "ok": right_today},
        "week": week(counts, today),
        "streak": streak(set(counts), today),
        "points": int(points),
        "best_mock": _mock_summary(best) if best else None,
        "open_practice": open_practice(db, child_id),
        "live_mock": live_mock(db, child_id, now),
    }


# ---------- problems ----------

def create_problem(db: Session, body: schemas.ProblemIn) -> dict:
    p = ProblemRow(**body.model_dump())
    db.add(p)
    db.flush()
    return _problem_dict(p)


def _in_running_test(db: Session, problem_id: int, child_id: int | None = None) -> bool:
    q = (select(MockTest.id).join(MockTestItem, MockTestItem.mock_test_id == MockTest.id)
         .where(MockTestItem.problem_id == problem_id, MockTest.status.in_(("preparing", "in_progress"))))
    if child_id is not None:
        q = q.where(MockTest.child_id == child_id)
    return db.scalars(q.limit(1)).first() is not None


def get_problem(db: Session, problem_id: int) -> dict:
    """A problem on a test that is being prepared or taken is shown without its key."""
    pd = _problem_dict(_get(db, ProblemRow, problem_id, "problem"))
    return _without_key(pd) if _in_running_test(db, problem_id) else pd


def seen_problem_ids(db: Session, child_id: int, skill: str | None = None) -> list[int]:
    """Problems this child has already answered, so he is never given one twice."""
    q = select(Answer.problem_id).where(Answer.child_id == child_id).distinct()
    if skill:
        q = q.join(ProblemRow, ProblemRow.id == Answer.problem_id).where(ProblemRow.skill == skill)
    return list(db.scalars(q))


# ---------- practice answers ----------

def _skill_row(db: Session, child_id: int, skill: str) -> SkillProgress:
    sp = db.get(SkillProgress, (child_id, skill), with_for_update=True)
    if sp is None:
        sp = SkillProgress(child_id=child_id, skill=skill,
                           **{k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in NEW_SKILL.items()})
        db.add(sp)
    return sp


def _set_skill(sp: SkillProgress, st: dict) -> None:
    for k in SKILL_FIELDS:
        setattr(sp, k, st[k])


def record_answer(db: Session, child_id: int, body: schemas.AnswerIn, now: datetime) -> dict:
    _child(db, child_id)
    problem = _get(db, ProblemRow, body.problem_id, "problem")
    if problem.status in ("rejected", "retired"):
        raise Problem(409, "That problem has been taken out of use.")
    if _in_running_test(db, problem.id, child_id):
        raise Problem(409, "That problem is on your mock test. Answer it there.")
    if body.practice_session_id is not None:
        s = _get(db, PracticeSession, body.practice_session_id, "practice set")
        if s.child_id != child_id:
            raise Problem(403, "That practice set belongs to another child.")
    pd = _problem_dict(problem)
    correct = is_correct(pd, body.chosen_index, body.typed_answer)
    sp = _skill_row(db, child_id, problem.skill)
    before = _skill_dict(sp)
    after = remember(apply_result(before, correct=correct, hints=body.hints_used), problem.question)
    _set_skill(sp, after)
    a = Answer(child_id=child_id, problem_id=problem.id, mode=body.mode, level=body.level,
               practice_session_id=body.practice_session_id, chosen_index=body.chosen_index,
               typed_answer=body.typed_answer, correct=correct, hints_used=body.hints_used, seconds=body.seconds,
               points=points_for(body.level, correct), skill_before=before, answered_at=now)
    db.add(a)
    db.flush()
    return {"answer_id": a.id, "correct": correct, "points": a.points, "skill": after, "problem": pd}


def update_answer(db: Session, child_id: int, answer_id: int, body: schemas.AnswerPatch) -> dict:
    """A reason, note or retry result added after answering. A changed reason redoes the level change,
    but only while this is still the latest answer for the skill; later answers have built on it."""
    a = _get(db, Answer, answer_id, "answer")
    if a.child_id != child_id:
        raise Problem(403, "That answer belongs to another child.")
    if a.mode == "mock":
        raise Problem(409, "Mock test answers cannot be changed after the test.")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(a, k, v)
    problem = db.get(ProblemRow, a.problem_id)
    guessed = a.trouble_reason == "guess"
    a.points = points_for(a.level, a.correct, guessed, bool(a.fixed_on_retry))
    releveled = False
    if "trouble_reason" in changes and a.skill_before is not None:
        later = db.scalar(select(func.count()).select_from(Answer)
                          .join(ProblemRow, ProblemRow.id == Answer.problem_id)
                          .where(Answer.child_id == child_id, ProblemRow.skill == problem.skill,
                                 Answer.mode != "mock", Answer.id > a.id))
        if not later:
            sp = _skill_row(db, child_id, problem.skill)
            st = apply_result(a.skill_before, correct=a.correct, guessed=guessed, hints=a.hints_used,
                              reason=a.trouble_reason)
            _set_skill(sp, remember(st, problem.question))
            releveled = True
    db.flush()
    return {"answer_id": a.id, "points": a.points, "releveled": releveled,
            "skill": _skill_dict(db.get(SkillProgress, (child_id, problem.skill)))}


def set_skill_level(db: Session, child_id: int, skill: str, level: int) -> dict:
    """Placement sets a starting level directly: after a miss, the topic's untried skills start at 2."""
    _child(db, child_id)
    sp = _skill_row(db, child_id, skill)
    sp.level, sp.up, sp.down = level, 0, 0
    db.flush()
    return _skill_dict(sp)


# ---------- practice sets ----------

def _practice_dict(s: PracticeSession) -> dict:
    return {"id": s.id, "kind": s.kind, "focus": s.focus, "goal": s.goal, "position": s.position,
            "planned": s.planned, "current_problem_id": s.current_problem_id, "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None}


def open_practice(db: Session, child_id: int) -> dict | None:
    s = db.scalars(select(PracticeSession).where(PracticeSession.child_id == child_id,
                                                 PracticeSession.status == "open")).first()
    return _practice_dict(s) if s else None


def start_practice(db: Session, child_id: int, body: schemas.PracticeIn) -> dict:
    """An open set is resumed rather than replaced, so he picks up where he left off on any device."""
    _child(db, child_id)
    existing = open_practice(db, child_id)
    if existing:
        return {**existing, "resumed": True}
    s = PracticeSession(child_id=child_id, kind=body.kind, focus=body.focus, goal=body.goal, planned=body.planned)
    db.add(s)
    try:
        db.flush()
    except IntegrityError:                   # another device opened one at the same moment
        db.rollback()
        return {**open_practice(db, child_id), "resumed": True}
    return {**_practice_dict(s), "resumed": False}


def update_practice(db: Session, child_id: int, session_id: int, body: schemas.PracticePatch) -> dict:
    s = _get(db, PracticeSession, session_id, "practice set")
    if s.child_id != child_id:
        raise Problem(403, "That practice set belongs to another child.")
    if s.status == "done":
        raise Problem(409, "That practice set is finished.")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("current_problem_id") is not None:
        _get(db, ProblemRow, changes["current_problem_id"], "problem")
    for k, v in changes.items():
        setattr(s, k, v)
    db.flush()
    return _practice_dict(s)


# ---------- mock tests ----------

def _mock_summary(m: MockTest) -> dict:
    return {"id": m.id, "contest": m.contest, "grade": m.grade, "size": m.size, "status": m.status,
            "minutes": m.minutes, "unit": m.unit, "questions": m.questions, "correct": m.correct,
            "score": _num(m.score), "max_score": _num(m.max_score), "seconds_used": m.seconds_used,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "ends_at": m.ends_at.isoformat() if m.ends_at else None,
            "finished_at": m.finished_at.isoformat() if m.finished_at else None}


def _own_mock(db: Session, child_id: int, mock_id: int, lock: bool = False) -> MockTest:
    m = db.get(MockTest, mock_id, with_for_update=lock)
    if m is None:
        raise Problem(404, f"No mock test {mock_id}.")
    if m.child_id != child_id:
        raise Problem(403, "That mock test belongs to another child.")
    return m


def _settle_clock(db: Session, m: MockTest, now: datetime) -> str:
    """Apply the clock: abandon a test left too long, score one whose time ran out."""
    state = check(m.status, m.ends_at, m.last_seen_at, now)
    if state == "abandoned":
        m.status = "abandoned"
        m.finished_at = now
    elif state == "time_up":
        _score(db, m, now)
    return m.status


def live_mock(db: Session, child_id: int, now: datetime) -> dict | None:
    m = db.scalars(select(MockTest).where(MockTest.child_id == child_id,
                                          MockTest.status.in_(("preparing", "in_progress")))).first()
    if m is None:
        return None
    if _settle_clock(db, m, now) not in ("preparing", "in_progress"):
        db.flush()
        return None
    return _mock_summary(m)


def create_mock(db: Session, child_id: int, body: schemas.MockIn, now: datetime) -> dict:
    """A new test, with its questions already written. An old one still preparing is replaced:
    a test is never paused, so there is nothing to go back to."""
    _child(db, child_id)
    old = live_mock(db, child_id, now)
    if old and old["status"] == "in_progress":
        raise Problem(409, "A mock test is already running. Finish it first.")
    if old:
        prev = db.get(MockTest, old["id"])
        prev.status, prev.finished_at = "abandoned", now
        db.flush()
    ids = [it.problem_id for it in body.items]
    if len(set(ids)) != len(ids):
        raise Problem(422, "A test cannot ask the same problem twice.")
    found = set(db.scalars(select(ProblemRow.id).where(ProblemRow.id.in_(ids))))
    if missing := [i for i in ids if i not in found]:
        raise Problem(404, f"No problems {missing}.")
    m = MockTest(child_id=child_id, contest=body.contest, grade=body.grade, size=body.size, status="preparing",
                 minutes=body.minutes, unit=body.unit, questions=len(ids))
    db.add(m)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Problem(409, "Another mock test was started at the same moment.")
    for pos, it in enumerate(body.items):
        db.add(MockTestItem(mock_test_id=m.id, position=pos, problem_id=it.problem_id, points=it.points, label=it.label))
    db.flush()
    return get_mock(db, child_id, m.id, now)


def get_mock(db: Session, child_id: int, mock_id: int, now: datetime) -> dict:
    """The test as the page shows it: no answer keys until it is over."""
    m = _own_mock(db, child_id, mock_id)
    _settle_clock(db, m, now)
    db.flush()
    over = m.status in ("finished", "abandoned")
    items = db.execute(select(MockTestItem, ProblemRow).join(ProblemRow, ProblemRow.id == MockTestItem.problem_id)
                       .where(MockTestItem.mock_test_id == m.id).order_by(MockTestItem.position)).all()
    given = {a.problem_id: a for a in db.scalars(select(Answer).where(Answer.mock_test_id == m.id))}
    out = []
    for item, p in items:
        pd = _problem_dict(p)
        a = given.get(p.id)
        row = {"position": item.position, "points": _num(item.points), "label": item.label,
               "problem": pd if over else _without_key(pd),
               "chosen_index": a.chosen_index if a else None, "typed_answer": a.typed_answer if a else None}
        if over:
            row["correct"] = bool(a and a.correct)
        out.append(row)
    return {**_mock_summary(m), "items": out,
            "seconds_left": max(0, int((m.ends_at - now).total_seconds())) if m.status == "in_progress" else None}


def start_mock(db: Session, child_id: int, mock_id: int, now: datetime) -> dict:
    m = _own_mock(db, child_id, mock_id, lock=True)
    if m.status != "preparing":
        raise Problem(409, f"This test is {m.status.replace('_', ' ')} and cannot be started.")
    m.status, m.started_at, m.last_seen_at = "in_progress", now, now
    m.ends_at = now + timedelta(minutes=m.minutes)
    db.flush()
    return get_mock(db, child_id, mock_id, now)


def _running(db: Session, child_id: int, mock_id: int, now: datetime) -> MockTest:
    m = _own_mock(db, child_id, mock_id, lock=True)
    if _settle_clock(db, m, now) != "in_progress":
        db.flush()
        raise Problem(409, "This test has ended." if m.status == "finished"
                      else "This test was left for more than two minutes, so it has ended. Start a new one.", keep=True)
    return m


def heartbeat(db: Session, child_id: int, mock_id: int, now: datetime) -> dict:
    """The page reports in every few seconds while the test is open."""
    m = _own_mock(db, child_id, mock_id, lock=True)
    if _settle_clock(db, m, now) == "in_progress":
        m.last_seen_at = now
    db.flush()
    return {"status": m.status,
            "seconds_left": max(0, int((m.ends_at - now).total_seconds())) if m.status == "in_progress" else None}


def answer_mock(db: Session, child_id: int, mock_id: int, position: int, body: schemas.MockAnswerIn, now: datetime) -> dict:
    """Keeps only his latest answer to each question."""
    m = _running(db, child_id, mock_id, now)
    m.last_seen_at = now
    item = db.get(MockTestItem, (m.id, position))
    if item is None:
        raise Problem(404, f"This test has no question {position + 1}.")
    p = db.get(ProblemRow, item.problem_id)
    a = db.scalars(select(Answer).where(Answer.mock_test_id == m.id, Answer.problem_id == p.id)).first()
    blank = body.chosen_index is None and not (body.typed_answer or "").strip()
    if blank:
        if a:
            db.delete(a)
        db.flush()
        return {"position": position, "answered": False}
    correct = is_correct(_problem_dict(p), body.chosen_index, body.typed_answer)
    if a is None:
        a = Answer(child_id=child_id, problem_id=p.id, mode="mock", level=p.level, mock_test_id=m.id)
        db.add(a)
    a.chosen_index, a.typed_answer, a.correct = body.chosen_index, body.typed_answer, correct
    a.points, a.answered_at = points_for(p.level, correct), now
    db.flush()
    return {"position": position, "answered": True}      # right or wrong stays hidden until the end


def _score(db: Session, m: MockTest, now: datetime) -> None:
    rows = db.execute(select(MockTestItem.points, Answer.correct)
                      .outerjoin(Answer, (Answer.mock_test_id == MockTestItem.mock_test_id)
                                 & (Answer.problem_id == MockTestItem.problem_id))
                      .where(MockTestItem.mock_test_id == m.id)).all()
    m.max_score = sum(pts for pts, _ in rows)
    m.score = sum(pts for pts, ok in rows if ok)
    m.correct = sum(1 for _, ok in rows if ok)
    m.questions = len(rows)
    end = min(now, m.ends_at) if m.ends_at else now
    m.seconds_used = int((end - m.started_at).total_seconds()) if m.started_at else None
    m.status, m.finished_at = "finished", end


def finish_mock(db: Session, child_id: int, mock_id: int, now: datetime) -> dict:
    """He presses Finish. Skill levels are left alone: a test measures, practice teaches."""
    m = _own_mock(db, child_id, mock_id, lock=True)
    state = _settle_clock(db, m, now)
    if state == "preparing":
        raise Problem(409, "This test has not started yet.")
    if state == "in_progress":
        _score(db, m, now)
    elif state != "finished":
        raise Problem(409, "This test was left for more than two minutes, so it was not scored.", keep=True)
    db.flush()
    return get_mock(db, child_id, mock_id, now)


def mock_history(db: Session, child_id: int, limit: int = 20) -> list[dict]:
    _child(db, child_id)
    rows = db.scalars(select(MockTest).where(MockTest.child_id == child_id, MockTest.status == "finished")
                      .order_by(MockTest.finished_at.desc().nulls_last()).limit(limit))
    return [_mock_summary(m) for m in rows]


def recent_answers(db: Session, child_id: int, limit: int = 20) -> list[dict]:
    """For the Recently answered screen: newest first, with the problem and its key."""
    _child(db, child_id)
    rows = db.execute(select(Answer, ProblemRow).join(ProblemRow, ProblemRow.id == Answer.problem_id)
                      .where(Answer.child_id == child_id)
                      .order_by(Answer.answered_at.desc(), Answer.id.desc()).limit(limit)).all()
    out = []
    for a, p in rows:
        if a.mock_test_id is not None:
            m = db.get(MockTest, a.mock_test_id)
            if m.status not in ("finished", "abandoned"):
                continue                     # answers in a running test stay hidden
        out.append({"answer_id": a.id, "mode": a.mode, "level": a.level, "correct": a.correct, "points": a.points,
                    "chosen_index": a.chosen_index, "typed_answer": a.typed_answer, "trouble_reason": a.trouble_reason,
                    "fixed_on_retry": a.fixed_on_retry, "answered_at": a.answered_at.isoformat(),
                    "problem": _problem_dict(p)})
    return out
