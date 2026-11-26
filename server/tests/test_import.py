"""The import script's SQL, checked without a database. A real run is in test_schema.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_state import build, lit  # noqa: E402

EXPORT = Path(__file__).parent / "fixtures" / "sample_export"


def test_quotes_text_and_json():
    assert lit("Ann's pie") == "'Ann''s pie'"
    assert lit(None) == "NULL" and lit(True) == "true" and lit(3) == "3"
    assert lit({"a": "it's"}) == "'{\"a\": \"it''s\"}'::jsonb"


def test_builds_one_transaction_with_a_guard():
    sql = build(EXPORT, "Sam", 5, "Family")
    assert sql.index("\\if :already") < sql.index("BEGIN;") < sql.index("COMMIT;")
    assert "'Sam'" in sql and "Kid''s favorite" in sql


def test_problems_merge_only_when_everything_matches():
    sql = build(EXPORT, "Sam", 5, "Family")
    # a2 and a3 are the same problem; a4 has the same question with other choices, so it is its own problem
    assert sql.count("INSERT INTO problems") == 3
    assert sql.count("INSERT INTO answers") == 4


def test_points_follow_the_rule():
    sql = build(EXPORT, "Sam", 5, "Family")
    answers = [line for line in sql.splitlines() if line.startswith("INSERT INTO answers")]
    # right first time at level 4 -> 4; wrong then fixed on retry -> 1; a right guess -> 0; right -> 4
    assert [a.rsplit(", ", 2)[-2] for a in answers] == ["4", "1", "0", "4"]
