"""Who may use the API. No web framework needed."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.access import decide, token_ok  # noqa: E402


@pytest.mark.parametrize("host, path, expected, cookie, header, ok", [
    ("127.0.0.1", "/api/claude", "", None, None, True),          # this Mac, no secret needed
    ("::1", "/api/children", "", None, None, True),
    ("192.168.1.20", "/", "", None, None, True),                 # the page alone holds nothing
    ("192.168.1.20", "/api/claude", "", None, None, False),      # no secret set: other devices are out
    ("192.168.1.20", "/api/claude", "s3cret", None, None, False),
    ("192.168.1.20", "/api/claude", "s3cret", "nope", None, False),
    ("192.168.1.20", "/api/claude", "s3cret", "s3cret", None, True),
    ("192.168.1.20", "/api/claude", "s3cret", None, "s3cret", True),
    ("192.168.1.20", "/docs", "s3cret", None, None, False),
    (None, "/api/children", "s3cret", None, None, False),
])
def test_decide(host, path, expected, cookie, header, ok):
    assert decide(host, path, expected, cookie, header)[0] is ok


def test_an_empty_secret_never_matches():
    assert not token_ok("", "") and not token_ok("", None) and not token_ok("x", None)
