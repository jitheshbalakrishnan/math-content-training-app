"""The local API. Run from server/:

    uv run uvicorn app.main:app --port 8000

Only this Mac can reach it by default. To use it from another device at home, add
--host 0.0.0.0; there is no sign-in yet, so anyone on the home network could then use it.
"""
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import schemas, service
from .config import CORS_ORIGINS
from .db import Session as SessionMaker

app = FastAPI(title="Math Contest Trainer", version="0.1.0")
if CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


def get_db() -> Iterator[Session]:
    """One transaction per request: committed when the request succeeds, rolled back otherwise."""
    with SessionMaker() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def get_now() -> datetime:
    return datetime.now(timezone.utc)


@app.exception_handler(service.Problem)
def problem(_: Request, e: service.Problem) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"detail": e.message})


DB = Depends(get_db)
NOW = Depends(get_now)


def run(fn: Callable, db: Session):
    """Errors raised inside a service function roll back, and their response still goes out.
    FastAPI sends the response before a dependency's cleanup, so commit here instead."""
    try:
        out = fn()
        db.commit()
        return out
    except service.Problem as e:
        db.commit() if e.keep else db.rollback()
        raise


@app.get("/api/health")
def health(db: Session = DB):
    db.execute(text("SELECT 1"))
    return {"ok": True}


# ---------- children ----------

@app.get("/api/children")
def children(db: Session = DB):
    return service.list_children(db)


@app.post("/api/children", status_code=201)
def add_child(body: schemas.ChildIn, db: Session = DB):
    return run(lambda: service.create_child(db, body), db)


@app.get("/api/children/{child_id}")
def child(child_id: int, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.child_summary(db, child_id, now), db)     # may close a test left too long


@app.patch("/api/children/{child_id}")
def edit_child(child_id: int, body: schemas.ChildPatch, db: Session = DB):
    return run(lambda: service.update_child(db, child_id, body), db)


@app.put("/api/children/{child_id}/skills/{skill}")
def skill_level(child_id: int, skill: str, body: schemas.SkillLevelIn, db: Session = DB):
    return run(lambda: service.set_skill_level(db, child_id, skill, body.level), db)


@app.get("/api/children/{child_id}/seen")
def seen(child_id: int, skill: str | None = None, db: Session = DB):
    return service.seen_problem_ids(db, child_id, skill)


@app.get("/api/children/{child_id}/answers")
def answers(child_id: int, limit: int = 20, db: Session = DB):
    return service.recent_answers(db, child_id, max(1, min(limit, 100)))


# ---------- problems and answers ----------

@app.post("/api/problems", status_code=201)
def add_problem(body: schemas.ProblemIn, db: Session = DB):
    return run(lambda: service.create_problem(db, body), db)


@app.get("/api/problems/{problem_id}")
def problem_by_id(problem_id: int, db: Session = DB):
    return service.get_problem(db, problem_id)


@app.post("/api/children/{child_id}/answers", status_code=201)
def answer(child_id: int, body: schemas.AnswerIn, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.record_answer(db, child_id, body, now), db)


@app.patch("/api/children/{child_id}/answers/{answer_id}")
def edit_answer(child_id: int, answer_id: int, body: schemas.AnswerPatch, db: Session = DB):
    return run(lambda: service.update_answer(db, child_id, answer_id, body), db)


@app.post("/api/children/{child_id}/answers/{answer_id}/retry")
def retry(child_id: int, answer_id: int, body: schemas.RetryIn, db: Session = DB):
    return run(lambda: service.retry_answer(db, child_id, answer_id, body), db)


# ---------- practice sets ----------

@app.post("/api/children/{child_id}/practice")
def practice(child_id: int, body: schemas.PracticeIn, db: Session = DB):
    return run(lambda: service.start_practice(db, child_id, body), db)


@app.patch("/api/children/{child_id}/practice/{session_id}")
def edit_practice(child_id: int, session_id: int, body: schemas.PracticePatch, db: Session = DB):
    return run(lambda: service.update_practice(db, child_id, session_id, body), db)


# ---------- mock tests ----------

@app.get("/api/children/{child_id}/mocks")
def mocks(child_id: int, db: Session = DB):
    return service.mock_history(db, child_id)


@app.post("/api/children/{child_id}/mocks", status_code=201)
def add_mock(child_id: int, body: schemas.MockIn, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.create_mock(db, child_id, body, now), db)


@app.get("/api/children/{child_id}/mocks/{mock_id}")
def mock(child_id: int, mock_id: int, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.get_mock(db, child_id, mock_id, now), db)


@app.post("/api/children/{child_id}/mocks/{mock_id}/start")
def start(child_id: int, mock_id: int, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.start_mock(db, child_id, mock_id, now), db)


@app.post("/api/children/{child_id}/mocks/{mock_id}/heartbeat")
def beat(child_id: int, mock_id: int, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.heartbeat(db, child_id, mock_id, now), db)


@app.put("/api/children/{child_id}/mocks/{mock_id}/answers/{position}")
def mock_answer(child_id: int, mock_id: int, position: int, body: schemas.MockAnswerIn, db: Session = DB,
                now: datetime = NOW):
    return run(lambda: service.answer_mock(db, child_id, mock_id, position, body, now), db)


@app.post("/api/children/{child_id}/mocks/{mock_id}/finish")
def finish(child_id: int, mock_id: int, db: Session = DB, now: datetime = NOW):
    return run(lambda: service.finish_mock(db, child_id, mock_id, now), db)
