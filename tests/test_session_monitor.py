"""Tests for ``mindeval.session_monitor``.

Task 1.1 establishes the foundational data models. These tests verify the
module imports cleanly and that the data models carry the documented fields,
defaults, and behavior. Later tasks add property-based tests (Hypothesis) for
the pure decision core and helpers to this suite.
"""

import math
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mindeval.session_monitor import (
    CapacityDecision,
    Invalid,
    MonitorConfig,
    Ok,
    RetrievalError,
    evaluate_capacity,
    in_unrestricted_window,
    validate_usage,
)


def test_monitor_config_defaults():
    cfg = MonitorConfig()
    assert cfg.target_judge == "claude_9router"
    assert cfg.threshold_percent == 50.0
    assert cfg.unrestricted_start_hour == 0
    assert cfg.unrestricted_end_hour == 3
    assert cfg.provider_url is None
    assert cfg.provider_method == "GET"
    assert cfg.provider_headers == {}
    assert cfg.provider_json_path is None
    assert cfg.provider_timeout == 10.0


def test_monitor_config_is_frozen():
    cfg = MonitorConfig()
    with pytest.raises(FrozenInstanceError):
        cfg.threshold_percent = 75.0  # type: ignore[misc]


def test_monitor_config_headers_default_factory_is_independent():
    a = MonitorConfig()
    b = MonitorConfig()
    # Each instance must get its own dict, not a shared mutable default.
    assert a.provider_headers is not b.provider_headers


def test_monitor_config_overrides():
    cfg = MonitorConfig(
        target_judge="gpt_9router",
        threshold_percent=80.0,
        unrestricted_start_hour=1,
        unrestricted_end_hour=4,
        provider_url="http://localhost:20128/api/session",
        provider_method="POST",
        provider_headers={"Authorization": "Bearer token"},
        provider_json_path="data.usage_percent",
        provider_timeout=5.0,
    )
    assert cfg.target_judge == "gpt_9router"
    assert cfg.threshold_percent == 80.0
    assert cfg.unrestricted_start_hour == 1
    assert cfg.unrestricted_end_hour == 4
    assert cfg.provider_url == "http://localhost:20128/api/session"
    assert cfg.provider_method == "POST"
    assert cfg.provider_headers == {"Authorization": "Bearer token"}
    assert cfg.provider_json_path == "data.usage_percent"
    assert cfg.provider_timeout == 5.0


def test_usage_result_variants_carry_payloads():
    ok = Ok(42.0)
    invalid = Invalid("not-a-number")
    err = RetrievalError("timeout")
    assert ok.value == 42.0
    assert invalid.raw == "not-a-number"
    assert err.detail == "timeout"


def test_usage_result_variants_are_frozen():
    ok = Ok(10.0)
    with pytest.raises(FrozenInstanceError):
        ok.value = 20.0  # type: ignore[misc]


def test_capacity_decision_fields():
    decision = CapacityDecision(
        should_continue=False,
        reason="at_or_above_threshold",
        usage_percentage=55.0,
        message="stopping",
    )
    assert decision.should_continue is False
    assert decision.reason == "at_or_above_threshold"
    assert decision.usage_percentage == 55.0
    assert decision.message == "stopping"
    # NamedTuple positional/tuple semantics.
    assert tuple(decision) == (False, "at_or_above_threshold", 55.0, "stopping")


def test_capacity_decision_allows_optional_none():
    decision = CapacityDecision(
        should_continue=True,
        reason="disabled",
        usage_percentage=None,
        message=None,
    )
    assert decision.should_continue is True
    assert decision.usage_percentage is None
    assert decision.message is None


# --- validate_usage (Task 2.1) ------------------------------------------------


@pytest.mark.parametrize("value", [0, 0.0, 1, 50, 99.9, 100, 100.0])
def test_validate_usage_accepts_in_range_numbers(value):
    result = validate_usage(value)
    assert isinstance(result, Ok)
    assert result.value == float(value)


def test_validate_usage_accepts_boundaries():
    assert validate_usage(0) == Ok(0.0)
    assert validate_usage(100) == Ok(100.0)


@pytest.mark.parametrize("raw", ["0", "50", " 99.5 ", "100"])
def test_validate_usage_accepts_numeric_strings(raw):
    result = validate_usage(raw)
    assert isinstance(result, Ok)


@pytest.mark.parametrize("value", [-0.1, -1, 100.1, 101, 1000])
def test_validate_usage_rejects_out_of_range(value):
    result = validate_usage(value)
    assert isinstance(result, Invalid)
    assert result.raw == value


@pytest.mark.parametrize("raw", ["abc", "", None, [], {}, "12.3.4"])
def test_validate_usage_rejects_unparseable(raw):
    result = validate_usage(raw)
    assert isinstance(result, Invalid)
    assert result.raw == raw


@pytest.mark.parametrize("raw", [float("nan"), float("inf"), float("-inf")])
def test_validate_usage_rejects_non_finite(raw):
    result = validate_usage(raw)
    assert isinstance(result, Invalid)


@pytest.mark.parametrize("raw", [True, False])
def test_validate_usage_rejects_booleans(raw):
    result = validate_usage(raw)
    assert isinstance(result, Invalid)
    assert result.raw is raw


def test_validate_usage_preserves_raw_in_invalid():
    result = validate_usage("not-a-number")
    assert isinstance(result, Invalid)
    assert result.raw == "not-a-number"


# --- in_unrestricted_window (Task 2.3) ----------------------------------------


def _at_hour(hour: int) -> datetime:
    """Helper: a datetime at the given hour-of-day (minutes/seconds vary)."""
    return datetime(2024, 1, 1, hour, 30, 15)


