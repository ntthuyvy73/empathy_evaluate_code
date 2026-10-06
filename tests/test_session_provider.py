"""Mock-based tests for ``HttpSessionUsageProvider`` (Task 6.2).

These tests exercise the I/O shell of the Session Capacity Monitor — the
pluggable HTTP usage provider — in isolation. The proxy's real usage endpoint
is not yet confirmed, so the provider is fully config-driven and must never
propagate a raw exception. Per the design's *Testing Strategy > Integration /
smoke tests*, the HTTP layer is covered by mock/example tests (not property
tests): a stubbed HTTP response body is fed in and the ``Ok`` / ``Invalid`` /
``RetrievalError`` mapping is asserted.

All HTTP is stubbed by patching ``mindeval.session_monitor.urllib.request.urlopen``
so no real network call is ever made.

Validates: Requirements 2.1, 2.2, 2.3, 6.1.
"""

import io
import json
from contextlib import contextmanager
from unittest import mock

import pytest
import urllib.error

import mindeval.session_monitor as sm
from mindeval.session_monitor import (
    HttpSessionUsageProvider,
    Invalid,
    MonitorConfig,
    Ok,
    RetrievalError,
)


# --- Test helpers -------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for the object returned by ``urllib.request.urlopen``.

    Supports the context-manager protocol and a ``read()`` returning bytes,
    which is all :meth:`HttpSessionUsageProvider.get_usage_percentage` uses.
    """

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return self._body


def _json_response(payload) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload).encode("utf-8"))


@contextmanager
def _patch_urlopen(side_effect=None, return_value=None):
    """Patch the module-level ``urllib.request.urlopen`` used by the provider."""
    with mock.patch.object(sm.urllib.request, "urlopen") as urlopen:
        if side_effect is not None:
            urlopen.side_effect = side_effect
        else:
            urlopen.return_value = return_value
        yield urlopen


def _make_provider(
    *,
    url="http://localhost:20128/api/session",
    method="GET",
    headers=None,
    json_path="usage_percent",
    timeout=10.0,
):
    return HttpSessionUsageProvider(
        url=url,
        method=method,
        headers=headers or {},
        json_path=json_path,
        timeout=timeout,
    )


# --- json_path extraction → Ok ------------------------------------------------


def test_top_level_json_path_returns_ok():
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_json_response({"usage_percent": 42})):
        result = provider.get_usage_percentage()
    assert result == Ok(42.0)


def test_nested_json_path_returns_ok():
    provider = _make_provider(json_path="data.session.usage_percent")
    payload = {"data": {"session": {"usage_percent": 73.5}}}
    with _patch_urlopen(return_value=_json_response(payload)):
        result = provider.get_usage_percentage()
    assert result == Ok(73.5)


def test_numeric_string_value_is_parsed_to_ok():
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_json_response({"usage_percent": "88"})):
        result = provider.get_usage_percentage()
    assert result == Ok(88.0)


@pytest.mark.parametrize("boundary", [0, 100])
def test_boundary_values_are_ok(boundary):
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_json_response({"usage_percent": boundary})):
        result = provider.get_usage_percentage()
    assert result == Ok(float(boundary))


def test_request_is_built_with_configured_url_method_and_headers():
    provider = _make_provider(
        url="http://localhost:20128/api/usage",
        method="POST",
        headers={"Authorization": "Bearer token123"},
        json_path="usage_percent",
        timeout=5.0,
    )
    with _patch_urlopen(return_value=_json_response({"usage_percent": 10})) as urlopen:
        result = provider.get_usage_percentage()

    assert result == Ok(10.0)
    # The Request object is the first positional arg to urlopen.
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:20128/api/usage"
    assert request.get_method() == "POST"
    assert request.headers.get("Authorization") == "Bearer token123"
    # timeout is forwarded as a keyword argument.
    assert urlopen.call_args.kwargs.get("timeout") == 5.0


# --- out-of-range payload → Invalid -------------------------------------------


@pytest.mark.parametrize("value", [-1, 101, 150.5, -0.01])
def test_out_of_range_value_is_invalid(value):
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_json_response({"usage_percent": value})):
        result = provider.get_usage_percentage()
    assert isinstance(result, Invalid)
    assert result.raw == value


def test_unparseable_value_is_invalid():
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_json_response({"usage_percent": "not-a-number"})):
        result = provider.get_usage_percentage()
    assert isinstance(result, Invalid)


# --- non-200 / HTTPError → RetrievalError -------------------------------------


def test_http_error_is_retrieval_error():
    provider = _make_provider()
    http_error = urllib.error.HTTPError(
        url="http://localhost:20128/api/session",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with _patch_urlopen(side_effect=http_error):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert "401" in result.detail


def test_http_error_500_is_retrieval_error():
    provider = _make_provider()
    http_error = urllib.error.HTTPError(
        url="http://localhost:20128/api/session",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with _patch_urlopen(side_effect=http_error):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert "500" in result.detail


# --- URLError / network / timeout → RetrievalError ----------------------------


def test_url_error_is_retrieval_error():
    provider = _make_provider()
    with _patch_urlopen(side_effect=urllib.error.URLError("connection refused")):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert "network error" in result.detail


def test_timeout_is_retrieval_error():
    provider = _make_provider()
    # socket timeouts surface as a bare TimeoutError from urlopen; the provider's
    # catch-all converts it to a RetrievalError rather than propagating.
    with _patch_urlopen(side_effect=TimeoutError("timed out")):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)


# --- non-JSON body → RetrievalError -------------------------------------------


def test_non_json_body_is_retrieval_error():
    provider = _make_provider(json_path="usage_percent")
    with _patch_urlopen(return_value=_FakeResponse(b"<html>not json</html>")):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert "invalid JSON" in result.detail


def test_missing_json_path_key_is_retrieval_error():
    provider = _make_provider(json_path="data.session.usage_percent")
    with _patch_urlopen(return_value=_json_response({"data": {"other": 1}})):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert "could not extract usage" in result.detail


def test_descend_into_non_object_is_retrieval_error():
    provider = _make_provider(json_path="data.session.usage_percent")
    # ``data`` is a scalar, so descending into ``session`` cannot work.
    with _patch_urlopen(return_value=_json_response({"data": 5})):
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)


# --- unconfigured provider → RetrievalError (no HTTP call) --------------------


def test_unconfigured_url_returns_retrieval_error_without_calling_http():
    provider = _make_provider(url=None)
    with _patch_urlopen(return_value=_json_response({"usage_percent": 10})) as urlopen:
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert result.detail == "provider not configured"
    urlopen.assert_not_called()


def test_unconfigured_json_path_returns_retrieval_error_without_calling_http():
    provider = _make_provider(json_path=None)
    with _patch_urlopen(return_value=_json_response({"usage_percent": 10})) as urlopen:
        result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)
    assert result.detail == "provider not configured"
    urlopen.assert_not_called()


def test_empty_url_returns_retrieval_error():
    provider = _make_provider(url="")
    result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)


# --- from_config wiring -------------------------------------------------------


def test_from_config_builds_provider_from_monitor_config():
    config = MonitorConfig(
        provider_url="http://localhost:20128/api/session",
        provider_method="GET",
        provider_headers={"Authorization": "Bearer abc"},
        provider_json_path="data.usage_percent",
        provider_timeout=7.5,
    )
    provider = HttpSessionUsageProvider.from_config(config)
    assert provider.url == "http://localhost:20128/api/session"
    assert provider.method == "GET"
    assert provider.headers == {"Authorization": "Bearer abc"}
    assert provider.json_path == "data.usage_percent"
    assert provider.timeout == 7.5

    with _patch_urlopen(return_value=_json_response({"data": {"usage_percent": 33}})):
        result = provider.get_usage_percentage()
    assert result == Ok(33.0)


def test_from_config_with_default_unconfigured_provider_returns_retrieval_error():
    # Default MonitorConfig leaves url/json_path unset → fail-safe RetrievalError.
    provider = HttpSessionUsageProvider.from_config(MonitorConfig())
    result = provider.get_usage_percentage()
    assert isinstance(result, RetrievalError)


# --- Opt-in wiring-confirmation smoke test (Task 6.3) -------------------------
#
# This is a *wiring-confirmation* smoke test, NOT a property test and NOT a mock
# test. Unlike every test above (which stubs ``urlopen`` so no real network call
# is ever made), this test deliberately performs a **real HTTP request** against
# the live Router_Proxy dashboard endpoint.
#
# IMPORTANT — it is SKIPPED BY DEFAULT. It only runs when the environment
# variable ``RUN_SESSION_SMOKE`` is set, because it has two hard external
# prerequisites that do not exist in CI or on a clean checkout:
#
#   1. The 9router proxy must be running and reachable at
#      ``http://localhost:20128`` (the ``claude_9router`` judge's proxy).
#   2. The real dashboard *session-usage* endpoint must have been **confirmed**
#      and wired into configuration — its path, auth header/token, and the JSON
#      field that holds the percentage. As documented in the design's research
#      findings, that endpoint was NOT confirmed at authoring time (every probed
#      ``/api/*`` path returned HTTP 401 with the OpenAI bearer key), so until an
#      operator fills in the confirmed values this test must stay opt-in.
#
# How to run it once the endpoint is confirmed and the proxy is up::
#
#     # Using the provider block from config.json (session_monitor.provider):
#     RUN_SESSION_SMOKE=1 pytest tests/test_session_provider.py -k smoke -s
#
#     # Or point it at the endpoint directly via env vars (overrides config.json):
#     RUN_SESSION_SMOKE=1 \
#       SESSION_SMOKE_URL=http://localhost:20128/api/session \
#       SESSION_SMOKE_JSON_PATH=usage_percent \
#       SESSION_SMOKE_AUTH="Bearer <dashboard-token>" \
#       pytest tests/test_session_provider.py -k smoke -s
#
# The test asserts that ``HttpSessionUsageProvider.get_usage_percentage()``
# returns a parseable percentage (an ``Ok``) — i.e. that the configured endpoint,
# auth, and ``json_path`` line up with the live response. A ``RetrievalError`` or
# ``Invalid`` result fails the test, since those mean the wiring is still wrong.
#
# Validates: Requirements 2.1.

import os

# The base URL of the proxy the claude_9router judge talks to. The real session
# dashboard lives on this host; see the design's research findings.
_SMOKE_PROXY_BASE = "http://localhost:20128"


def _load_smoke_provider_config():
    """Resolve the provider config for the smoke test.

    Resolution order:
      1. Explicit env overrides (``SESSION_SMOKE_URL`` / ``SESSION_SMOKE_JSON_PATH``
         / ``SESSION_SMOKE_AUTH``) so the endpoint can be confirmed without
         editing config.json.
      2. Otherwise the ``session_monitor.provider`` block from config.json,
         parsed through the same ``parse_monitor_config`` path the real monitor
         uses.

    Returns a configured ``MonitorConfig`` (provider fields populated) or ``None``
    when no usable provider config is available, in which case the test is
    skipped rather than failed.
    """
    env_url = os.environ.get("SESSION_SMOKE_URL")
    env_json_path = os.environ.get("SESSION_SMOKE_JSON_PATH")
    if env_url and env_json_path:
        headers = {}
        auth = os.environ.get("SESSION_SMOKE_AUTH")
        if auth:
            headers["Authorization"] = auth
        return MonitorConfig(
            provider_url=env_url,
            provider_json_path=env_json_path,
            provider_headers=headers,
        )

    # Fall back to config.json's session_monitor.provider block.
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
    )
    block = sm._load_session_monitor_block(config_path)
    if block is None:
        return None
    config = sm.parse_monitor_config(block)
    if not config.provider_url or not config.provider_json_path:
        return None
    return config


@pytest.mark.skipif(
    not os.environ.get("RUN_SESSION_SMOKE"),
    reason=(
        "Opt-in smoke test: requires the real dashboard session-usage endpoint to "
        "be confirmed AND the 9router proxy running at http://localhost:20128. "
        "Set RUN_SESSION_SMOKE=1 (and optionally SESSION_SMOKE_URL / "
        "SESSION_SMOKE_JSON_PATH / SESSION_SMOKE_AUTH) to run it."
    ),
)
def test_live_provider_returns_parseable_percentage_smoke():
    """Hit the real proxy and assert a parseable usage percentage is returned.

    This confirms the end-to-end wiring (endpoint URL + auth + json_path) against
    a live Router_Proxy. It makes a real network call — no mocking — and is only
    reached when ``RUN_SESSION_SMOKE`` is set.

    Validates: Requirements 2.1.
    """
    config = _load_smoke_provider_config()
    if config is None:
        pytest.skip(
            "No session-usage provider configured: set SESSION_SMOKE_URL + "
            "SESSION_SMOKE_JSON_PATH, or add a session_monitor.provider block "
            "with url/json_path to config.json."
        )

    # Sanity-check we are pointed at the expected proxy host before calling out.
    assert _SMOKE_PROXY_BASE in config.provider_url, (
        f"smoke test expects the provider URL to target {_SMOKE_PROXY_BASE}, "
        f"got {config.provider_url!r}"
    )

    provider = HttpSessionUsageProvider.from_config(config)
    result = provider.get_usage_percentage()

    assert isinstance(result, Ok), (
        "expected a parseable percentage (Ok) from the live endpoint, got "
        f"{result!r}. A RetrievalError/Invalid means the endpoint, auth, or "
        "json_path wiring is not yet confirmed/correct."
    )
    assert 0.0 <= result.value <= 100.0
    print(f"[smoke] live session usage = {result.value}%")
