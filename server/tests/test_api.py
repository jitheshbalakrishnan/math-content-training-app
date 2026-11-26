"""The API end to end, against a real database. Skipped unless TEST_DATABASE_URL is set; see conftest.py."""
from datetime import datetime, timedelta, timezone

import pytest


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.fixture()
def api(clean):
    from fastapi.testclient import TestClient

    from app.main import app, get_now
    clock = Clock()
    app.dependency_overrides[get_now] = clock
    with TestClient(app) as client:
        client.clock = clock
        yield client
    app.dependency_overrides.clear()


def child(api, name="Sam"):
    r = api.post("/api/children", json={"first_name": name, "grade": 5})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def problem(api, skill="number.fractions", level=3, answer_index=1, **kw):
    body = {"skill": skill, "level": level, "question": f"Q {kw.pop('n', 0)}", "choices": ["a", "b", "c", "d", "e"],
            "answer_index": answer_index, **kw}
    r = api.post("/api/problems", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------- children ----------

def test_children_and_a_duplicate_name(api):
    cid = child(api)
    assert api.get("/api/children").json()[0]["first_name"] == "Sam"
    assert api.post("/api/children", json={"first_name": "Sam"}).status_code == 409
    assert api.get("/api/children/999").status_code == 404


def test_settings_change_only_what_is_sent(api):
    cid = child(api)
    r = api.patch(f"/api/children/{cid}", json={"contest": "kangaroo", "daily_goal": 8})
    assert r.json()["goals"] == {"day": 8, "week": 50} and r.json()["grade"] == 5
    assert api.patch(f"/api/children/{cid}", json={"daily_goal": 0}).status_code == 422
    assert api.patch(f"/api/children/{cid}", json={"daily_goal": None}).status_code == 422


# ---------- problems and answers ----------

def test_a_problem_needs_a_key_that_points_at_a_choice(api):
    bad = {"skill": "x", "level": 3, "question": "q", "choices": ["a", "b"], "answer_index": 2}
    assert api.post("/api/problems", json=bad).status_code == 422
    assert api.post("/api/problems", json={**bad, "level": 6, "answer_index": 0}).status_code == 422
    typed = {"skill": "x", "level": 3, "question": "q", "answer_kind": "typed", "accepted_answers": []}
    assert api.post("/api/problems", json=typed).status_code == 422


def test_the_server_marks_answers_and_levels_up(api):
    cid = child(api)
    for n in range(2):
        r = api.post(f"/api/children/{cid}/answers",
                     json={"problem_id": problem(api, n=n), "mode": "practice", "level": 3, "chosen_index": 1})
        assert r.json()["correct"] is True and r.json()["points"] == 3
    assert r.json()["skill"]["level"] == 4
    wrong = api.post(f"/api/children/{cid}/answers",
                     json={"problem_id": problem(api, n=9), "mode": "practice", "level": 4, "chosen_index": 0}).json()
    assert wrong["correct"] is False and wrong["points"] == 0
    s = api.get(f"/api/children/{cid}").json()
    assert (s["today"], s["points"], s["streak"]) == ({"n": 3, "ok": 2}, 6, 1)


def test_typed_answers_accept_equal_forms(api):
    cid = child(api)
    pid = api.post("/api/problems", json={"skill": "x", "level": 2, "question": "half?", "answer_kind": "typed",
                                          "accepted_answers": ["1/2"]}).json()["id"]
    r = api.post(f"/api/children/{cid}/answers", json={"problem_id": pid, "mode": "practice", "level": 2, "typed_answer": "0.5"})
    assert r.json()["correct"] is True


def test_saying_it_was_a_guess_redoes_the_level_change(api):
    cid = child(api)
    first = api.post(f"/api/children/{cid}/answers",
                     json={"problem_id": problem(api, n=1), "mode": "practice", "level": 3, "chosen_index": 1}).json()
    second = api.post(f"/api/children/{cid}/answers",
                      json={"problem_id": problem(api, n=2), "mode": "practice", "level": 3, "chosen_index": 1}).json()
    assert second["skill"]["level"] == 4
    r = api.patch(f"/api/children/{cid}/answers/{second['answer_id']}", json={"trouble_reason": "guess"}).json()
    assert (r["releveled"], r["points"], r["skill"]["level"], r["skill"]["correct"]) == (True, 0, 3, 1)
    # the first answer has a later one built on it, so its level change is left alone
    r = api.patch(f"/api/children/{cid}/answers/{first['answer_id']}", json={"trouble_reason": "guess"}).json()
    assert r["releveled"] is False


def test_a_retry_is_marked_by_the_server(api):
    cid = child(api)
    a = api.post(f"/api/children/{cid}/answers",
                 json={"problem_id": problem(api), "mode": "practice", "chosen_index": 0}).json()
    url = f"/api/children/{cid}/answers/{a['answer_id']}"
    assert api.patch(url, json={"fixed_on_retry": True}).json()["points"] == 0           # a claim alone earns nothing
    miss = api.post(url + "/retry", json={"chosen_index": 3}).json()
    assert (miss["fixed"], miss["retries"], miss["points"]) == (False, 1, 0)
    fix = api.post(url + "/retry", json={"chosen_index": 1}).json()
    assert (fix["fixed"], fix["retries"], fix["points"]) == (True, 2, 1)
    assert api.post(url + "/retry", json={"chosen_index": 1}).status_code == 409
    assert api.get(f"/api/children/{cid}").json()["skills"]["number.fractions"]["level"] == 3   # levels keep the first answer


def test_one_child_cannot_touch_anothers_answers(api):
    sam, ria = child(api), child(api, "Ria")
    a = api.post(f"/api/children/{sam}/answers",
                 json={"problem_id": problem(api), "mode": "practice", "level": 3, "chosen_index": 1}).json()
    assert api.patch(f"/api/children/{ria}/answers/{a['answer_id']}", json={"note": "x"}).status_code == 403
    s = api.post(f"/api/children/{sam}/practice", json={"kind": "daily"}).json()
    r = api.post(f"/api/children/{ria}/answers", json={"problem_id": problem(api, n=3), "mode": "practice", "level": 3,
                                                       "chosen_index": 1, "practice_session_id": s["id"]})
    assert r.status_code == 403


def test_seen_problems_are_listed_per_child(api):
    sam, ria = child(api), child(api, "Ria")
    pid = problem(api)
    api.post(f"/api/children/{sam}/answers", json={"problem_id": pid, "mode": "practice", "level": 3, "chosen_index": 1})
    assert api.get(f"/api/children/{sam}/seen").json() == [pid]
    assert api.get(f"/api/children/{ria}/seen").json() == []


# ---------- practice sets ----------

def test_an_open_practice_set_is_resumed(api):
    cid = child(api)
    s = api.post(f"/api/children/{cid}/practice", json={"kind": "daily", "goal": 10}).json()
    pid = problem(api)
    api.patch(f"/api/children/{cid}/practice/{s['id']}", json={"position": 3, "current_problem_id": pid})
    again = api.post(f"/api/children/{cid}/practice", json={"kind": "topic"}).json()
    assert (again["id"], again["resumed"], again["position"], again["current_problem_id"]) == (s["id"], True, 3, pid)
    api.patch(f"/api/children/{cid}/practice/{s['id']}", json={"status": "done"})
    assert api.post(f"/api/children/{cid}/practice", json={"kind": "topic"}).json()["resumed"] is False
    assert api.patch(f"/api/children/{cid}/practice/{s['id']}", json={"position": 4}).status_code == 409


# ---------- mock tests ----------

def make_mock(api, cid, n=3, minutes=30):
    items = [{"problem_id": problem(api, n=100 + i, answer_index=i % 5), "points": 3} for i in range(n)]
    r = api.post(f"/api/children/{cid}/mocks", json={"contest": "kangaroo", "minutes": minutes, "items": items})
    assert r.status_code == 201, r.text
    return r.json()


def test_a_mock_test_hides_keys_until_it_ends_and_scores_on_finish(api):
    cid = child(api)
    m = make_mock(api, cid)
    assert "answer_index" not in m["items"][0]["problem"]
    m = api.post(f"/api/children/{cid}/mocks/{m['id']}/start").json()
    assert m["seconds_left"] == 30 * 60
    put = lambda pos, i: api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/{pos}", json={"chosen_index": i})
    assert put(0, 0).json() == {"position": 0, "answered": True}           # right, but not said yet
    put(1, 0)                                                                # wrong
    put(1, 1)                                                                # changed to right: only the last answer counts
    put(2, 4)
    put(2, None)                                                             # cleared again
    done = api.post(f"/api/children/{cid}/mocks/{m['id']}/finish").json()
    assert (done["status"], done["score"], done["max_score"], done["correct"]) == ("finished", 6, 9, 2)
    assert done["items"][0]["problem"]["answer_index"] == 0 and done["items"][2]["correct"] is False
    skills = api.get(f"/api/children/{cid}").json()["skills"]
    assert skills == {}                                                     # a test never changes levels


def test_away_for_more_than_two_minutes_abandons_the_test(api):
    cid = child(api)
    m = make_mock(api, cid)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    api.clock.advance(seconds=90)
    assert api.post(f"/api/children/{cid}/mocks/{m['id']}/heartbeat").json()["status"] == "in_progress"
    api.clock.advance(minutes=2, seconds=1)
    r = api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/0", json={"chosen_index": 0})
    assert r.status_code == 409 and "two minutes" in r.json()["detail"]
    assert api.get(f"/api/children/{cid}/mocks/{m['id']}").json()["status"] == "abandoned"   # and it stays so
    assert api.get(f"/api/children/{cid}").json()["live_mock"] is None
    assert api.get(f"/api/children/{cid}/mocks").json() == []                                # not scored


def test_time_running_out_scores_the_test(api):
    cid = child(api)
    m = make_mock(api, cid, minutes=1)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/0", json={"chosen_index": 0})
    api.clock.advance(seconds=61)
    r = api.get(f"/api/children/{cid}/mocks/{m['id']}").json()
    assert (r["status"], r["score"], r["seconds_used"]) == ("finished", 3, 60)


def test_only_one_live_mock_test_and_no_repeated_problems(api):
    cid = child(api)
    m = make_mock(api, cid)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    items = [{"problem_id": problem(api, n=500), "points": 3}]
    assert api.post(f"/api/children/{cid}/mocks", json={"contest": "kangaroo", "minutes": 5, "items": items}).status_code == 409
    api.post(f"/api/children/{cid}/mocks/{m['id']}/finish")
    twice = items * 2
    assert api.post(f"/api/children/{cid}/mocks", json={"contest": "kangaroo", "minutes": 5, "items": twice}).status_code == 422


def test_a_test_still_being_prepared_is_replaced(api):
    cid = child(api)
    old = make_mock(api, cid)
    new = make_mock(api, cid)
    assert api.get(f"/api/children/{cid}/mocks/{old['id']}").json()["status"] == "abandoned"
    assert api.get(f"/api/children/{cid}").json()["live_mock"]["id"] == new["id"]
    assert api.post(f"/api/children/{cid}/mocks/{new['id']}/finish").status_code == 409


def test_recent_answers_hide_a_running_test(api):
    cid = child(api)
    api.post(f"/api/children/{cid}/answers", json={"problem_id": problem(api), "mode": "practice", "level": 3, "chosen_index": 1})
    m = make_mock(api, cid)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/0", json={"chosen_index": 0})
    assert [a["mode"] for a in api.get(f"/api/children/{cid}/answers").json()] == ["practice"]
    api.post(f"/api/children/{cid}/mocks/{m['id']}/finish")
    assert [a["mode"] for a in api.get(f"/api/children/{cid}/answers").json()] == ["mock", "practice"]


def test_a_test_question_key_cannot_be_found_another_way(api):
    cid = child(api)
    m = make_mock(api, cid)
    pid = m["items"][0]["problem"]["id"]
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    assert "answer_index" not in api.get(f"/api/problems/{pid}").json()
    r = api.post(f"/api/children/{cid}/answers", json={"problem_id": pid, "mode": "practice", "level": 3, "chosen_index": 0})
    assert r.status_code == 409
    api.post(f"/api/children/{cid}/mocks/{m['id']}/finish")
    assert api.get(f"/api/problems/{pid}").json()["answer_index"] == 0



# ---------- found in review ----------

def test_level_and_points_come_from_the_problem_not_the_page(api):
    cid = child(api)
    r = api.post(f"/api/children/{cid}/answers",
                 json={"problem_id": problem(api, level=1), "mode": "practice", "level": 5, "chosen_index": 1})
    assert r.json()["points"] == 1


def test_the_same_problem_cannot_be_answered_twice(api):
    cid = child(api)
    body = {"problem_id": problem(api), "mode": "practice", "chosen_index": 1}
    assert api.post(f"/api/children/{cid}/answers", json=body).status_code == 201
    assert api.post(f"/api/children/{cid}/answers", json=body).status_code == 409
    s = api.get(f"/api/children/{cid}").json()
    assert (s["points"], s["skills"]["number.fractions"]["attempts"]) == (3, 1)


def test_a_running_test_does_not_give_its_answers_away(api):
    cid = child(api)
    m = make_mock(api, cid)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/0", json={"chosen_index": 0})      # right
    s = api.get(f"/api/children/{cid}").json()
    assert (s["today"], s["points"]) == ({"n": 0, "ok": 0}, 0)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/finish")
    s = api.get(f"/api/children/{cid}").json()
    assert (s["today"], s["points"]) == ({"n": 1, "ok": 1}, 3)


def test_an_abandoned_test_earns_nothing(api):
    cid = child(api)
    m = make_mock(api, cid)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/0", json={"chosen_index": 0})
    api.clock.advance(minutes=5)
    s = api.get(f"/api/children/{cid}").json()
    assert (s["live_mock"], s["points"], s["today"]["n"]) == (None, 0, 0)


def test_keys_stay_hidden_from_a_sibling_while_one_child_takes_a_test(api):
    sam, ria = child(api), child(api, "Ria")
    shared = problem(api, n=77, answer_index=2)
    # Ria finishes a test with the problem, then Sam starts one with it
    rm = api.post(f"/api/children/{ria}/mocks", json={"contest": "kangaroo", "minutes": 5,
                                                     "items": [{"problem_id": shared, "points": 3}]}).json()
    api.post(f"/api/children/{ria}/mocks/{rm['id']}/start")
    api.put(f"/api/children/{ria}/mocks/{rm['id']}/answers/0", json={"chosen_index": 2})
    api.post(f"/api/children/{ria}/mocks/{rm['id']}/finish")
    sm = api.post(f"/api/children/{sam}/mocks", json={"contest": "kangaroo", "minutes": 5,
                                                     "items": [{"problem_id": shared, "points": 3}]}).json()
    api.post(f"/api/children/{sam}/mocks/{sm['id']}/start")
    ria_view = api.get(f"/api/children/{ria}/mocks/{rm['id']}").json()["items"][0]
    assert "answer_index" not in ria_view["problem"] and "correct" not in ria_view
    assert api.get(f"/api/children/{ria}/answers").json() == []
    other = api.post(f"/api/children/{child(api, 'Bo')}/answers", json={"problem_id": shared, "mode": "practice",
                                                                         "chosen_index": 2})
    assert other.status_code == 409


def test_recent_answers_still_fill_the_page_when_some_are_hidden(api):
    cid = child(api)
    for n in range(3):
        api.post(f"/api/children/{cid}/answers", json={"problem_id": problem(api, n=n), "mode": "practice", "chosen_index": 1})
    m = make_mock(api, cid, n=3)
    api.post(f"/api/children/{cid}/mocks/{m['id']}/start")
    for pos in range(3):
        api.put(f"/api/children/{cid}/mocks/{m['id']}/answers/{pos}", json={"chosen_index": 0})
    assert len(api.get(f"/api/children/{cid}/answers?limit=3").json()) == 3


def test_a_test_cannot_reuse_seen_or_withdrawn_problems(api, clean):
    cid = child(api)
    seen = problem(api, n=1)
    api.post(f"/api/children/{cid}/answers", json={"problem_id": seen, "mode": "practice", "chosen_index": 1})
    body = lambda pid: {"contest": "kangaroo", "minutes": 5, "items": [{"problem_id": pid, "points": 3}]}
    assert api.post(f"/api/children/{cid}/mocks", json=body(seen)).status_code == 422
    retired = problem(api, n=2)
    with clean.begin() as c:
        c.exec_driver_sql(f"UPDATE problems SET status = 'retired' WHERE id = {retired}")
    assert api.post(f"/api/children/{cid}/mocks", json=body(retired)).status_code == 422


def test_nulls_and_blank_keys_are_refused_politely(api):
    cid = child(api)
    s = api.post(f"/api/children/{cid}/practice", json={"kind": "daily"}).json()
    assert api.patch(f"/api/children/{cid}/practice/{s['id']}", json={"position": None}).status_code == 422
    assert api.patch(f"/api/children/{cid}/practice/{s['id']}", json={"status": None}).status_code == 422
    typed = {"skill": "x", "level": 3, "question": "q", "answer_kind": "typed", "accepted_answers": ["  "]}
    assert api.post("/api/problems", json=typed).status_code == 422


# ---------- the page and Claude calls ----------

def test_the_page_is_served(api):
    r = api.get("/")
    assert r.status_code == 200 and "Math Contest Trainer" in r.text


def test_claude_calls_use_the_configured_model_and_are_recorded(api, clean, monkeypatch):
    from app.agents import claude
    seen = {}

    def fake(agent, cfg, messages, tier=None, key=None, now=None):
        seen.update(agent=agent, model=claude.pick_model(cfg, tier), messages=messages)
        return claude.Reply(text='{"answer":"C"}', model="claude-sonnet-5-5", tokens_in=40, tokens_out=8, seconds=0.5)
    monkeypatch.setattr(claude, "call", fake)
    cid = child(api)
    r = api.post("/api/claude", json={"agent": "checker", "messages": [{"role": "user", "content": "solve"}], "child_id": cid})
    assert r.json() == {"text": '{"answer":"C"}', "model": "claude-sonnet-5-5"}
    assert seen["model"] == "claude-sonnet-5-5"                  # from config/agents.toml
    with clean.connect() as c:
        row = c.exec_driver_sql("SELECT agent, model, child_id, tokens_in, tokens_out, ok FROM agent_runs").one()
    assert tuple(row) == ("checker", "claude-sonnet-5-5", cid, 40, 8, True)


def test_a_failed_claude_call_says_why_and_is_recorded(api, clean, monkeypatch):
    from app.agents import claude

    def fail(*a, **k):
        raise claude.AgentError("no_key", 503, "ANTHROPIC_API_KEY is not set in .env.")
    monkeypatch.setattr(claude, "call", fail)
    r = api.post("/api/claude", json={"agent": "writer", "messages": [{"role": "user", "content": "x"}], "child_id": 999})
    assert r.status_code == 503 and r.json()["code"] == "no_key"
    with clean.connect() as c:
        assert tuple(c.exec_driver_sql("SELECT agent, ok, error, child_id FROM agent_runs").one()) == ("writer", False, "no_key", None)


def test_only_live_agents_can_be_called(api):
    r = api.post("/api/claude", json={"agent": "coach", "messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 422