@pytest.mark.parametrize("hour", [0, 1, 2])
def test_default_window_includes_start_inclusive_hours(hour):
    # Default window is 00:00 inclusive .. 03:00 exclusive.
    assert in_unrestricted_window(_at_hour(hour), MonitorConfig()) is True


@pytest.mark.parametrize("hour", [3, 4, 9, 12, 17, 23])
def test_default_window_excludes_end_exclusive_and_later_hours(hour):
    # Hour 3 is the exclusive end and must be outside the window.
    assert in_unrestricted_window(_at_hour(hour), MonitorConfig()) is False


def test_start_hour_is_inclusive():
    cfg = MonitorConfig(unrestricted_start_hour=2, unrestricted_end_hour=5)
    assert in_unrestricted_window(_at_hour(2), cfg) is True


def test_end_hour_is_exclusive():
    cfg = MonitorConfig(unrestricted_start_hour=2, unrestricted_end_hour=5)
    assert in_unrestricted_window(_at_hour(5), cfg) is False


def test_hour_just_before_end_is_inside():
    cfg = MonitorConfig(unrestricted_start_hour=2, unrestricted_end_hour=5)
    assert in_unrestricted_window(_at_hour(4), cfg) is True


def test_minutes_and_seconds_are_ignored():
    cfg = MonitorConfig()  # 00:00 .. 03:00
    # 02:59:59 is still hour 2 -> inside; 03:00:00 is hour 3 -> outside.
    assert in_unrestricted_window(datetime(2024, 1, 1, 2, 59, 59), cfg) is True
    assert in_unrestricted_window(datetime(2024, 1, 1, 3, 0, 0), cfg) is False


@pytest.mark.parametrize("hour", [22, 23, 0, 1, 2])
def test_wraparound_window_includes_hours_across_midnight(hour):
    cfg = MonitorConfig(unrestricted_start_hour=22, unrestricted_end_hour=3)
    assert in_unrestricted_window(_at_hour(hour), cfg) is True


@pytest.mark.parametrize("hour", [3, 4, 12, 21])
def test_wraparound_window_excludes_daytime_hours(hour):
    cfg = MonitorConfig(unrestricted_start_hour=22, unrestricted_end_hour=3)
    assert in_unrestricted_window(_at_hour(hour), cfg) is False


@pytest.mark.parametrize("hour", range(24))
def test_empty_window_is_never_unrestricted(hour):
    cfg = MonitorConfig(unrestricted_start_hour=5, unrestricted_end_hour=5)
    assert in_unrestricted_window(_at_hour(hour), cfg) is False


# --- evaluate_capacity (Task 3.1) ---------------------------------------------
#
# Decision core unit tests. The default MonitorConfig uses an unrestricted
# window of 00:00..03:00 and a 50% threshold, so hour 12 is restricted and
# hour 1 is unrestricted.


def _restricted_now() -> datetime:
    # Hour 12 is well outside the default 00:00..03:00 unrestricted window.
    return datetime(2024, 1, 1, 12, 0, 0)


def _unrestricted_now() -> datetime:
    # Hour 1 is inside the default 00:00..03:00 unrestricted window.
    return datetime(2024, 1, 1, 1, 0, 0)


@pytest.mark.parametrize(
    "usage",
    [Ok(0.0), Ok(50.0), Ok(100.0), Invalid("bad"), RetrievalError("down")],
)
def test_evaluate_capacity_unrestricted_always_continues(usage):
    # In the unrestricted window the run always continues regardless of usage,
    # and the usage is never reflected in the decision.
    decision = evaluate_capacity(now=_unrestricted_now(), config=MonitorConfig(), usage=usage)
    assert decision.should_continue is True
    assert decision.reason == "unrestricted_window"
    assert decision.usage_percentage is None


def test_evaluate_capacity_restricted_below_threshold_continues():
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=Ok(49.9)
    )
    assert decision.should_continue is True
    assert decision.reason == "below_threshold"
    assert decision.usage_percentage == 49.9


def test_evaluate_capacity_restricted_at_threshold_stops():
    # v == threshold must stop (>= threshold).
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=Ok(50.0)
    )
    assert decision.should_continue is False
    assert decision.reason == "at_or_above_threshold"
    assert decision.usage_percentage == 50.0


def test_evaluate_capacity_restricted_above_threshold_stops():
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=Ok(75.0)
    )
    assert decision.should_continue is False
    assert decision.reason == "at_or_above_threshold"
    assert decision.usage_percentage == 75.0


def test_evaluate_capacity_restricted_retrieval_error_stops():
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=RetrievalError("timeout")
    )
    assert decision.should_continue is False
    assert decision.reason == "retrieval_error_restricted"
    assert decision.usage_percentage is None


def test_evaluate_capacity_restricted_invalid_value_stops():
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=Invalid(150)
    )
    assert decision.should_continue is False
    assert decision.reason == "invalid_value_restricted"
    assert decision.usage_percentage is None


def test_evaluate_capacity_honors_custom_threshold():
    cfg = MonitorConfig(threshold_percent=80.0)
    # 75 is below the custom 80% threshold -> continue.
    cont = evaluate_capacity(now=_restricted_now(), config=cfg, usage=Ok(75.0))
    assert cont.should_continue is True
    assert cont.reason == "below_threshold"
    # 80 is at the custom threshold -> stop.
    stop = evaluate_capacity(now=_restricted_now(), config=cfg, usage=Ok(80.0))
    assert stop.should_continue is False
    assert stop.reason == "at_or_above_threshold"


def test_evaluate_capacity_message_is_none():
    # Message formatting is deferred to the monitor (Task 4.3).
    decision = evaluate_capacity(
        now=_restricted_now(), config=MonitorConfig(), usage=Ok(90.0)
    )
    assert decision.message is None


