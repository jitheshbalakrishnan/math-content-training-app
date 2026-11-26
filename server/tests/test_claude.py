"""The Claude client against a stand-in API on this machine. Standard library only."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents import claude  # noqa: E402

CFG = {"provider": "anthropic", "model": "small", "hard_model": "big", "max_tokens": 100}


class StandIn(BaseHTTPRequestHandler):
    reply = (200, {"content": [{"type": "text", "text": "hi"}], "model": "small", "usage": {"input_tokens": 5, "output_tokens": 2}})
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        StandIn.seen.append({"headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        status, data = StandIn.reply
        out = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture()
def api(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), StandIn)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(claude, "API_URL", f"http://127.0.0.1:{server.server_port}/v1/messages")
    monkeypatch.setattr(claude, "limiter", claude._Limiter(100))
    StandIn.seen = []
    StandIn.reply = (200, {"content": [{"type": "text", "text": "hi"}], "model": "small",
                           "usage": {"input_tokens": 5, "output_tokens": 2}})
    yield StandIn
    server.shutdown()


def test_sends_the_key_model_and_messages(api):
    r = claude.call("writer", CFG, [{"role": "user", "content": "write one"}], key="k-123")
    assert (r.text, r.tokens_in, r.tokens_out) == ("hi", 5, 2)
    sent = api.seen[0]
    assert sent["headers"]["x-api-key"] == "k-123" and sent["headers"]["anthropic-version"] == "2023-06-01"
    assert sent["body"] == {"model": "small", "max_tokens": 100, "messages": [{"role": "user", "content": "write one"}]}


def test_the_stronger_setting_uses_the_hard_model(api):
    claude.call("writer", CFG, [{"role": "user", "content": "x"}], tier="default", key="k")
    claude.call("tutor", {"model": "only"}, [{"role": "user", "content": "x"}], tier="default", key="k")
    assert [s["body"]["model"] for s in api.seen] == ["big", "only"]


def test_turns_are_tidied_for_the_api():
    msgs = [{"role": "assistant", "content": "stray"}, {"role": "user", "content": "rules"},
            {"role": "user", "content": "help"}, {"role": "assistant", "content": ""}, {"role": "assistant", "content": "ok"},
            {"role": "system", "content": "odd"}]
    assert claude.tidy(msgs) == [{"role": "user", "content": "rules\n\nhelp"}, {"role": "assistant", "content": "ok"},
                                 {"role": "user", "content": "odd"}]


@pytest.mark.parametrize("status, code", [(401, "no_key"), (429, "rate_limited"), (400, "bad_request"), (529, "unavailable")])
def test_api_errors_become_codes_the_page_understands(api, status, code):
    api.reply = (status, {"error": {"message": "nope"}})
    with pytest.raises(claude.AgentError) as e:
        claude.call("writer", CFG, [{"role": "user", "content": "x"}], key="k")
    assert e.value.code == code


def test_refused_before_calling(api, monkeypatch):
    for agent, key, msgs, code in [("coach", "k", [{"role": "user", "content": "x"}], "bad_request"),
                                   ("writer", "", [{"role": "user", "content": "x"}], "no_key"),
                                   ("writer", "k", [], "bad_request"),
                                   ("writer", "k", [{"role": "user", "content": "x" * 70_000}], "bad_request")]:
        with pytest.raises(claude.AgentError) as e:
            claude.call(agent, CFG, msgs, key=key)
        assert e.value.code == code
    assert api.seen == []


def test_calls_per_minute_are_capped(api, monkeypatch):
    monkeypatch.setattr(claude, "limiter", claude._Limiter(2))
    t = [0.0]
    for _ in range(2):
        claude.call("tutor", CFG, [{"role": "user", "content": "x"}], key="k", now=lambda: t[0])
    with pytest.raises(claude.AgentError) as e:
        claude.call("tutor", CFG, [{"role": "user", "content": "x"}], key="k", now=lambda: t[0])
    assert e.value.code == "rate_limited"
    t[0] = 61.0
    claude.call("tutor", CFG, [{"role": "user", "content": "x"}], key="k", now=lambda: t[0])


def test_unreachable_api(monkeypatch):
    monkeypatch.setattr(claude, "API_URL", "http://127.0.0.1:9/v1/messages")
    monkeypatch.setattr(claude, "limiter", claude._Limiter(100))
    with pytest.raises(claude.AgentError) as e:
        claude.call("writer", CFG, [{"role": "user", "content": "x"}], key="k")
    assert e.value.code == "unavailable"
