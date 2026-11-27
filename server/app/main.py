"""The local API. Run from server/:

    uv run uvicorn app.main:app --port 8000

Only this Mac can reach it by default. To use it from another device at home, set APP_TOKEN in
.env, run with --host 0.0.0.0, and open http://<mac-address>:8000/?token=<APP_TOKEN> once on that
device (see app/access.py).
"""
import os
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import access, schemas, service
from .agents import claude
from .config import CORS_ORIGINS, ROOT, agents
from .db import Session as SessionMaker
from .models import AgentRun

PAGE = ROOT / "math-contest-trainer.html"
APP_TOKEN = os.environ.get("APP_TOKEN", "").strip()

app = FastAPI(title="Math Contest Trainer", version="0.1.0")
if CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def only_allowed_devices(request: Request, call_next):
    ok, why = access.decide(request.client.host if request.client else None, request.url.path, APP_TOKEN,
                            request.cookies.get(access.COOKIE), request.headers.get(access.HEADER))
    if not ok:
        return JSONResponse(status_code=403, content={"code": "not_allowed", "detail": why})
    return await call_next(request)


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


@app.get("/")
def page(token: str | None = None):
    """The app itself, built from src/ by build.py. Served here, its Claude calls come to /api/claude.
    ?token=<APP_TOKEN> lets this browser use the API from another device, then drops it from the address."""
    if token is not None:
        if not access.token_ok(APP_TOKEN, token):
            return PlainTextResponse("That link is not right. Ask a grown-up for the app's link.", status_code=403)
        r = RedirectResponse("/", status_code=303)
        r.set_cookie(access.COOKIE, token, max_age=365 * 24 * 3600, httponly=True, samesite="strict")
        return r
    return FileResponse(PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})


@app.get("/api/health")
def health(db: Session = DB):
    db.execute(text("SELECT 1"))
    return {"ok": True, "claude": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())}


@app.exception_handler(claude.AgentError)
def agent_error(_: Request, e: claude.AgentError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"code": e.code, "detail": e.detail})


@app.post("/api/claude")
def ask_claude(body: schemas.ClaudeIn):
    """Runs in a worker thread (a plain def), so a slow reply does not hold up other requests.
    Every call is recorded in agent_runs, without its text."""
    cfg = agents()[body.agent]
    started = time.monotonic()
    run_row = {"agent": body.agent, "provider": cfg.get("provider", "anthropic"),
               "model": claude.pick_model(cfg, body.tier), "child_id": body.child_id}
    try:
        reply = claude.call(body.agent, cfg, [t.model_dump() for t in body.messages], body.tier)
    except claude.AgentError as e:
        _record(**run_row, ok=False, error=e.code, seconds=round(time.monotonic() - started, 2))
        raise
    _record(**run_row, model_used=reply.model, ok=True, tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
            seconds=reply.seconds)
    return {"text": reply.text, "model": reply.model}


def _record(model_used: str | None = None, **row) -> None:
    """Best effort: a logging failure never costs him his problem."""
    if model_used:
        row["model"] = model_used
    try:
        with SessionMaker() as db:
            if row.get("child_id") is not None and db.get(service.Child, row["child_id"]) is None:
                row["child_id"] = None
            db.add(AgentRun(**row))
            db.commit()
    except Exception:
        pass


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