# --- Property-based test (Task 2.2) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 4
# Property 4: Usage value range validation
# Validates: Requirements 2.2, 2.3
#
# For any retrieved numeric value v, validate_usage classifies it as Ok(v) iff
# 0 <= v <= 100 (inclusive), and classifies every other value (out of range or
# unparseable) as Invalid.


def _is_in_range_number(raw: object) -> bool:
    """Reference oracle: True iff ``raw`` parses to a finite number in [0, 100].

    Mirrors the documented contract of ``validate_usage`` (booleans are never
    valid usage values even though ``bool`` is an ``int`` subclass).
    """
    if isinstance(raw, bool):
        return False
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if math.isnan(value) or math.isinf(value):
        return False
    return 0.0 <= value <= 100.0


# A strategy spanning the whole input space the validator must classify:
# in-range / out-of-range floats and ints (with 0 and 100 boundaries forced in),
# non-finite floats, numeric and non-numeric strings, and non-numeric objects.
_usage_inputs = st.one_of(
    st.floats(min_value=0.0, max_value=100.0),                       # in range
    st.sampled_from([0, 0.0, 100, 100.0, -0.0, 50, 99.999999]),      # boundaries
    st.floats(min_value=100.0001, max_value=1e9),                    # above range
    st.floats(min_value=-1e9, max_value=-0.0001),                    # below range
    st.integers(min_value=-1000, max_value=1000),                    # ints either side
    st.floats(allow_nan=True, allow_infinity=True),                  # incl. NaN/inf
    st.text(),                                                       # arbitrary strings
    st.sampled_from(["0", "50", "100", " 99.5 ", "abc", "", "12.3.4"]),  # numeric/garbage strings
    st.none(),
    st.booleans(),                                                   # bools -> Invalid
    st.lists(st.integers()),
    st.dictionaries(st.text(), st.integers()),
)


@settings(max_examples=200)
@given(raw=_usage_inputs)
def test_property4_usage_value_range_validation(raw):
    result = validate_usage(raw)

    if _is_in_range_number(raw):
        # Must be Ok and carry the parsed numeric value.
        assert isinstance(result, Ok), f"expected Ok for {raw!r}, got {result!r}"
        assert result.value == float(raw)
    else:
        # Out of range or unparseable -> Invalid, preserving the raw value.
        assert isinstance(result, Invalid), f"expected Invalid for {raw!r}, got {result!r}"
        assert result.raw is raw or result.raw == raw


# --- Config parsing + factory (Task 4.1) --------------------------------------

import json

from mindeval.session_monitor import (
    SessionCapacityMonitor,
    parse_monitor_config,
)


def _write_config(tmp_path, data) -> str:
    """Write ``data`` (or raw text) to a config.json under ``tmp_path``."""
    path = tmp_path / "config.json"
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class _SpyProvider:
    """A usage provider stand-in that records whether it was ever called."""

    def __init__(self):
        self.calls = 0

    def get_usage_percentage(self):
        self.calls += 1
        return Ok(10.0)


# parse_monitor_config -----------------------------------------------------


def test_parse_monitor_config_none_block_yields_defaults():
    cfg = parse_monitor_config(None)
    assert cfg == MonitorConfig()


def test_parse_monitor_config_empty_block_yields_defaults():
    cfg = parse_monitor_config({})
    assert cfg.target_judge == "claude_9router"
    assert cfg.threshold_percent == 50.0
    assert cfg.unrestricted_start_hour == 0
    assert cfg.unrestricted_end_hour == 3
    assert cfg.provider_url is None
    assert cfg.provider_method == "GET"
    assert cfg.provider_headers == {}
    assert cfg.provider_json_path is None
    assert cfg.provider_timeout == 10.0


def test_parse_monitor_config_full_block_maps_all_keys():
    block = {
        "target_judge": "claude_9router",
        "threshold_percent": 75,
        "unrestricted_window": {"start_hour": 1, "end_hour": 4},
        "provider": {
            "url": "http://localhost:20128/api/session",
            "method": "POST",
            "headers": {"Authorization": "Bearer token"},
            "json_path": "data.usage_percent",
            "timeout": 5,
        },
    }
    cfg = parse_monitor_config(block)
    assert cfg.target_judge == "claude_9router"
    assert cfg.threshold_percent == 75.0
    assert cfg.unrestricted_start_hour == 1
    assert cfg.unrestricted_end_hour == 4
    assert cfg.provider_url == "http://localhost:20128/api/session"
    assert cfg.provider_method == "POST"
    assert cfg.provider_headers == {"Authorization": "Bearer token"}
    assert cfg.provider_json_path == "data.usage_percent"
    assert cfg.provider_timeout == 5.0


def test_parse_monitor_config_partial_block_applies_defaults_for_missing():
    block = {"threshold_percent": 30}
    cfg = parse_monitor_config(block)
    assert cfg.threshold_percent == 30.0
    # Everything else falls back to defaults.
    assert cfg.unrestricted_start_hour == 0
    assert cfg.unrestricted_end_hour == 3
    assert cfg.provider_url is None


def test_parse_monitor_config_malformed_values_fall_back_to_defaults():
    block = {
        "target_judge": 123,  # wrong type
        "threshold_percent": "not-a-number",
        "unrestricted_window": "nope",  # wrong type for the whole sub-block
        "provider": {"timeout": "abc", "headers": ["not", "a", "dict"]},
    }
    cfg = parse_monitor_config(block)
    assert cfg.target_judge == "claude_9router"
    assert cfg.threshold_percent == 50.0
    assert cfg.unrestricted_start_hour == 0
    assert cfg.unrestricted_end_hour == 3
    assert cfg.provider_timeout == 10.0
    assert cfg.provider_headers == {}


