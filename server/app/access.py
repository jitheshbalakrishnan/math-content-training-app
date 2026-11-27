"""Who may use the API.

Requests from this Mac are always allowed. Another device (a phone or tablet at home, when the
server runs with --host 0.0.0.0) needs the secret APP_TOKEN from .env: open the app once at
http://<mac-address>:8000/?token=<APP_TOKEN> and that browser keeps a cookie. Without APP_TOKEN
set, other devices can open the page but cannot use the API, so they cannot spend the Claude key
or read anyone's progress.
"""
import hmac

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
COOKIE = "mct_token"
HEADER = "x-app-token"
OPEN_TO_ALL = {"/", "/favicon.ico"}          # the page itself holds no data and no key


def token_ok(expected: str, presented: str | None) -> bool:
    return bool(expected) and presented is not None and hmac.compare_digest(expected.encode(), presented.encode())


def decide(host: str | None, path: str, expected: str, cookie: str | None, header: str | None) -> tuple[bool, str]:
    """(allowed, reason shown when not)."""
    if host in LOOPBACK or path in OPEN_TO_ALL:
        return True, ""
    if not expected:
        return False, "This app can only be used on the computer it runs on. To use it on another device, set APP_TOKEN in .env."
    if token_ok(expected, cookie) or token_ok(expected, header):
        return True, ""
    return False, "Open the app once with its secret link on this device first."
