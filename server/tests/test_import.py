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


# ---------- edge cases found in review ----------
import json  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402
from import_state import ImportError_  # noqa: E402


def copy_export(tmp_path):
    dst = tmp_path / "export"
    shutil.copytree(EXPORT, dst)
    return dst


@pytest.mark.parametrize("name", ["D'Souza", "Mary-Jane", "Ana Lucia", "José"])
def test_real_names_are_accepted_and_kept_out_of_psql_commands(name):
    sql = build(EXPORT, name, 5, "Family")
    for line in sql.splitlines():           # a name may appear only inside a quoted SQL literal
        if line.lstrip().startswith("\\"):
            assert name not in line


@pytest.mark.parametrize("name", ["x' \\! echo hi '", "a\\b", "", "Sam\nBob", "7up"])
def test_names_that_could_reach_psql_are_refused(name):
    with pytest.raises(ImportError_):
        build(EXPORT, name, 5, "Family")


def test_an_unfinished_mock_test_stops_the_import(tmp_path):
    export = copy_export(tmp_path)
    (export / "mock.json").write_text(json.dumps({"v": 1, "phase": "run", "items": []}))
    with pytest.raises(ImportError_, match="not finished"):
        build(export, "Sam", 5, "Family")


def test_an_answer_without_a_time_gets_the_import_time(tmp_path):
    export = copy_export(tmp_path)
    a = json.loads((export / "log/attempts/a1.json").read_text())
    del a["at"]
    (export / "log/attempts/a1.json").write_text(json.dumps(a))
    first = [line for line in build(export, "Sam", 5, "Family").splitlines() if line.startswith("INSERT INTO answers")][0]
    assert "answered_at" not in first


def test_added_topics_do_not_clash_with_a_sibling():
    assert "ON CONFLICT (family_id, skill_id) DO NOTHING" in build(EXPORT, "Sam", 5, "Family")


def test_mock_answers_are_linked_to_their_test(tmp_path):
    export = copy_export(tmp_path)
    (export / "log/attempts/m1.json").write_text(json.dumps({
        "at": "2026-10-01T15:00:00Z", "skill": "number.fractions", "level": 3, "mode": "mock",
        "question": "What is 1/3 of 12?", "figure": None, "choices": ["2", "3", "4", "6", "9"],
        "answer": 2, "picked": None, "correct": False, "ms": None, "hints": 0, "reason": None, "note": ""}))
    sql = build(export, "Sam", 5, "Family")
    mock_answer = [line for line in sql.splitlines() if "'mock'" in line and line.startswith("INSERT INTO answers")][0]
    assert ":m0" in mock_answer and "RETURNING id AS m0" in sql


def test_old_results_and_problems_do_not_guess_a_contest():
    sql = build(EXPORT, "Sam", 5, "Family")
    mock = [line for line in sql.splitlines() if line.startswith("INSERT INTO mock_tests")][0]
    assert "'kangaroo'" not in mock and "NULL" in mock
    assert all('"contest"' not in line for line in sql.splitlines() if line.startswith("INSERT INTO problems"))