def test_parse_monitor_config_numeric_strings_are_coerced():
    block = {
        "threshold_percent": "60",
        "unrestricted_window": {"start_hour": "2", "end_hour": "5"},
        "provider": {"timeout": "7.5"},
    }
    cfg = parse_monitor_config(block)
    assert cfg.threshold_percent == 60.0
    assert cfg.unrestricted_start_hour == 2
    assert cfg.unrestricted_end_hour == 5
    assert cfg.provider_timeout == 7.5


# from_config: activation scope -------------------------------------------


def test_from_config_enabled_for_target_judge_with_block(tmp_path):
    path = _write_config(tmp_path, {"session_monitor": {"target_judge": "claude_9router"}})
    monitor = SessionCapacityMonitor.from_config("claude_9router", path)
    assert monitor.enabled is True


def test_from_config_disabled_for_non_target_judge(tmp_path):
    path = _write_config(tmp_path, {"session_monitor": {"target_judge": "claude_9router"}})
    monitor = SessionCapacityMonitor.from_config("gpt", path)
    assert monitor.enabled is False


def test_from_config_disabled_when_block_absent(tmp_path):
    # File exists with no session_monitor block -> disabled even for the target judge.
    path = _write_config(tmp_path, {"judges": {}})
    monitor = SessionCapacityMonitor.from_config("claude_9router", path)
    assert monitor.enabled is False


def test_from_config_respects_custom_target_judge(tmp_path):
    path = _write_config(tmp_path, {"session_monitor": {"target_judge": "gpt_9router"}})
    enabled = SessionCapacityMonitor.from_config("gpt_9router", path)
    disabled = SessionCapacityMonitor.from_config("claude_9router", path)
    assert enabled.enabled is True
    assert disabled.enabled is False


def test_from_config_disabled_when_judge_name_none(tmp_path):
    path = _write_config(tmp_path, {"session_monitor": {"target_judge": "claude_9router"}})
    monitor = SessionCapacityMonitor.from_config(None, path)
    assert monitor.enabled is False


def test_from_config_disabled_when_config_path_none():
    monitor = SessionCapacityMonitor.from_config("claude_9router", None)
    assert monitor.enabled is False


def test_from_config_missing_file_is_disabled_with_defaults(tmp_path):
    missing = str(tmp_path / "does_not_exist.json")
    monitor = SessionCapacityMonitor.from_config("claude_9router", missing)
    assert monitor.enabled is False
    assert monitor.config == MonitorConfig()


def test_from_config_malformed_json_is_disabled_with_defaults(tmp_path):
    path = _write_config(tmp_path, "{ this is : not valid json ")
    monitor = SessionCapacityMonitor.from_config("claude_9router", path)
    # Unparseable config -> treated as no block -> disabled, defaults applied.
    assert monitor.enabled is False
    assert monitor.config == MonitorConfig()


def test_from_config_malformed_block_uses_defaults_but_still_enables(tmp_path):
    # Block is present (so enablement is possible) but its values are malformed;
    # defaults are applied and, since the default target matches, it is enabled.
    path = _write_config(
        tmp_path,
        {"session_monitor": {"threshold_percent": "bad", "target_judge": 999}},
    )
    monitor = SessionCapacityMonitor.from_config("claude_9router", path)
    assert monitor.enabled is True
    assert monitor.config.threshold_percent == 50.0
    assert monitor.config.target_judge == "claude_9router"


def test_from_config_parses_provider_block(tmp_path):
    path = _write_config(
        tmp_path,
        {
            "session_monitor": {
                "threshold_percent": 65,
                "unrestricted_window": {"start_hour": 0, "end_hour": 6},
                "provider": {
                    "url": "http://localhost:20128/api/session",
                    "json_path": "usage_percent",
                    "timeout": 8,
                },
            }
        },
    )
    monitor = SessionCapacityMonitor.from_config("claude_9router", path)
    assert monitor.enabled is True
    assert monitor.config.threshold_percent == 65.0
    assert monitor.config.unrestricted_end_hour == 6
    assert monitor.config.provider_url == "http://localhost:20128/api/session"
    assert monitor.config.provider_json_path == "usage_percent"
    assert monitor.config.provider_timeout == 8.0


# should_continue: disabled no-op -----------------------------------------


def test_disabled_monitor_should_continue_returns_continue():
    monitor = SessionCapacityMonitor(config=MonitorConfig(), enabled=False)
    decision = monitor.should_continue(completed_count=5, output_path="out.jsonl")
    assert decision.should_continue is True
    assert decision.reason == "disabled"
    assert decision.usage_percentage is None
    assert decision.message is None


def test_disabled_monitor_never_calls_provider():
    spy = _SpyProvider()
    monitor = SessionCapacityMonitor(config=MonitorConfig(), enabled=False, provider=spy)
    monitor.should_continue(completed_count=0, output_path="out.jsonl")
    assert spy.calls == 0


def test_from_config_accepts_injected_provider(tmp_path):
    path = _write_config(tmp_path, {"session_monitor": {"target_judge": "claude_9router"}})
    spy = _SpyProvider()
    monitor = SessionCapacityMonitor.from_config("claude_9router", path, provider=spy)
    assert monitor.enabled is True
    # Provider injection is wired but should not be invoked by construction.
    assert spy.calls == 0


# --- Property-based test (Task 3.2) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 2
# Property 2: Unrestricted window always continues without retrieval
# Validates: Requirements 3.1, 3.2, 6.2, 8.2
#
# For any configured unrestricted window [start_hour, end_hour), for any local
# time inside that window, and for any UsageResult (Ok, Invalid, or
# RetrievalError), evaluate_capacity returns CONTINUE with reason
# "unrestricted_window" and does not reflect the usage value in the decision.
# Because evaluate_capacity is pure and never calls a provider, "provider not
# invoked" is satisfied structurally; we assert the decision is CONTINUE and
# that the usage was not reflected (usage_percentage is None).


