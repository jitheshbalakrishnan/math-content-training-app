"""Settings read from the environment, with a .env file at the repo root as a fallback."""
import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]          # the repo root
load_dotenv(ROOT / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg:///math_trainer")
for plain in ("postgresql://", "postgres://"):      # the usual form: use the psycopg 3 driver that is installed
    if DATABASE_URL.startswith(plain):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(plain):]
SKILL_MAP = ROOT / "skill_map.json"
TIMEZONE = os.environ.get("APP_TIMEZONE", "America/New_York")       # the family's calendar day, for daily counts
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
AGENTS_FILE = Path(__file__).resolve().parents[1] / "config" / "agents.toml"


def agents() -> dict:
    """Each agent's provider and model, from config/agents.toml."""
    with open(AGENTS_FILE, "rb") as f:
        return tomllib.load(f)["agents"]
