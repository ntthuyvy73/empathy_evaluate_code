"""Non-invasiveness regression guard (Task 10.2).

The Session Capacity Monitor is an opt-in, non-invasive add-on. The user's
explicit constraint is that the existing evaluation behavior must not change
unless the selected judge is the configured ``target_judge`` (``claude_9router``)
*and* a ``session_monitor`` config block is present. For every other case the
monitor must be a true no-op: ``should_continue`` always returns CONTINUE, no
usage provider is ever consulted, and no HTTP call is ever made.

These tests lock that contract in at the unit level (no real API run):

- A monitor built for a non-target judge is disabled and never touches a spy
  provider, even across many ``should_continue`` calls.
- A monitor built for the target judge but with NO ``session_monitor`` block in
  the config is also disabled.
- ``mindeval.session_monitor.urllib.request.urlopen`` is patched and asserted to
  be NEVER called while the monitor is disabled, regardless of how many times
  ``should_continue`` is invoked.

Validates: Requirements 1.2, 1.3.
"""

import json
from contextlib import contextmanager
from datetime import datetime
from unittest import mock

import pytest

import mindeval.session_monitor as sm
from mindeval.session_monitor import SessionCapacityMonitor


# --- Test helpers -------------------------------------------------------------


class _SpyProvider:
    """A usage provider that records every call.

    A disabled monitor must never invoke a provider, so ``calls`` must stay at
    zero for every non-invasive scenario. The returned value is irrelevant
    because it should never be observed.
    """

    def __init__(self):
        self.calls = 0

    def get_usage_percentage(self):
        self.calls += 1
        return sm.Ok(0.0)