def _hours_inside_window(start: int, end: int) -> list[int]:
    """Return the hours-of-day that fall inside the half-open window [start, end).

    Mirrors ``in_unrestricted_window``: a non-wrapping window (start < end) spans
    ``range(start, end)``; a wrap-around window (start > end) spans
    ``range(start, 24)`` plus ``range(0, end)``. An empty window (start == end)
    has no inside hours.
    """
    if start == end:
        return []
    if start < end:
        return list(range(start, end))
    return list(range(start, 24)) + list(range(0, end))


# A UsageResult strategy yielding all three variants with arbitrary payloads,
# including the in-range/out-of-range/non-numeric cases the window logic must
# ignore entirely.
_usage_results = st.one_of(
    st.builds(Ok, st.floats(min_value=0.0, max_value=100.0)),
    st.builds(Ok, st.sampled_from([0.0, 50.0, 100.0])),
    st.builds(Invalid, st.one_of(st.text(), st.integers(), st.none(), st.floats(allow_nan=True))),
    st.builds(RetrievalError, st.text()),
)


@st.composite
def _window_and_inside_time(draw):
    """Draw a (config, datetime-inside-window) pair.

    The window is any non-empty interval over hours 0..23 (covering both
    non-wrapping and wrap-around windows); the time is pinned to an hour that is
    inside that window, with arbitrary minutes/seconds to confirm they are
    ignored.
    """
    start = draw(st.integers(min_value=0, max_value=23))
    end = draw(st.integers(min_value=0, max_value=23).filter(lambda e: e != start))
    inside_hours = _hours_inside_window(start, end)
    hour = draw(st.sampled_from(inside_hours))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    threshold = draw(st.floats(min_value=0.0, max_value=100.0))
    config = MonitorConfig(
        unrestricted_start_hour=start,
        unrestricted_end_hour=end,
        threshold_percent=threshold,
    )
    now = datetime(2024, 1, 1, hour, minute, second)
    return config, now


@settings(max_examples=100)
@given(window_time=_window_and_inside_time(), usage=_usage_results)
def test_property2_unrestricted_window_always_continues(window_time, usage):
    config, now = window_time

    # Sanity: the generated time really is inside the configured window.
    assert in_unrestricted_window(now, config) is True

    decision = evaluate_capacity(now=now, config=config, usage=usage)

    # CONTINUE in all cases, regardless of the usage variant or value.
    assert decision.should_continue is True
    assert decision.reason == "unrestricted_window"
    # Usage was not reflected in the decision (provider result ignored).
    assert decision.usage_percentage is None
    assert decision.message is None


# --- should_continue: enabled path (Task 4.3) ---------------------------------
#
# The enabled monitor reads datetime.now() internally, so these tests freeze the
# module clock to land deterministically inside or outside the default
# 00:00..03:00 unrestricted window. A configurable fake provider stands in for
# the (unconfirmed) HTTP usage provider and records its call count so we can
# assert the unrestricted window skips retrieval (Requirement 3.2) and the
# restricted window queries exactly once (Requirement 2.1).


class _FixedClock:
    """Stands in for the module-level ``datetime`` so ``now()`` is deterministic."""

    def __init__(self, fixed: datetime):
        self._fixed = fixed

    def now(self):
        return self._fixed


class _FakeProvider:
    """A usage provider whose return value is configurable; counts invocations."""

    def __init__(self, result):
        self._result = result
        self.calls = 0

    def get_usage_percentage(self):
        self.calls += 1
        return self._result


def _freeze_now(monkeypatch, hour: int) -> None:
    """Freeze ``session_monitor.datetime.now()`` to a fixed hour-of-day."""
    import mindeval.session_monitor as sm

    monkeypatch.setattr(sm, "datetime", _FixedClock(datetime(2024, 1, 1, hour, 30, 0)))


def _enabled_monitor(provider=None, config=None) -> SessionCapacityMonitor:
    return SessionCapacityMonitor(
        config=config or MonitorConfig(),
        enabled=True,
        provider=provider,
    )


def test_should_continue_unrestricted_skips_retrieval(monkeypatch):
    _freeze_now(monkeypatch, hour=1)  # inside default 00:00..03:00 window
    spy = _FakeProvider(Ok(99.0))
    monitor = _enabled_monitor(provider=spy)

    decision = monitor.should_continue(completed_count=7, output_path="out.jsonl")

    assert decision.should_continue is True
    assert decision.reason == "unrestricted_window"
    assert decision.message is None
    # Retrieval is skipped entirely in the unrestricted window.
    assert spy.calls == 0


