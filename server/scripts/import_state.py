"""Turn progress exported from the hosted app into SQL for the local database.

    python scripts/import_state.py EXPORT_DIR --child Name [--grade 5] [--family Name] > import.sql
    psql math_trainer -f import.sql

EXPORT_DIR holds what the hosted app stored for one learner: state.json, log/attempts/*.json
and, if a test was in progress, mock.json. The script only writes SQL, so the file can be read
before it is run. It runs in one transaction and stops if the child already exists.
Needs only the Python standard library.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.points import points_for  # noqa: E402


def lit(v) -> str:
    """A SQL literal. Text is quoted with doubled single quotes (standard_conforming_strings is on)."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (dict, list)):
        return lit(json.dumps(v, ensure_ascii=False)) + "::jsonb"
    return "'" + str(v).replace("'", "''") + "'"


NAME = re.compile(r"[^\W\d_][\w' .-]{0,39}")   # a first or family name: letters, spaces, ' . -


def echo(sql_text: str) -> str:
    """Print a message. Built in SQL and passed through a variable, so a name never reaches psql's command parser."""
    return f"SELECT {sql_text} AS msg \\gset\n\\echo :msg"


def insert(table: str, row: dict, returning: str | None = None) -> str:
    cols = ", ".join(f'"{c}"' for c in row)
    vals = ", ".join(row.values())
    tail = f" RETURNING id AS {returning} \\gset" if returning else ";"
    return f"INSERT INTO {table} ({cols}) VALUES ({vals}){tail}"


class ImportError_(Exception):
    pass


