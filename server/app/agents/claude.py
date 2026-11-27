"""One Claude call for an agent, with the model set in config/agents.toml.

Plain standard library (no SDK), so it can be tested against a stand-in server. The key comes
from ANTHROPIC_API_KEY in .env and never reaches the page.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

API_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"
API_VERSION = "2023-06-01"
TIMEOUT_S = 150                  # the page gives up after the same time
MAX_INPUT_CHARS = 60_000         # a prompt larger than this is a bug, not a question
LIVE_AGENTS = ("writer", "checker", "tutor")
CALLS_PER_MINUTE = 40            # a loop in the page should hit this long before it hits the bill


class AgentError(Exception):
    """code is what the page shows a message for: no_key, rate_limited, bad_request, unavailable, timeout."""
    def __init__(self, code: str, status: int, detail: str = ""):
        super().__init__(detail or code)
        self.code, self.status, self.detail = code, status, detail


@dataclass
class Reply:
    text: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    seconds: float


class _Limiter:
    """Calls in the last minute, shared by all requests in this server."""
    def __init__(self, per_minute: int):
        self.per_minute, self.times, self.lock = per_minute, [], threading.Lock()

    def take(self, now: float) -> bool:
        with self.lock:
            self.times = [t for t in self.times if now - t < 60]
            if len(self.times) >= self.per_minute:
                return False
            self.times.append(now)
            return True


limiter = _Limiter(CALLS_PER_MINUTE)


def pick_model(cfg: dict, tier: str | None) -> str:
    """'default' is the page's stronger setting for problem writing; it uses hard_model where an agent has one."""
    return cfg.get("hard_model", cfg["model"]) if tier == "default" else cfg["model"]


def tidy(messages: list[dict]) -> list[dict]:
    """Messages the API accepts: text only, starting with the child's side, same-side turns joined."""
    out: list[dict] = []
    for m in messages:
        role = "assistant" if m.get("role") == "assistant" else "user"
        text = str(m.get("content") or "").strip()
        if not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if not out:
        raise AgentError("bad_request", 422, "There is nothing to send.")
    if sum(len(m["content"]) for m in out) > MAX_INPUT_CHARS:
        raise AgentError("bad_request", 422, "That prompt is too long.")
    return out


def call(agent: str, cfg: dict, messages: list[dict], tier: str | None = None, key: str | None = None,
         now=time.monotonic) -> Reply:
    if agent not in LIVE_AGENTS:
        raise AgentError("bad_request", 422, f"Unknown agent {agent!r}.")
    if cfg.get("provider", "anthropic") != "anthropic":
        raise AgentError("unavailable", 501, f"Provider {cfg.get('provider')!r} is not supported yet.")
    key = key if key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
    if not key.strip():
        raise AgentError("no_key", 503, "ANTHROPIC_API_KEY is not set in .env.")
    msgs = tidy(messages)
    if not limiter.take(now()):
        raise AgentError("rate_limited", 429, "Too many calls in the last minute.")
    model = pick_model(cfg, tier)
    body = json.dumps({"model": model, "max_tokens": int(cfg.get("max_tokens", 2000)), "messages": msgs}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json", "x-api-key": key.strip(), "anthropic-version": API_VERSION})
    start = now()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            detail = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        if status in (401, 403):
            raise AgentError("no_key", 503, "The Claude key was refused. Check ANTHROPIC_API_KEY in .env.")
        if status == 429:
            raise AgentError("rate_limited", 429, detail or "Claude is busy. Wait a minute.")
        if status in (400, 404, 413, 422):
            raise AgentError("bad_request", 502, detail or f"Claude refused the request ({status}).")
        raise AgentError("unavailable", 502, detail or f"Claude answered with an error ({status}).")
    except TimeoutError:
        raise AgentError("timeout", 504, "Claude took too long to answer.")
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise AgentError("timeout", 504, "Claude took too long to answer.")
        raise AgentError("unavailable", 502, f"Could not reach Claude: {e.reason}")
    try:                                     # a proxy or outage can answer 200 with an HTML page
        data = json.loads(raw)
        blocks = data["content"]
        if not isinstance(blocks, list):
            raise TypeError("content is not a list")
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise AgentError("unavailable", 502, "Claude's answer could not be read.")
    usage = data.get("usage") or {}
    return Reply(text=text, model=data.get("model", model), tokens_in=usage.get("input_tokens"),
                 tokens_out=usage.get("output_tokens"), seconds=round(now() - start, 2))