def test_should_continue_restricted_below_threshold_continues(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    spy = _FakeProvider(Ok(10.0))
    monitor = _enabled_monitor(provider=spy)

    decision = monitor.should_continue(completed_count=3, output_path="out.jsonl")

    assert decision.should_continue is True
    assert decision.reason == "below_threshold"
    assert decision.usage_percentage == 10.0
    assert decision.message is None
    # Provider queried exactly once before the batch.
    assert spy.calls == 1


def test_should_continue_restricted_at_or_above_threshold_stops_with_message(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    spy = _FakeProvider(Ok(80.0))
    monitor = _enabled_monitor(provider=spy)  # default threshold 50

    decision = monitor.should_continue(completed_count=42, output_path="results/out.jsonl")

    assert decision.should_continue is False
    assert decision.reason == "at_or_above_threshold"
    assert decision.usage_percentage == 80.0
    assert spy.calls == 1
    # Requirement 7.1: usage percentage AND threshold present.
    assert "80.0" in decision.message
    assert "50.0" in decision.message
    # Requirement 7.2: completed count AND output path present.
    assert "42" in decision.message
    assert "results/out.jsonl" in decision.message


def test_should_continue_restricted_retrieval_error_stops_with_message(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    spy = _FakeProvider(RetrievalError("connection refused"))
    monitor = _enabled_monitor(provider=spy)

    decision = monitor.should_continue(completed_count=5, output_path="out.jsonl")

    assert decision.should_continue is False
    assert decision.reason == "retrieval_error_restricted"
    assert spy.calls == 1
    # Requirement 7.2: completed count and output path present; failure noted.
    assert "5" in decision.message
    assert "out.jsonl" in decision.message
    assert "retriev" in decision.message.lower()


def test_should_continue_restricted_invalid_value_stops_with_message(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    spy = _FakeProvider(Invalid(150))
    monitor = _enabled_monitor(provider=spy)

    decision = monitor.should_continue(completed_count=9, output_path="out.jsonl")

    assert decision.should_continue is False
    assert decision.reason == "invalid_value_restricted"
    assert spy.calls == 1
    assert "9" in decision.message
    assert "out.jsonl" in decision.message
    assert "invalid" in decision.message.lower()


def test_should_continue_restricted_no_provider_fails_safe(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    monitor = _enabled_monitor(provider=None)

    decision = monitor.should_continue(completed_count=0, output_path="out.jsonl")

    # No provider configured -> treated as retrieval error -> graceful stop.
    assert decision.should_continue is False
    assert decision.reason == "retrieval_error_restricted"
    assert decision.message is not None
    assert "out.jsonl" in decision.message


def test_should_continue_unrestricted_no_provider_continues(monkeypatch):
    _freeze_now(monkeypatch, hour=1)  # unrestricted
    monitor = _enabled_monitor(provider=None)

    decision = monitor.should_continue(completed_count=0, output_path="out.jsonl")

    # Unrestricted window never retrieves, so a missing provider is irrelevant.
    assert decision.should_continue is True
    assert decision.reason == "unrestricted_window"


def test_should_continue_honors_custom_threshold_in_message(monkeypatch):
    _freeze_now(monkeypatch, hour=12)  # restricted
    cfg = MonitorConfig(threshold_percent=65.0)
    spy = _FakeProvider(Ok(65.0))
    monitor = _enabled_monitor(provider=spy, config=cfg)

    decision = monitor.should_continue(completed_count=1, output_path="out.jsonl")

    assert decision.should_continue is False
    assert decision.reason == "at_or_above_threshold"
    assert "65.0" in decision.message


# --- Property-based test (Task 3.3) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 3
# Property 3: Restricted-window threshold boundary
# Validates: Requirements 4.1, 4.2, 8.1
#
# For any configured threshold T, for any local time OUTSIDE the unrestricted
# window, and for any validly retrieved usage value v (Ok(v)), the decision is
# CONTINUE if and only if v < T (equivalently, the run stops exactly when
# v >= T). The generators deliberately include v exactly at T, 0, and 100.


def _hours_outside_window(start: int, end: int) -> list[int]:
    """Return the hours-of-day that fall OUTSIDE the half-open window [start, end).

    The complement (within 0..23) of :func:`_hours_inside_window`. For an empty
    window (start == end) every hour is outside.
    """
    inside = set(_hours_inside_window(start, end))
    return [h for h in range(24) if h not in inside]


@st.composite
def _restricted_case(draw):
    """Draw a (config, datetime-outside-window, usage_value) triple.

    The window is any interval over hours 0..23 (non-wrapping, wrap-around, or
    empty); the time is pinned to an hour guaranteed to be outside that window;
    the threshold T and usage value v are arbitrary in [0, 100] with the
    boundaries 0 and 100 forced in and v == T exercised explicitly.
    """
    start = draw(st.integers(min_value=0, max_value=23))
    end = draw(st.integers(min_value=0, max_value=23))
    outside_hours = _hours_outside_window(start, end)
    # outside_hours is always non-empty unless the window covers all 24 hours,
    # which a half-open [start, end) interval can never do, so this is safe.
    hour = draw(st.sampled_from(outside_hours))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))

    threshold = draw(st.floats(min_value=0.0, max_value=100.0))

    # Usage value v in [0, 100], deliberately including 0, 100, the threshold
    # itself, and values straddling the threshold boundary.
    value = draw(
        st.one_of(
            st.floats(min_value=0.0, max_value=100.0),
            st.sampled_from([0.0, 100.0, threshold]),
            st.sampled_from(
                [v for v in (threshold - 0.001, threshold + 0.001) if 0.0 <= v <= 100.0]
            ),
        )
    )

    config = MonitorConfig(
        unrestricted_start_hour=start,
        unrestricted_end_hour=end,
        threshold_percent=threshold,
    )
    now = datetime(2024, 1, 1, hour, minute, second)
    return config, now, value


@settings(max_examples=100)
@given(case=_restricted_case())
def test_property3_restricted_window_threshold_boundary(case):
    config, now, value = case

    # Sanity: the generated time really is outside the configured window.
    assert in_unrestricted_window(now, config) is False

    decision = evaluate_capacity(now=now, config=config, usage=Ok(value))

    # CONTINUE iff v < T; STOP iff v >= T.
    expected_continue = value < config.threshold_percent
    assert decision.should_continue is expected_continue
    assert decision.usage_percentage == value
    if expected_continue:
        assert decision.reason == "below_threshold"
    else:
        assert decision.reason == "at_or_above_threshold"


# --- Property-based test (Task 3.4) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 5
# Property 5: Restricted-window fail-safe stop on abnormal usage
# Validates: Requirements 6.1, 2.3
#
# For any local time OUTSIDE the unrestricted window, if the usage result is a
# RetrievalError or an Invalid value, the decision is STOP (should_continue is
# False) and the decision's reason identifies the retrieval/validation failure
# (one of "retrieval_error_restricted" or "invalid_value_restricted"). This is
# the fail-safe behavior: a monitoring failure during working hours must never
# silently consume the shared session.


# Abnormal usage results the restricted window must fail safe on: RetrievalError
# and Invalid, each with arbitrary payloads. Ok is intentionally excluded — it
# is covered by Property 3 (threshold boundary).
_abnormal_usage_results = st.one_of(
    st.builds(RetrievalError, st.text()),
    st.builds(
        Invalid,
        st.one_of(
            st.text(),
            st.integers(),
            st.floats(allow_nan=True, allow_infinity=True),
            st.none(),
            st.sampled_from([-1, 100.1, 101, 1000, "abc", "", "12.3.4"]),
            st.lists(st.integers()),
            st.dictionaries(st.text(), st.integers()),
        ),
    ),
)


@st.composite
def _restricted_abnormal_case(draw):
    """Draw a (config, datetime-outside-window, abnormal-usage) triple.

    The window is any interval over hours 0..23 (non-wrapping, wrap-around, or
    empty); the time is pinned to an hour guaranteed to be OUTSIDE that window;
    the threshold is arbitrary in [0, 100]; the usage is a RetrievalError or an
    Invalid carrying an arbitrary payload.
    """
    start = draw(st.integers(min_value=0, max_value=23))
    end = draw(st.integers(min_value=0, max_value=23))
    outside_hours = _hours_outside_window(start, end)
    # A half-open [start, end) interval can never cover all 24 hours, so
    # outside_hours is always non-empty.
    hour = draw(st.sampled_from(outside_hours))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))

    threshold = draw(st.floats(min_value=0.0, max_value=100.0))
    usage = draw(_abnormal_usage_results)

    config = MonitorConfig(
        unrestricted_start_hour=start,
        unrestricted_end_hour=end,
        threshold_percent=threshold,
    )
    now = datetime(2024, 1, 1, hour, minute, second)
    return config, now, usage


@settings(max_examples=100)
@given(case=_restricted_abnormal_case())
def test_property5_restricted_window_failsafe_stop(case):
    config, now, usage = case

    # Sanity: the generated time really is outside the configured window.
    assert in_unrestricted_window(now, config) is False

    decision = evaluate_capacity(now=now, config=config, usage=usage)

    # Fail-safe: STOP on any abnormal usage in the restricted window.
    assert decision.should_continue is False
    # The reason identifies the specific retrieval/validation failure.
    if isinstance(usage, RetrievalError):
        assert decision.reason == "retrieval_error_restricted"
    else:
        assert decision.reason == "invalid_value_restricted"
    assert decision.reason in {
        "retrieval_error_restricted",
        "invalid_value_restricted",
    }


# --- Property-based test (Task 4.2) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 1
# Property 1: Activation scope is exactly the Target_Judge
# Validates: Requirements 1.1, 1.2
#
# For any judge identifier, a monitor built from a present ``session_monitor``
# config block is enabled if and only if that identifier equals the configured
# ``target_judge``; and for any non-target judge the monitor is disabled, its
# ``should_continue`` returns CONTINUE, and it never invokes the usage provider.
#
# NOTE: Hypothesis does not support the pytest ``tmp_path`` fixture inside
# ``@given``, so the temp config is written via ``tempfile`` inside the test.

import os
import tempfile

# Identifiers spanning real judge names plus arbitrary text, so equality with
# the configured target_judge is exercised both ways (match and mismatch).
_judge_identifiers = st.one_of(
    st.sampled_from(
        ["claude_9router", "gpt_9router", "gpt", "claude", "gemini", "qwen"]
    ),
    st.text(min_size=1, max_size=20),
)


@settings(max_examples=100)
@given(judge_name=_judge_identifiers, target_judge=_judge_identifiers)
def test_property1_activation_scope_is_exactly_target_judge(judge_name, target_judge):
    # A present session_monitor block configuring an arbitrary target_judge.
    config_data = {"session_monitor": {"target_judge": target_judge}}

    tmp_dir = tempfile.mkdtemp()
    config_path = os.path.join(tmp_dir, "config.json")
    try:
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config_data, fh)

        spy = _SpyProvider()
        monitor = SessionCapacityMonitor.from_config(
            judge_name, config_path, provider=spy
        )

        # Enabled iff the identifier equals the configured target_judge.
        assert monitor.enabled is (judge_name == target_judge)

        if judge_name != target_judge:
            # Non-target judge: disabled no-op that always continues and never
            # touches the provider.
            decision = monitor.should_continue(
                completed_count=0, output_path="out.jsonl"
            )
            assert decision.should_continue is True
            assert decision.reason == "disabled"
            assert spy.calls == 0
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)
        os.rmdir(tmp_dir)


