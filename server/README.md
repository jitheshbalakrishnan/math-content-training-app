# Local backend

The part of Math Contest Trainer that runs on your Mac: a Postgres database, an API, and the
agents that write problems, check answers and tutor, using your own Claude key.

The app can now be opened from this server at http://localhost:8000. Its Claude calls then go
through the server with the model each agent is set to in `config/agents.toml`. **For now it
still saves progress in the browser, not in the database**, so keep using the copy in Claude
for real practice until the next change moves saving to the API.

## One-time setup

```bash
brew install postgresql@17 && brew services start postgresql@17
createdb math_trainer

cd ~/code/math-content-training-app/server
uv sync
uv run alembic upgrade head        # creates the tables
```

Settings come from `.env` at the repo root (never committed):

```
ANTHROPIC_API_KEY=...
DATABASE_URL=postgresql+psycopg:///math_trainer
```

`DATABASE_URL` can be left out when the database is called `math_trainer` on this Mac.

## Run the API

```bash
uv run alembic upgrade head          # after every git pull, in case there is a new migration
uv run uvicorn app.main:app --port 8000
```

Then open http://localhost:8000 for the app, or http://localhost:8000/docs to see and try every route. Only this Mac can reach it.
Adding `--host 0.0.0.0` lets other devices at home use it, but there is no sign-in yet, so
anyone on your home network could.

Optional settings in `.env`: `APP_TIMEZONE` (default `America/New_York`, used for daily counts
and streaks) and `CORS_ORIGINS` (comma-separated, for a page served from another address).

### What it does

| Route | For |
|---|---|
| `GET /api/children`, `POST /api/children` | The "who's practicing?" list; add a child |
| `GET /api/children/{id}` | Home and progress in one call: skills, today, week, streak, points, best test, open practice set, live test |
| `PATCH /api/children/{id}` | Contest, focus, goals, grade, settings |
| `POST /api/problems` | Store a written problem; its key is checked |
| `POST /api/children/{id}/answers` | Record an answer. The server marks it, changes the level and gives points |
| `PATCH /api/children/{id}/answers/{answer}` | His reason, a note, or a retry result. Saying it was a guess redoes the level change while it is the latest answer for that skill |
| `GET /api/children/{id}/answers` | Recently answered, newest first |
| `GET /api/children/{id}/seen` | Problems he has already had, so none repeats |
| `POST /api/children/{id}/practice` | Start a practice set, or get the open one back |
| `POST /api/children/{id}/mocks` … `/start`, `/heartbeat`, `/answers/{n}`, `/finish` | Mock tests: keys hidden until the end, last answer kept, scored when time runs out, abandoned after two minutes away |
| `GET /` | The app |
| `POST /api/claude` | One call for the writer, checker or tutor, with the model from `config/agents.toml`. Recorded in `agent_runs` (model, tokens, time, failures), without the text. At most 40 calls a minute |

## Import progress from the hosted app

1. Export the learner's saved data into a folder outside the repo (Claude can do this
   for you with the artifact's data tool). It holds `state.json`, `log/attempts/*.json`
   and, if a test was running, `mock.json`.
2. Turn it into SQL, read it if you like, then run it:

```bash
uv run python scripts/import_state.py ~/math-trainer-export --child Name --grade 5 > import.sql
psql math_trainer -f import.sql
```

It runs in one transaction and does nothing if that child is already there.

## Files

| Path | What it holds |
|---|---|
| `app/main.py` | The API routes |
| `app/service.py` | What each route does |
| `app/rules/` | Leveling, marking, the mock test clock, days and streaks: plain Python |
| `app/agents/claude.py` | One Claude call for an agent, with your key |
| `app/models.py` | The tables, as SQLAlchemy models |
| `app/points.py` | The reward points rule |
| `app/config.py` | Settings, and each agent's model from `config/agents.toml` |
| `config/agents.toml` | Which model each agent uses |
| `migrations/sql/0001_initial.sql` | The first schema, as plain SQL |
| `migrations/versions/` | Alembic migrations |
| `scripts/import_state.py` | Hosted-app progress to SQL |

## Changing the schema

Edit `app/models.py`, then write the next migration in `migrations/versions/`
(`uv run alembic revision --autogenerate -m "what changed"` drafts one; read it before
using it). `tests/test_schema.py` fails if the models and the migrations disagree.

## Tests

```bash
uv run pytest                                   # the rules and the import, no database needed
createdb math_trainer_test
TEST_DATABASE_URL=postgresql+psycopg:///math_trainer_test uv run pytest   # also the API and migrations
```