def build(export: Path, child: str, grade: int | None, family: str) -> str:
    for label, name in (("child", child), ("family", family)):
        if not NAME.fullmatch(name):
            raise ImportError_(f"The {label} name {name!r} can only use letters, spaces, apostrophes, dots and hyphens.")
    mock = export / "mock.json"
    if mock.exists() and json.loads(mock.read_text(encoding="utf-8") or "null"):
        raise ImportError_("This export has a mock test that was not finished (mock.json). Finish or cancel it in the "
                           "app, export again, then import. Nothing was imported.")
    state = json.loads((export / "state.json").read_text(encoding="utf-8"))
    attempts = sorted((json.loads(p.read_text(encoding="utf-8")) for p in (export / "log" / "attempts").glob("*.json")),
                      key=lambda a: a.get("at") or "")
    contest = state.get("contest")
    goals = state.get("goals") or {}
    out = [
        "\\set ON_ERROR_STOP on",
        f"SELECT EXISTS (SELECT 1 FROM children c JOIN families f ON f.id = c.family_id "
        f"WHERE f.name = {lit(family)} AND c.first_name = {lit(child)}) AS already \\gset",
        "\\if :already",
        "  " + echo(lit(f"{child} is already in the database. Nothing was imported.")),
        "  \\quit",
        "\\endif",
        "BEGIN;",
        f"WITH f AS (SELECT id FROM families WHERE name = {lit(family)} ORDER BY id LIMIT 1), "
        f"ins AS (INSERT INTO families (name) SELECT {lit(family)} WHERE NOT EXISTS (SELECT 1 FROM f) RETURNING id) "
        f"SELECT id AS family_id FROM f UNION ALL SELECT id FROM ins \\gset",
        insert("children", {
            "family_id": ":family_id",
            "first_name": lit(child),
            "grade": lit(grade),
            "contest": lit(contest),
            "focus": lit(state.get("focus")),
            "daily_goal": lit(goals.get("day") or 10),
            "weekly_goal": lit(goals.get("week") or 50),
            "placement": lit(state.get("placement") or {}),
            "settings": lit({"tier": state.get("tier", "quick"), "verify": bool(state.get("verify"))}),
        }, returning="child_id"),
    ]
    for t in state.get("custom") or []:         # a sibling may already have brought the same topic into the family
        out.append(insert("custom_topics", {
            "family_id": ":family_id", "skill_id": lit(t["id"]), "name": lit(t["name"]),
            "topic": lit(t.get("topic", "custom")), "contests": lit(t.get("contests") or []), "note": lit(t.get("note")),
        })[:-1] + " ON CONFLICT (family_id, skill_id) DO NOTHING;")
    for skill, s in (state.get("skills") or {}).items():
        out.append(insert("skill_progress", {
            "child_id": ":child_id", "skill": lit(skill), "level": lit(s.get("level", 3)),
            "up": lit(s.get("up", 0)), "down": lit(s.get("down", 0)), "attempts": lit(s.get("n", 0)),
            "correct": lit(s.get("ok", 0)), "reasons": lit(s.get("reasons") or {}), "recent": lit(s.get("recent") or []),
        }))
    mock_var: dict[str, str] = {}              # finish time -> psql variable holding that test's id
    for j, m in enumerate(state.get("mocks") or []):   # past test results: scores only, the questions were not kept
        var = f"m{j}" if m.get("at") else None
        if var:
            mock_var[m["at"]] = var
        out.append(insert("mock_tests", {
            "child_id": ":child_id", "contest": lit(m.get("contest") or (contest if contest in ("kangaroo", "imc", "olympiad") else "kangaroo")),
            "size": lit(m.get("size", "full")), "status": lit("finished"), "unit": lit(m.get("unit", "point")),
            "finished_at": lit(m.get("at")), "questions": lit(m.get("n")), "correct": lit(m.get("correct")),
            "score": lit(m.get("score")), "max_score": lit(m.get("max")), "seconds_used": lit(m.get("secs")),
        }, returning=var))
    imported = 0
    seen: dict[str, str] = {}                   # everything stored about a problem -> psql variable holding its id
    for i, a in enumerate(attempts):
        q = a.get("question")
        if not q or not isinstance(a.get("choices"), list):
            continue
        # Same problem only when every stored field matches, so an answer is never linked to other choices or key.
        key = json.dumps([a.get("skill"), a.get("level", 3), q, a["choices"], a.get("answer"), a.get("figure")],
                         sort_keys=True, ensure_ascii=False)
        var = seen.get(key)
        if var is None:
            var = seen[key] = f"p{i}"
            out.append(insert("problems", {
                "skill": lit(a["skill"]), "level": lit(a.get("level", 3)),
                "contest": lit(contest if contest in ("kangaroo", "imc", "olympiad") else None),
                "question": lit(q), "choices": lit(a["choices"]), "answer_index": lit(a.get("answer")),
                "figure": lit(a.get("figure")), "written_by": lit("import"),
            }, returning=var))
        correct, guessed, fixed = bool(a.get("correct")), a.get("reason") == "guess", bool(a.get("fixed"))
        imported += 1
        row = {
            "child_id": ":child_id", "problem_id": f":{var}", "mode": lit(a.get("mode", "practice")),
            "level": lit(a.get("level", 3)), "chosen_index": lit(a.get("picked")), "correct": lit(correct),
            "trouble_reason": lit(a.get("reason")), "note": lit(a.get("note") or None),
            "hints_used": lit(a.get("hints", 0)), "seconds": lit(round(a["ms"] / 1000) if a.get("ms") else None),
            "retries": lit(a.get("retries", 0)), "fixed_on_retry": lit(fixed),
            "points": lit(points_for(a.get("level", 3), correct, guessed, fixed)),
        }
        if a.get("at"):                         # without one, the database records the import time
            row["answered_at"] = lit(a["at"])
        if a.get("mode") == "mock" and a.get("at") in mock_var:   # a test logs its answers with its own finish time
            row["mock_test_id"] = f":{mock_var[a['at']]}"
        out.append(insert("answers", row))
    skipped = len(attempts) - imported
    out += ["COMMIT;", echo(lit(f"Imported {child}: {len(state.get('skills') or {})} skills, {imported} answers, "
                                f"{len(state.get('mocks') or [])} mock test results."
                                + (f" Skipped {skipped} answers with no question or choices." if skipped else "")))]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", type=Path)
    ap.add_argument("--child", required=True, help="the child's first name")
    ap.add_argument("--grade", type=int)
    ap.add_argument("--family", default="Family")
    args = ap.parse_args()
    if args.grade is not None and not 1 <= args.grade <= 12:
        ap.error("--grade must be between 1 and 12")
    try:
        sys.stdout.write(build(args.export, args.child, args.grade, args.family))
    except ImportError_ as e:
        ap.exit(1, f"{e}\n")


if __name__ == "__main__":
    main()