def _write_config(tmp_path, payload: dict) -> str:
    """Write ``payload`` as JSON to a temp config file and return its path."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return str(config_path)


def _config_without_session_monitor(tmp_path) -> str:
    """A realistic config file that deliberately omits ``session_monitor``."""
    return _write_config(
        tmp_path,
        {
            "openai_api_key": "placeholder",
            "models": {"gpt": "gpt-4o"},
        },
    )


# --- Disabled-monitor no-op: never calls the provider -------------------------


def test_non_target_judge_is_disabled_and_never_calls_provider(tmp_path):
    """A non-target judge yields a disabled no-op monitor (Requirement 1.2).

    Note: ``from_config`` only builds its own provider when enabled; a disabled
    monitor must never call any injected provider either. We inject a spy and
    assert zero calls across many ``should_continue`` invocations.
    """
    config_path = _config_without_session_monitor(tmp_path)
    spy = _SpyProvider()

    monitor = SessionCapacityMonitor.from_config("gpt", config_path, provider=spy)

    assert monitor.enabled is False

    for i in range(50):
        decision = monitor.should_continue(completed_count=i, output_path="out.jsonl")
        assert decision.should_continue is True
        assert decision.reason == "disabled"
        assert decision.message is None

    assert spy.calls == 0


def test_target_judge_without_session_monitor_block_is_disabled(tmp_path):
    """Target judge but NO ``session_monitor`` block → still disabled (Requirement 1.2)."""
    config_path = _config_without_session_monitor(tmp_path)
    spy = _SpyProvider()

    monitor = SessionCapacityMonitor.from_config(
        "claude_9router", config_path, provider=spy
    )

    assert monitor.enabled is False

    for i in range(50):
        decision = monitor.should_continue(completed_count=i, output_path="out.jsonl")
        assert decision.should_continue is True
        assert decision.reason == "disabled"

    assert spy.calls == 0


def test_missing_config_path_is_disabled_and_never_calls_provider():
    """No config path at all → disabled no-op, provider never consulted."""
    spy = _SpyProvider()

    monitor = SessionCapacityMonitor.from_config("claude_9router", None, provider=spy)

    assert monitor.enabled is False

    for i in range(25):
        decision = monitor.should_continue(completed_count=i, output_path="out.jsonl")
        assert decision.should_continue is True
        assert decision.reason == "disabled"

    assert spy.calls == 0


# --- No HTTP call is ever made while disabled ---------------------------------


def test_disabled_monitor_makes_no_http_call_non_target_judge(tmp_path):
    """Patch ``urlopen`` and assert it is NEVER called for a non-target judge.

    Even with a fully-specified ``session_monitor`` block present, selecting a
    judge other than the target must keep the monitor disabled and perform no
    network I/O (Requirement 1.2). This guards against any accidental HTTP call
    sneaking into the disabled path.
    """
    config_path = _write_config(
        tmp_path,
        {
            "session_monitor": {
                "target_judge": "claude_9router",
                "threshold_percent": 50,
                "unrestricted_window": {"start_hour": 0, "end_hour": 3},
                "provider": {
                    "url": "http://localhost:20128/api/session",
                    "method": "GET",
                    "headers": {"Authorization": "Bearer token"},
                    "json_path": "usage_percent",
                    "timeout": 10,
                },
            }
        },
    )

    with mock.patch.object(sm.urllib.request, "urlopen") as urlopen:
        monitor = SessionCapacityMonitor.from_config("gpt", config_path)

        assert monitor.enabled is False

        for i in range(100):
            decision = monitor.should_continue(
                completed_count=i, output_path="out.jsonl"
            )
            assert decision.should_continue is True
            assert decision.reason == "disabled"

        urlopen.assert_not_called()


def test_disabled_monitor_makes_no_http_call_without_config_block(tmp_path):
    """Patch ``urlopen`` and assert no network call when the config omits the block."""
    config_path = _config_without_session_monitor(tmp_path)

    with mock.patch.object(sm.urllib.request, "urlopen") as urlopen:
        monitor = SessionCapacityMonitor.from_config("claude_9router", config_path)

        assert monitor.enabled is False

        for i in range(100):
            decision = monitor.should_continue(
                completed_count=i, output_path="out.jsonl"
            )
            assert decision.should_continue is True

        urlopen.assert_not_called()


def test_constructing_monitor_for_non_target_judge_makes_zero_network_calls(tmp_path):
    """Focused check: merely building + probing a disabled monitor is network-silent.

    Covers the constructor path as well as ``should_continue`` to ensure the
    non-invasive contract holds end-to-end for a non-target judge.
    """
    config_path = _config_without_session_monitor(tmp_path)

    with mock.patch.object(sm.urllib.request, "urlopen") as urlopen:
        for judge in ("gpt", "claude", "gemini", "qwen", "gpt_9router"):
            monitor = SessionCapacityMonitor.from_config(judge, config_path)
            assert monitor.enabled is False
            decision = monitor.should_continue(completed_count=0, output_path="o.jsonl")
            assert decision.should_continue is True
            assert decision.reason == "disabled"

        urlopen.assert_not_called()


# --- Disabled stays a no-op across every hour of the day ----------------------


@contextmanager
def _freeze_hour(hour: int):
    """Freeze ``mindeval.session_monitor``'s clock at a fixed hour-of-day.

    The module imports ``datetime`` via ``from datetime import datetime``, so the
    name to patch is ``mindeval.session_monitor.datetime``. We freeze ``now()`` at
    the requested hour so we can sweep across both the unrestricted window
    (hours 0-2 by default) and the restricted window (hours 3-23) and prove the
    disabled path takes neither branch.
    """
    frozen = datetime(2024, 1, 1, hour, 30, 0)
    with mock.patch.object(sm, "datetime", wraps=datetime) as dt:
        dt.now.return_value = frozen
        yield dt


def test_disabled_monitor_is_noop_across_all_hours_no_http_no_provider(tmp_path):
    """Sweep every hour (restricted + unrestricted) and assert a true no-op.

    With a fully-specified ``session_monitor`` block but a non-target judge, the
    monitor must stay disabled regardless of the wall clock: it must never read
    usage from the spy provider and never make an HTTP call, whether the frozen
    time falls inside or outside the unrestricted window (Requirements 1.2, 1.3).
    """
    config_path = _write_config(
        tmp_path,
        {
            "session_monitor": {
                "target_judge": "claude_9router",
                "threshold_percent": 50,
                "unrestricted_window": {"start_hour": 0, "end_hour": 3},
                "provider": {
                    "url": "http://localhost:20128/api/session",
                    "method": "GET",
                    "headers": {"Authorization": "Bearer token"},
                    "json_path": "usage_percent",
                    "timeout": 10,
                },
            }
        },
    )
    spy = _SpyProvider()

    with mock.patch.object(sm.urllib.request, "urlopen") as urlopen:
        monitor = SessionCapacityMonitor.from_config("gpt", config_path, provider=spy)
        assert monitor.enabled is False

        # 24 hours x ~2 iterations each → well over 50 should_continue calls that
        # span both the restricted and unrestricted windows.
        for hour in range(24):
            with _freeze_hour(hour):
                for i in range(2):
                    decision = monitor.should_continue(
                        completed_count=i, output_path="out.jsonl"
                    )
                    assert decision.should_continue is True
                    assert decision.reason == "disabled"
                    assert decision.message is None

        urlopen.assert_not_called()

    assert spy.calls == 0
