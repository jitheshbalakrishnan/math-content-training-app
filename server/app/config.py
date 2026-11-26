"""Settings read from the environment, with a .env file at the repo root as a fallback."""
import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]          # the repo root
load_dotenv(ROOT / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg:///math_trainer")
SKILL_MAP = ROOT / "skill_map.json"
AGENTS_FILE = Path(__file__).resolve().parents[1] / "config" / "agents.toml"


def agents() -> dict:
    """Each agent's provider and model, from config/agents.toml."""
    with open(AGENTS_FILE, "rb") as f:
        return tomllib.load(f)["agents"]