# --- Property-based test (Task 4.4) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 6
# Property 6: Stop messages contain required information
# Validates: Requirements 7.1, 7.2
#
# For any stop caused by reaching the threshold, the emitted message contains
# both the observed usage percentage and the configured threshold; and for any
# graceful stop (any stop reason), the emitted message contains both the number
# of completed interactions and the output file path.
#
# The enabled monitor reads ``datetime.now()`` internally, so we freeze the
# module-level clock to a restricted hour (12:30) for the duration of the call
# and restore it in a finally block (``@given`` cannot easily consume the
# monkeypatch fixture). A configurable ``_FakeProvider`` supplies the usage
# result that drives each stop reason: an ``Ok(v)`` with ``v >= threshold``
# forces a threshold stop, while ``RetrievalError`` and ``Invalid`` exercise the
# other graceful-stop reasons.


@st.composite
def _stop_case(draw):
    """Draw a (threshold, usage_result) pair that forces a graceful stop.

    Three stop reasons are covered:
      * ``threshold``  -> ``Ok(v)`` with ``v >= threshold`` (at_or_above_threshold)
      * ``retrieval``  -> ``RetrievalError`` (retrieval_error_restricted)
      * ``invalid``    -> ``Invalid`` (invalid_value_restricted)
    The threshold spans the full [0, 100] range, including the 0 and 100
    boundaries, and the threshold-stop usage includes ``v == threshold``.
    """
    threshold = draw(st.floats(min_value=0.0, max_value=100.0))
    kind = draw(st.sampled_from(["threshold", "retrieval", "invalid"]))
    if kind == "threshold":
        # v >= threshold (boundary v == threshold included) -> threshold stop.
        v = draw(st.floats(min_value=threshold, max_value=100.0))
        return threshold, Ok(v)
    if kind == "retrieval":
        return threshold, RetrievalError(draw(st.text()))
    return threshold, Invalid(
        draw(st.one_of(st.text(), st.integers(), st.none(), st.floats(allow_nan=True)))
    )


