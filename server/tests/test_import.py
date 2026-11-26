"""The import script's SQL, checked without a database. A real run is in test_schema.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_state import build, lit  # noqa: E402

EXPORT = Path(__file__).parent / "fixtures" / "export"


def test_quotes_text_and_json():
    assert lit("Ann's pie") == "'Ann''s pie'"
    assert lit(None) == "NULL" and lit(True) == "true" and lit(3) == "3"
    assert lit({"a": "it's"}) == "'{\"a\": \"it''s\"}'::jsonb"


def test_builds_one_transaction_with_a_guard():
    sql = build(EXPORT, "Sam", 5, "Family")
    assert sql.index("\\if :already") < sql.index("BEGIN;") < sql.index("COMMIT;")
    assert "'Sam'" in sql and "Kid''s favorite" in sql


def test_same_question_is_one_problem():
    sql = build(EXPORT, "Sam", 5, "Family")
    assert sql.count("INSERT INTO problems") == 2
    assert sql.count("INSERT INTO answers") == 3


def test_points_follow_the_rule():
    sql = build(EXPORT, "Sam", 5, "Family")
    answers = [line for line in sql.splitlines() if line.startswith("INSERT INTO answers")]
    # right first time at level 4 -> 4; wrong then fixed on retry -> 1; a right guess -> 0
    assert [a.rsplit(", ", 2)[-2] for a in answers] == ["4", "1", "0"]
