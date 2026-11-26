# Local backend

The part of Math Contest Trainer that runs on your Mac: a Postgres database and, later, the
agents that write problems and tutor. This first step is the database and the import of
progress from the hosted app. The page still runs in Claude and still saves there; it is
switched over in a later change.

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
uv run pytest                                   # no database needed
createdb math_trainer_test
TEST_DATABASE_URL=postgresql+psycopg:///math_trainer_test uv run pytest   # also checks a real database
```
