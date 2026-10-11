#!/usr/bin/env python3
"""Build math-contest-trainer.html from the files under src/ and skill_map.json.

    python3 build.py          write the built page
    python3 build.py --check  exit 1 if the built page is out of date

The page is src/index.html with every file in src/css and src/js pasted in,
in file-name order, and the skill map embedded. The numbers at the start of
each file name set that order; the scripts share one scope, so a file may use
anything defined in a file that comes before it.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SHELL = SRC / "index.html"
SKILL_MAP = ROOT / "skill_map.json"
OUTPUT = ROOT / "math-contest-trainer.html"
CSS_SLOT = "/*__CSS__*/\n"
JS_SLOT = "/*__JS__*/\n"
MAP_SLOT = "__SKILLMAP__"


def bundle(folder: str, ext: str) -> str:
    files = sorted((SRC / folder).glob(f"*.{ext}"))
    if not files:
        sys.exit(f"no .{ext} files found in src/{folder}")
    return "".join(f.read_text(encoding="utf-8") for f in files)


def once(text: str, slot: str, where: str) -> None:
    if text.count(slot) != 1:
        sys.exit(f"{where} must contain {slot.strip()} exactly once")


def build() -> str:
    shell = SHELL.read_text(encoding="utf-8")
    once(shell, CSS_SLOT, "src/index.html")
    once(shell, JS_SLOT, "src/index.html")
    script = bundle("js", "js")
    once(script, MAP_SLOT, "the files in src/js together")
    skill_map = json.loads(SKILL_MAP.read_text(encoding="utf-8"))
    ids = {skill["id"] for skill in skill_map["skills"]}
    for skill in skill_map["skills"]:
        missing = [p for p in skill["prerequisites"] if p not in ids]
        if missing:
            sys.exit(f"{skill['id']} lists unknown prerequisites: {missing}")
    compact = json.dumps(skill_map, separators=(",", ":"), ensure_ascii=False)
    page = shell.replace(CSS_SLOT, bundle("css", "css")).replace(JS_SLOT, script)
    return page.replace(MAP_SLOT, compact)


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
