#!/usr/bin/env python3
"""Build math-contest-trainer.html from app.src.html and skill_map.json.

    python3 build.py          write the built page
    python3 build.py --check  exit 1 if the built page is out of date
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "app.src.html"
SKILL_MAP = ROOT / "skill_map.json"
OUTPUT = ROOT / "math-contest-trainer.html"
PLACEHOLDER = "__SKILLMAP__"


def build() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    if source.count(PLACEHOLDER) != 1:
        sys.exit(f"{SOURCE.name} must contain {PLACEHOLDER} exactly once")
    skill_map = json.loads(SKILL_MAP.read_text(encoding="utf-8"))
    ids = {skill["id"] for skill in skill_map["skills"]}
    for skill in skill_map["skills"]:
        missing = [p for p in skill["prerequisites"] if p not in ids]
        if missing:
            sys.exit(f"{skill['id']} lists unknown prerequisites: {missing}")
    compact = json.dumps(skill_map, separators=(",", ":"), ensure_ascii=False)
    return source.replace(PLACEHOLDER, compact)


def main() -> None:
    page = build()
    if "--check" in sys.argv[1:]:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != page:
            sys.exit(f"{OUTPUT.name} is out of date. Run: python3 build.py")
        print(f"{OUTPUT.name} is up to date")
        return
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT.name}")


if __name__ == "__main__":
    main()