@settings(max_examples=100)
@given(
    case=_stop_case(),
    completed_count=st.integers(min_value=0, max_value=10**9),
    output_path=st.text(),
)
def test_property6_stop_messages_contain_required_information(
    case, completed_count, output_path
):
    threshold, usage_result = case
    config = MonitorConfig(threshold_percent=threshold)
    monitor = _enabled_monitor(provider=_FakeProvider(usage_result), config=config)

    # Freeze the module clock to a restricted hour (outside 00:00..03:00) so the
    # monitor performs retrieval and reaches a stop decision. Restore it after.
    import mindeval.session_monitor as sm

    original_datetime = sm.datetime
    sm.datetime = _FixedClock(datetime(2024, 1, 1, 12, 30, 0))
    try:
        decision = monitor.should_continue(
            completed_count=completed_count, output_path=output_path
        )
    finally:
        sm.datetime = original_datetime

    # The usage result forces a graceful stop in the restricted window.
    assert decision.should_continue is False
    assert decision.message is not None

    # Requirement 7.2: every graceful stop names the completed count and output
    # path, regardless of the stop reason.
    assert str(completed_count) in decision.message
    assert output_path in decision.message

    # Requirement 7.1: a threshold stop additionally names the observed usage
    # percentage and the configured threshold.
    if decision.reason == "at_or_above_threshold":
        assert str(decision.usage_percentage) in decision.message
        assert str(monitor.config.threshold_percent) in decision.message


# --- Property-based test (Task 9.2) -------------------------------------------
# Feature: session-capacity-auto-stop, Property 7
# Property 7: Resume processes exactly the un-judged interactions
# Validates: Requirements 5.3
#
# For any set of interaction ids (a list that may contain duplicates) and for
# any subset already present in the output file (including ids not in all_ids,
# and the empty and full subsets), compute_todo_ids returns exactly the
# complement of the already-present subset within all_ids: no already-judged id
# is reprocessed and no un-judged id is omitted. The result is de-duplicated and
# preserves the first-occurrence order of all_ids.

from mindeval.session_monitor import compute_todo_ids

# A small id pool so that all_ids reliably contains duplicates and existing_ids
# reliably overlaps with (and sometimes extends beyond) all_ids.
_id_pool = st.one_of(
    st.integers(min_value=0, max_value=9),
    st.sampled_from(["a", "b", "c", "d", "e"]),
)


@st.composite
def _ids_and_existing(draw):
    """Draw an (all_ids list, existing_ids) pair.

    ``all_ids`` is a list that may contain duplicates (including the empty list).
    ``existing_ids`` is built from an arbitrary subset of the distinct ids in
    ``all_ids`` (covering the empty and full subsets) plus arbitrary extra ids
    that may not appear in ``all_ids`` at all.
    """
    all_ids = draw(st.lists(_id_pool, min_size=0, max_size=20))

    distinct = list(dict.fromkeys(all_ids))  # first-occurrence order, unique
    # Choose how many of the distinct ids are already present. Forcing 0 and the
    # full count exercises the empty-subset and full-subset edge cases.
    if distinct:
        k = draw(st.integers(min_value=0, max_value=len(distinct)))
        # A deterministic-but-varied subset selection driven by Hypothesis.
        flags = draw(
            st.lists(st.booleans(), min_size=len(distinct), max_size=len(distinct))
        )
        present = [d for d, keep in zip(distinct, flags) if keep]
        # Occasionally force the full subset to guarantee that edge is hit.
        if draw(st.booleans()):
            present = distinct[:k]
    else:
        present = []

    # Extra ids that may or may not be in all_ids (arbitrary "already-present" set).
    extras = draw(st.lists(_id_pool, min_size=0, max_size=10))

    # existing_ids may be any iterable; vary list vs set representation.
    existing = present + extras
    if draw(st.booleans()):
        existing = set(existing)
    return all_ids, existing


@settings(max_examples=100)
@given(case=_ids_and_existing())
def test_property7_resume_processes_exactly_unjudged(case):
    all_ids, existing_ids = case

    todo = compute_todo_ids(all_ids, existing_ids)

    existing_set = set(existing_ids)
    all_set = set(all_ids)

    # Every returned id is in all_ids and not in existing_ids.
    for item in todo:
        assert item in all_set
        assert item not in existing_set

    # Result has no duplicates.
    assert len(todo) == len(set(todo))

    # Result preserves the first-occurrence order of all_ids (restricted to the
    # ids that survive the filter).
    expected_order = [
        item
        for item in dict.fromkeys(all_ids)  # first-occurrence order, de-duplicated
        if item not in existing_set
    ]
    assert todo == expected_order

    # The set of returned ids equals exactly the complement of existing within all.
    assert set(todo) == all_set - existing_set
