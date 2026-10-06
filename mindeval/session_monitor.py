"""Session Capacity Monitor — core data models.

This module is a non-invasive add-on used to gate an in-progress evaluation run
against the usage of a shared 9router proxy session. It is intentionally
self-contained: no existing module imports from here yet, and this module does
not import any existing project module.

This file currently defines only the foundational data models (Task 1.1):

- ``MonitorConfig``  — frozen dataclass holding the monitor configuration.
- ``UsageResult``    — tagged union (``Ok`` | ``Invalid`` | ``RetrievalError``).
- ``CapacityDecision`` — NamedTuple describing a single continue/stop verdict.

Later tasks add pure helpers and the orchestrating monitor to this same file.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, NamedTuple, Optional, Protocol, Union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for the Session Capacity Monitor.

    Defaults match the requirements: threshold 50%, an unrestricted window of
    00:00 (inclusive) to 03:00 (exclusive), and a provider whose concrete HTTP
    wiring is intentionally unset until the real dashboard endpoint is confirmed.
    """

    target_judge: str = "claude_9router"
    threshold_percent: float = 50.0
    unrestricted_start_hour: int = 0  # 00:00 inclusive (single-window back-compat)
    unrestricted_end_hour: int = 3  # 03:00 exclusive (single-window back-compat)
    # Optional list of multiple unrestricted windows as (start_hour, end_hour)
    # half-open pairs. When non-empty, it takes precedence over the single
    # start/end pair above and the run is unrestricted if the current hour falls
    # in ANY of these windows.
    unrestricted_windows: tuple = ()
    # Optional list of additional unrestricted windows as ((start_hour, end_hour), ...).
    # When non-empty, membership is "inside ANY window"; otherwise the single
    # start/end pair above is used (backward compatible).
    unrestricted_windows: tuple = ()
    provider_url: Optional[str] = None  # UNCONFIRMED — must be wired up
    provider_method: str = "GET"
    provider_headers: dict = field(default_factory=dict)
    provider_json_path: Optional[str] = None  # UNCONFIRMED — must be wired up
    provider_timeout: float = 10.0
    # Provider selection + 9router-specific settings.
    provider_type: str = "http"  # "http" (generic) | "router9" (9Router proxy)
    provider_base_url: Optional[str] = None  # e.g. http://localhost:20128
    provider_connection_id: Optional[str] = None  # 9router provider connection id
    provider_quota_key: str = "session (5h)"  # which quota to read
    provider_base_dir: Optional[str] = None  # 9router app-data dir (for cli token)
    provider_refresh_seconds: float = 120.0  # min seconds between live usage fetches
    provider_stale_seconds: float = 900.0  # reuse last good value up to this age on error
    provider_fail_open: bool = True  # on cold-start fetch failure, continue (don't stop)
    # Behavior when the threshold is reached in the restricted window:
    #   "stop" → end the run (resume by re-running);
    #   "wait" → pause and poll until usage drops below threshold, then continue.
    action: str = "stop"
    wait_poll_seconds: float = 120.0  # how often to re-check while paused in "wait" mode


# --- UsageResult tagged union -------------------------------------------------


@dataclass(frozen=True)
class Ok:
    """A successfully retrieved and validated usage value in the range 0..100."""

    value: float


@dataclass(frozen=True)
class Invalid:
    """A value was retrieved but is out of [0, 100] or otherwise unparseable."""

    raw: object


@dataclass(frozen=True)
class RetrievalError:
    """Usage could not be retrieved (network / HTTP / timeout / auth / unconfigured)."""

    detail: str


# The tagged union of all possible usage retrieval outcomes.
UsageResult = Union[Ok, Invalid, RetrievalError]


class CapacityDecision(NamedTuple):
    """The verdict produced for a single capacity check.

    ``reason`` is a machine-readable code, one of:
    ``"disabled"`` | ``"unrestricted_window"`` | ``"below_threshold"``
    | ``"at_or_above_threshold"`` | ``"retrieval_error_restricted"``
    | ``"retrieval_error_unrestricted"`` | ``"invalid_value_restricted"``
    | ``"invalid_value_unrestricted"``.
    """

    should_continue: bool
    reason: str
    usage_percentage: Optional[float]
    message: Optional[str]


# --- Pure helpers -------------------------------------------------------------


def validate_usage(raw: object) -> UsageResult:
    """Validate a raw retrieved usage value into a :data:`UsageResult`.

    Parses ``raw`` as a number and returns ``Ok(v)`` if and only if the parsed
    value ``v`` satisfies ``0 <= v <= 100`` (boundaries inclusive). Any value
    that is unparseable, non-finite (``NaN`` / infinity), or outside the
    ``[0, 100]`` range is classified as ``Invalid(raw)``.

    Notes:
        - Numeric strings such as ``"50"`` or ``" 99.5 "`` are accepted.
        - Booleans are rejected as ``Invalid`` since they are not meaningful
          usage percentages even though ``bool`` is a subclass of ``int``.
        - The original ``raw`` value is preserved verbatim inside ``Invalid``.

    Validates: Requirements 2.2, 2.3 (Design: Property 4).
    """
    # Booleans are technically ints in Python but are never valid usage values.
    if isinstance(raw, bool):
        return Invalid(raw)

    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return Invalid(raw)

    # Reject NaN and +/-infinity: the range comparison below would also reject
    # NaN, but being explicit guards against accidental Ok(inf)-style mistakes.
    if value != value or value in (float("inf"), float("-inf")):
        return Invalid(raw)

    if 0.0 <= value <= 100.0:
        return Ok(value)

    return Invalid(raw)


def _hour_in_window(hour: int, start: int, end: int) -> bool:
    """Half-open membership of ``hour`` in ``[start, end)`` with wrap-around.

    ``start == end`` is an empty window (always False); ``start < end`` is a
    normal interval; ``start > end`` wraps past midnight (inside iff
    ``hour >= start`` or ``hour < end``).
    """
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def in_unrestricted_window(now: datetime, config: MonitorConfig) -> bool:
    """Return whether ``now`` falls inside any configured unrestricted window.

    Only the hour-of-day of ``now`` is considered. If ``config`` defines a list
    of ``unrestricted_windows`` (one or more ``(start_hour, end_hour)`` half-open
    pairs), the result is True when the current hour is inside ANY of them.
    Otherwise the single ``[unrestricted_start_hour, unrestricted_end_hour)``
    pair is used (start inclusive, end exclusive).

    Each window supports wrap-around past midnight (e.g. ``23..4`` covers hours
    23, 0, 1, 2, 3) and treats ``start == end`` as an empty window.

    Validates: Requirements 3.1, 3.2, 8.2.
    """
    hour = now.hour
    windows = getattr(config, "unrestricted_windows", ()) or ()
    if windows:
        return any(_hour_in_window(hour, s, e) for (s, e) in windows)
    return _hour_in_window(hour, config.unrestricted_start_hour, config.unrestricted_end_hour)


# --- Pure decision core (Task 3.1) --------------------------------------------


def evaluate_capacity(
    *,
    now: datetime,
    config: MonitorConfig,
    usage: UsageResult,
) -> CapacityDecision:
    """Decide whether the run may continue, based solely on time and usage.

    This is the pure decision heart of the feature: it performs no I/O and
    holds all of the continue/stop requirement logic. The caller is responsible
    for obtaining ``now`` and (only when needed) retrieving ``usage``.

    Decision rules (mirrors Requirements 3, 4, 6):

    - **Unrestricted window** (``in_unrestricted_window`` is true): always
      CONTINUE with reason ``"unrestricted_window"``. ``usage`` is never
      inspected here, consistent with the provider not being called in this
      window. *(R3.1, R3.2, R6.2)*
    - **Restricted window** with ``Ok(v)`` and ``v < threshold``: CONTINUE with
      reason ``"below_threshold"``. *(R4.1)*
    - **Restricted window** with ``Ok(v)`` and ``v >= threshold``: STOP with
      reason ``"at_or_above_threshold"``. *(R4.2)*
    - **Restricted window** with ``RetrievalError``: STOP with reason
      ``"retrieval_error_restricted"`` (fail-safe). *(R6.1)*
    - **Restricted window** with ``Invalid``: STOP with reason
      ``"invalid_value_restricted"`` (fail-safe). *(R2.3, R6.1)*

    ``usage_percentage`` is populated whenever an ``Ok`` value is available.
    ``message`` is left ``None`` here; human-facing message formatting is the
    responsibility of the monitor (Task 4.3).

    Validates: Requirements 3.1, 3.2, 4.1, 4.2, 6.1, 6.2, 2.3
    (Design: Properties 2, 3, 5).
    """
    # Unrestricted window: continue unconditionally without inspecting usage.
    if in_unrestricted_window(now, config):
        return CapacityDecision(
            should_continue=True,
            reason="unrestricted_window",
            usage_percentage=None,
            message=None,
        )

    # Restricted window: enforce the capacity threshold and fail safe on any
    # abnormal usage result.
    if isinstance(usage, Ok):
        if usage.value < config.threshold_percent:
            return CapacityDecision(
                should_continue=True,
                reason="below_threshold",
                usage_percentage=usage.value,
                message=None,
            )
        return CapacityDecision(
            should_continue=False,
            reason="at_or_above_threshold",
            usage_percentage=usage.value,
            message=None,
        )

    if isinstance(usage, RetrievalError):
        return CapacityDecision(
            should_continue=False,
            reason="retrieval_error_restricted",
            usage_percentage=None,
            message=None,
        )

    # Remaining case: Invalid.
    return CapacityDecision(
        should_continue=False,
        reason="invalid_value_restricted",
        usage_percentage=None,
        message=None,
    )


# --- Config parsing + factory (Task 4.1) --------------------------------------


def _coerce_str(value: object, default: str, *, field_name: str) -> str:
    """Return ``value`` as a non-empty string, else log a warning and use ``default``."""
    if isinstance(value, str) and value != "":
        return value
    logger.warning(
        "session_monitor: invalid value for %s (%r); using default %r",
        field_name,
        value,
        default,
    )
    return default


def _coerce_float(value: object, default: float, *, field_name: str) -> float:
    """Return ``value`` as a float, else log a warning and use ``default``.

    Booleans are rejected because ``bool`` is an ``int`` subclass but is never a
    meaningful numeric configuration value.
    """
    if isinstance(value, bool):
        logger.warning(
            "session_monitor: invalid value for %s (%r); using default %r",
            field_name,
            value,
            default,
        )
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            pass
    logger.warning(
        "session_monitor: invalid value for %s (%r); using default %r",
        field_name,
        value,
        default,
    )
    return default


def _coerce_int_hour(value: object, default: int, *, field_name: str) -> int:
    """Return ``value`` as an integer hour, else log a warning and use ``default``."""
    if isinstance(value, bool):
        logger.warning(
            "session_monitor: invalid value for %s (%r); using default %r",
            field_name,
            value,
            default,
        )
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            pass
    logger.warning(
        "session_monitor: invalid value for %s (%r); using default %r",
        field_name,
        value,
        default,
    )
    return default


def parse_monitor_config(block: Optional[dict]) -> MonitorConfig:
    """Build a :class:`MonitorConfig` from a raw ``session_monitor`` config block.

    Missing keys fall back to the documented defaults (target judge
    ``claude_9router``, threshold 50%, window 00:00–03:00, an unconfigured
    provider). Individual values with the wrong type are logged as a warning and
    replaced with their default rather than raising, so a partially malformed
    block degrades gracefully (Requirement 8.3).

    A ``None`` block (no ``session_monitor`` configured) yields an all-defaults
    config.

    Validates: Requirements 8.1, 8.2, 8.3.
    """
    defaults = MonitorConfig()
    if block is None:
        return defaults
    if not isinstance(block, dict):
        logger.warning(
            "session_monitor: expected an object for the 'session_monitor' block, "
            "got %r; using defaults",
            block,
        )
        return defaults

    target_judge = _coerce_str(
        block.get("target_judge", defaults.target_judge),
        defaults.target_judge,
        field_name="target_judge",
    )
    threshold_percent = _coerce_float(
        block.get("threshold_percent", defaults.threshold_percent),
        defaults.threshold_percent,
        field_name="threshold_percent",
    )

    window = block.get("unrestricted_window", {})
    if not isinstance(window, dict):
        logger.warning(
            "session_monitor: expected an object for 'unrestricted_window', got %r; "
            "using defaults",
            window,
        )
        window = {}
    start_hour = _coerce_int_hour(
        window.get("start_hour", defaults.unrestricted_start_hour),
        defaults.unrestricted_start_hour,
        field_name="unrestricted_window.start_hour",
    )
    end_hour = _coerce_int_hour(
        window.get("end_hour", defaults.unrestricted_end_hour),
        defaults.unrestricted_end_hour,
        field_name="unrestricted_window.end_hour",
    )

    # Optional list of multiple unrestricted windows.
    windows_list = block.get("unrestricted_windows", None)
    parsed_windows: list = []
    if isinstance(windows_list, list):
        for i, w in enumerate(windows_list):
            if not isinstance(w, dict):
                logger.warning(
                    "session_monitor: unrestricted_windows[%d] is not an object (%r); skipped",
                    i, w,
                )
                continue
            s = _coerce_int_hour(w.get("start_hour", 0), 0, field_name=f"unrestricted_windows[{i}].start_hour")
            e = _coerce_int_hour(w.get("end_hour", 0), 0, field_name=f"unrestricted_windows[{i}].end_hour")
            parsed_windows.append((s, e))
    elif windows_list is not None:
        logger.warning(
            "session_monitor: 'unrestricted_windows' must be a list; got %r; ignored",
            windows_list,
        )
    unrestricted_windows = tuple(parsed_windows)

    provider = block.get("provider", {})
    if not isinstance(provider, dict):
        logger.warning(
            "session_monitor: expected an object for 'provider', got %r; using defaults",
            provider,
        )
        provider = {}

    raw_url = provider.get("url", defaults.provider_url)
    provider_url = raw_url if isinstance(raw_url, str) and raw_url != "" else defaults.provider_url

    provider_method = _coerce_str(
        provider.get("method", defaults.provider_method),
        defaults.provider_method,
        field_name="provider.method",
    )

    raw_headers = provider.get("headers", None)
    if raw_headers is None:
        provider_headers: dict = {}
    elif isinstance(raw_headers, dict):
        provider_headers = dict(raw_headers)
    else:
        logger.warning(
            "session_monitor: expected an object for 'provider.headers', got %r; "
            "using empty headers",
            raw_headers,
        )
        provider_headers = {}

    raw_json_path = provider.get("json_path", defaults.provider_json_path)
    provider_json_path = (
        raw_json_path
        if isinstance(raw_json_path, str) and raw_json_path != ""
        else defaults.provider_json_path
    )

    provider_timeout = _coerce_float(
        provider.get("timeout", defaults.provider_timeout),
        defaults.provider_timeout,
        field_name="provider.timeout",
    )

    raw_ptype = provider.get("type", defaults.provider_type)
    provider_type = raw_ptype if isinstance(raw_ptype, str) and raw_ptype else defaults.provider_type

    raw_base = provider.get("base_url", defaults.provider_base_url)
    provider_base_url = raw_base if isinstance(raw_base, str) and raw_base else defaults.provider_base_url

    raw_conn = provider.get("connection_id", defaults.provider_connection_id)
    provider_connection_id = (
        raw_conn if isinstance(raw_conn, str) and raw_conn else defaults.provider_connection_id
    )

    raw_qkey = provider.get("quota_key", defaults.provider_quota_key)
    provider_quota_key = raw_qkey if isinstance(raw_qkey, str) and raw_qkey else defaults.provider_quota_key

    raw_bdir = provider.get("base_dir", defaults.provider_base_dir)
    provider_base_dir = raw_bdir if isinstance(raw_bdir, str) and raw_bdir else defaults.provider_base_dir

    provider_refresh_seconds = _coerce_float(
        provider.get("refresh_seconds", defaults.provider_refresh_seconds),
        defaults.provider_refresh_seconds,
        field_name="provider.refresh_seconds",
    )
    provider_stale_seconds = _coerce_float(
        provider.get("stale_seconds", defaults.provider_stale_seconds),
        defaults.provider_stale_seconds,
        field_name="provider.stale_seconds",
    )
    raw_failopen = provider.get("fail_open", defaults.provider_fail_open)
    provider_fail_open = bool(raw_failopen) if isinstance(raw_failopen, bool) else defaults.provider_fail_open

    raw_action = block.get("action", defaults.action)
    action = raw_action if raw_action in ("stop", "wait") else defaults.action
    wait_poll_seconds = _coerce_float(
        block.get("wait_poll_seconds", defaults.wait_poll_seconds),
        defaults.wait_poll_seconds,
        field_name="wait_poll_seconds",
    )

    return MonitorConfig(
        target_judge=target_judge,
        threshold_percent=threshold_percent,
        unrestricted_start_hour=start_hour,
        unrestricted_end_hour=end_hour,
        unrestricted_windows=unrestricted_windows,
        provider_url=provider_url,
        provider_method=provider_method,
        provider_headers=provider_headers,
        provider_json_path=provider_json_path,
        provider_timeout=provider_timeout,
        provider_type=provider_type,
        provider_base_url=provider_base_url,
        provider_connection_id=provider_connection_id,
        provider_quota_key=provider_quota_key,
        provider_base_dir=provider_base_dir,
        provider_refresh_seconds=provider_refresh_seconds,
        provider_stale_seconds=provider_stale_seconds,
        provider_fail_open=provider_fail_open,
        action=action,
        wait_poll_seconds=wait_poll_seconds,
    )


def _load_session_monitor_block(config_path: Optional[str]) -> Optional[dict]:
    """Load the raw ``session_monitor`` block from ``config_path``.

    Returns the block dict when present, or ``None`` when the file is missing,
    unreadable, not valid JSON, or simply has no ``session_monitor`` key. Parse
    failures are logged as a warning so a malformed config never raises here; an
    absent or unreadable config simply leaves the monitor disabled.
    """
    if not config_path:
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.warning("session_monitor: config file not found at %s", config_path)
        return None
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "session_monitor: could not read/parse config at %s (%s); monitor disabled",
            config_path,
            exc,
        )
        return None

    if not isinstance(data, dict):
        logger.warning(
            "session_monitor: top-level config is not an object (%r); monitor disabled",
            data,
        )
        return None

    return data.get("session_monitor")


class SessionCapacityMonitor:
    """Orchestrates the continue/stop decision and is the single integration point.

    A monitor is **enabled** only when the selected ``judge_name`` matches the
    configured ``target_judge`` *and* a ``session_monitor`` config block is
    present. Otherwise it is a **disabled** no-op whose :meth:`should_continue`
    always returns CONTINUE and never touches the usage provider — guaranteeing
    zero behavioral change for every other judge (Requirements 1.1, 1.2).

    The full enabled-path retrieval and message formatting are implemented in a
    later task; this class currently provides the factory, the ``enabled``
    property, provider injection for testing, and the disabled no-op path.
    """

    def __init__(
        self,
        *,
        config: MonitorConfig,
        enabled: bool,
        provider: Optional[Any] = None,
    ) -> None:
        self._config = config
        self._enabled = enabled
        self._provider = provider

    @property
    def config(self) -> MonitorConfig:
        return self._config

    @property
    def enabled(self) -> bool:
        return self._enabled

    @classmethod
    def from_config(
        cls,
        judge_name: Optional[str],
        config_path: Optional[str],
        *,
        provider: Optional[Any] = None,
    ) -> "SessionCapacityMonitor":
        """Build a monitor from the optional ``session_monitor`` config block.

        Returns an **enabled** monitor only when a ``session_monitor`` block is
        present *and* ``judge_name`` equals the block's ``target_judge``;
        otherwise returns a **disabled** no-op monitor. Malformed config values
        are logged and replaced with defaults, and a mismatched ``target_judge``
        keeps the monitor disabled.

        Validates: Requirements 1.1, 1.2, 8.1, 8.2, 8.3.
        """
        block = _load_session_monitor_block(config_path)
        config = parse_monitor_config(block)
        enabled = (
            block is not None
            and judge_name is not None
            and judge_name == config.target_judge
        )
        return cls(config=config, enabled=enabled, provider=provider)

    def should_continue(self, completed_count: int, output_path: str) -> CapacityDecision:
        """Decide whether the run may proceed before submitting the next batch.

        A disabled monitor short-circuits to CONTINUE immediately, performing no
        time check and never calling the provider (Requirement 1.2).

        An enabled monitor:

        - Reads the current local time ``now`` (``datetime.now()``).
        - In the **unrestricted window**, skips usage retrieval entirely and
          delegates to :func:`evaluate_capacity` (which ignores ``usage`` in this
          branch), returning a CONTINUE decision with reason
          ``"unrestricted_window"`` (Requirements 3.1, 3.2).
        - In the **restricted window**, queries the injected provider exactly
          once via ``get_usage_percentage()`` (Requirement 2.1); when no provider
          is configured the retrieval is treated as a ``RetrievalError`` so the
          run fails safe. The verdict is delegated to :func:`evaluate_capacity`.

        On any STOP verdict a human-facing ``message`` is formatted:

        - ``at_or_above_threshold`` → the message names the observed usage
          percentage and the configured threshold (Requirement 7.1), plus the
          completed count and output path (Requirement 7.2).
        - other stop reasons (``retrieval_error_restricted``,
          ``invalid_value_restricted``) → the message names the failure reason,
          plus the completed count and output path (Requirement 7.2).

        On CONTINUE the ``message`` is left ``None``.

        In ``action="wait"`` mode, instead of returning a STOP decision when the
        threshold is reached, the call **blocks**: it pauses and re-checks every
        ``wait_poll_seconds`` until the session usage drops back below the
        threshold (e.g. after a 5-hour reset) or the time enters the unrestricted
        window, then returns CONTINUE. The run never exits; completed judgments
        stay saved between checks.

        Validates: Requirements 2.1, 5.2, 7.1, 7.2.
        """
        if not self._enabled:
            return CapacityDecision(
                should_continue=True,
                reason="disabled",
                usage_percentage=None,
                message=None,
            )

        decision = self._decide_once(completed_count, output_path)
        if decision.should_continue:
            return decision

        # Threshold reached (or fail-safe stop). In "stop" mode, return the stop
        # decision so the generator ends the run. In "wait" mode, pause and poll
        # until it is safe to continue.
        if self._config.action != "wait":
            return decision

        return self._wait_until_clear(decision, completed_count, output_path)

    def _decide_once(self, completed_count: int, output_path: str) -> CapacityDecision:
        """Make a single continue/stop decision (no waiting)."""
        now = datetime.now()

        if in_unrestricted_window(now, self._config):
            # Unrestricted window: skip retrieval entirely. evaluate_capacity
            # ignores ``usage`` here, so any placeholder is fine.
            return evaluate_capacity(
                now=now,
                config=self._config,
                usage=RetrievalError("usage not retrieved in unrestricted window"),
            )

        # Restricted window: retrieve usage exactly once. An absent provider is
        # treated as a retrieval error (fail-safe stop).
        if self._provider is None:
            usage: UsageResult = RetrievalError("provider not configured")
        else:
            usage = self._provider.get_usage_percentage()

        decision = evaluate_capacity(now=now, config=self._config, usage=usage)

        if decision.should_continue:
            return decision

        message = self._format_stop_message(
            decision, completed_count=completed_count, output_path=output_path
        )
        return decision._replace(message=message)

    def _wait_until_clear(
        self, decision: CapacityDecision, completed_count: int, output_path: str
    ) -> CapacityDecision:
        """Pause and poll until the run may continue (``action="wait"`` mode).

        Re-checks every ``wait_poll_seconds`` and returns CONTINUE as soon as the
        usage drops below the threshold or the time enters the unrestricted
        window. Blocks indefinitely otherwise (the run is paused, not stopped).
        """
        import time

        poll = max(
            5.0,
            float(self._config.wait_poll_seconds),
            float(self._config.provider_refresh_seconds) + 1.0,
        )
        print(
            f"[session-monitor] Paused: {decision.message} "
            f"Waiting for session to reset below {self._config.threshold_percent}% "
            f"(re-checking every {int(poll)}s). The run is paused, not stopped."
        )
        while True:
            time.sleep(poll)
            decision = self._decide_once(completed_count, output_path)
            if decision.should_continue:
                pct = decision.usage_percentage
                pct_str = f"{pct}%" if pct is not None else "unrestricted window"
                print(
                    f"[session-monitor] Resuming evaluation (session now {pct_str}, "
                    f"below threshold {self._config.threshold_percent}%)."
                )
                return decision
            # Still blocked; emit a brief heartbeat and keep waiting.
            print(
                f"[session-monitor] Still paused ({decision.reason}); "
                f"re-checking in {int(poll)}s."
            )

    def _format_stop_message(
        self,
        decision: CapacityDecision,
        *,
        completed_count: int,
        output_path: str,
    ) -> str:
        """Build the human-facing message for a graceful stop.

        Always includes the number of completed interactions and the output file
        path (Requirement 7.2). For a threshold stop it additionally states the
        observed usage percentage and the configured threshold (Requirement 7.1).
        """
        progress = (
            f"Completed {completed_count} interaction(s); "
            f"saved to {output_path}."
        )

        if decision.reason == "at_or_above_threshold":
            return (
                "Stopping evaluation: session usage "
                f"{decision.usage_percentage}% has reached the configured "
                f"threshold of {self._config.threshold_percent}%. "
                f"{progress} Re-run to resume the remaining interactions."
            )

        if decision.reason == "retrieval_error_restricted":
            return (
                "Stopping evaluation: could not retrieve the session usage "
                "percentage (retrieval failure). "
                f"{progress} Re-run to resume the remaining interactions."
            )

        if decision.reason == "invalid_value_restricted":
            return (
                "Stopping evaluation: the retrieved session usage value was "
                "invalid (outside 0-100 or unparseable). "
                f"{progress} Re-run to resume the remaining interactions."
            )

        # Fallback for any other stop reason: still satisfy Requirement 7.2.
        return (
            f"Stopping evaluation ({decision.reason}). "
            f"{progress} Re-run to resume the remaining interactions."
        )


# --- Pluggable session-usage provider (Task 6.1) -----------------------------


def _extract_json_path(data: object, json_path: str) -> object:
    """Pluck a value out of ``data`` using a simple dotted ``json_path``.

    The path is a dot-separated sequence of keys (e.g.
    ``"data.session.usage_percent"``). Each segment indexes into a mapping. If
    any segment is missing or the current value is not a mapping, a
    :class:`KeyError` is raised so the caller can convert it into a
    :class:`RetrievalError`.

    Empty path segments (e.g. a leading dot or ``"a..b"``) are treated as a
    malformed path and raise :class:`KeyError`.
    """
    current = data
    for segment in json_path.split("."):
        if segment == "":
            raise KeyError(f"empty segment in json_path {json_path!r}")
        if not isinstance(current, dict):
            raise KeyError(
                f"cannot descend into non-object at segment {segment!r} of {json_path!r}"
            )
        if segment not in current:
            raise KeyError(f"missing key {segment!r} in json_path {json_path!r}")
        current = current[segment]
    return current


class SessionUsageProvider(Protocol):
    """Interface for retrieving the current session-usage percentage.

    Implementations isolate the (currently unconfirmed) usage-retrieval
    mechanism behind a single method so the concrete source can be swapped via
    configuration or replaced with a fake/spy in tests without touching the
    monitor or the generators.
    """

    def get_usage_percentage(self) -> UsageResult:
        """Return ``Ok(0..100)``, ``Invalid(raw)``, or ``RetrievalError(detail)``.

        Implementations MUST never raise: every network/HTTP/timeout/auth or
        validation failure is converted into a ``RetrievalError`` (or
        ``Invalid``) so a monitoring failure can never crash an evaluation run.
        """
        ...


class HttpSessionUsageProvider:
    """Default, fully config-driven HTTP provider for session usage.

    The proxy's real usage endpoint is **not yet confirmed**, so every piece of
    the request is configurable: the ``url``, HTTP ``method``, ``headers`` (e.g.
    an ``Authorization`` token), the dotted ``json_path`` used to pluck the
    percentage out of the JSON response, and the request ``timeout``.

    Retrieval is fail-safe: any error (unconfigured, network, HTTP status,
    timeout, auth, non-JSON body, or a missing ``json_path``) is caught and
    returned as a :class:`RetrievalError`; an out-of-range or unparseable value
    becomes :class:`Invalid` via :func:`validate_usage`. The method never
    propagates a raw exception.

    Validates: Requirements 2.1, 2.2, 2.3, 6.1 (Design: Component 3).
    """

    def __init__(
        self,
        *,
        url: Optional[str],
        method: str = "GET",
        headers: Optional[dict] = None,
        json_path: Optional[str],
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.method = method or "GET"
        self.headers = dict(headers) if headers else {}
        self.json_path = json_path
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: MonitorConfig) -> "HttpSessionUsageProvider":
        """Build a provider from the provider-related fields of a :class:`MonitorConfig`."""
        return cls(
            url=config.provider_url,
            method=config.provider_method,
            headers=config.provider_headers,
            json_path=config.provider_json_path,
            timeout=config.provider_timeout,
        )

    def get_usage_percentage(self) -> UsageResult:
        """Retrieve and validate the session usage percentage over HTTP.

        Returns a :class:`RetrievalError` if the provider is unconfigured
        (missing ``url`` or ``json_path``) or if any error occurs during the
        request/parse; otherwise routes the extracted raw value through
        :func:`validate_usage` to produce ``Ok`` or ``Invalid``.
        """
        # Fail-safe: an unconfigured provider can never succeed.
        if not self.url or not self.json_path:
            return RetrievalError("provider not configured")

        try:
            request = urllib.request.Request(
                self.url,
                method=self.method,
                headers=self.headers,
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
            payload = json.loads(body.decode("utf-8"))
            raw_value = _extract_json_path(payload, self.json_path)
        except urllib.error.HTTPError as exc:
            return RetrievalError(f"HTTP error {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            return RetrievalError(f"network error: {exc.reason}")
        except json.JSONDecodeError as exc:
            return RetrievalError(f"invalid JSON response: {exc}")
        except KeyError as exc:
            return RetrievalError(f"could not extract usage: {exc}")
        except Exception as exc:  # noqa: BLE001 — never propagate; fail safe.
            return RetrievalError(f"usage retrieval failed: {exc}")

        return validate_usage(raw_value)


# --- ID-based resume helper (Task 9.1) ----------------------------------------


def compute_todo_ids(all_ids: Iterable, existing_ids: Iterable) -> list:
    """Return the ids from ``all_ids`` that are not present in ``existing_ids``.

    This mirrors the generators' existing ``skip_existing`` ID-based resume
    semantics: given the full set of interaction ids and the subset that already
    has judgments in the output file, the "todo" list is exactly the complement
    of ``existing_ids`` within ``all_ids``.

    Guarantees:

    - **Order-preserving:** ids are returned in their original ``all_ids`` order.
    - **De-duplicated:** if ``all_ids`` contains duplicates, each kept id appears
      only once (its first occurrence); already-judged ids are dropped.
    - ``existing_ids`` may be any iterable (list, set, generator, ...); it is
      materialized into a set once for O(1) membership checks.

    Validates: Requirements 5.3 (Design: Property 7).
    """
    existing = set(existing_ids)
    seen: set = set()
    todo: list = []
    for item in all_ids:
        if item in existing or item in seen:
            continue
        seen.add(item)
        todo.append(item)
    return todo


# --- 9Router-specific usage provider ------------------------------------------


def _default_9router_dir() -> pathlib.Path:
    """Return the 9Router app-data directory (where machine-id / cli-secret live)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return pathlib.Path(appdata) / "9router"
    return pathlib.Path.home() / "AppData" / "Roaming" / "9router"


# Maps the human quota key shown in the 9Router dashboard to the field name in
# Anthropic's OAuth usage response.
_QUOTA_KEY_TO_ANTHROPIC_FIELD = {
    "session (5h)": "five_hour",
    "weekly (7d)": "seven_day",
}

_ANTHROPIC_OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
_ANTHROPIC_BETA = "oauth-2025-04-20"
_ANTHROPIC_VERSION = "2023-06-01"


def _read_connection(base_dir: pathlib.Path, connection_id: str) -> tuple[str, bool]:
    """Return ``(access_token, is_active)`` for a 9Router provider connection.

    Reads from the local 9Router SQLite DB (``<base_dir>/db/data.sqlite``),
    table ``providerConnections``. 9Router refreshes the token in place, so
    reading it fresh on each check avoids using a stale value. ``is_active``
    reflects whether the account is currently enabled for routing.
    """
    import sqlite3

    db = base_dir / "db" / "data.sqlite"
    uri = f"file:{db.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        row = con.execute(
            "SELECT data, isActive FROM providerConnections WHERE id=?", (connection_id,)
        ).fetchone()
    finally:
        con.close()
    if not row:
        raise KeyError(f"connection {connection_id!r} not found")
    data = json.loads(row[0])
    token = data.get("accessToken")
    is_active = bool(row[1])
    if not token:
        raise KeyError("connection has no accessToken")
    return token, is_active


class Router9SessionUsageProvider:
    """Reads a Claude account's session/weekly usage for a 9Router connection.

    9Router's own ``/api/usage`` endpoint only returns quota data to an
    *admin* (dashboard-password) session, so the locally-derivable CLI token is
    insufficient. Instead this provider reads the connection's OAuth access
    token from 9Router's local SQLite DB and calls Anthropic's OAuth usage
    endpoint directly — exactly the same upstream call the dashboard makes —
    and returns the ``utilization`` (percent used, 0..100) of the configured
    quota (``session (5h)`` → ``five_hour`` by default).

    Like every provider it never raises: any error becomes a ``RetrievalError``
    so a monitoring failure cannot crash an evaluation run (fail-safe stop in
    the restricted window).

    Validates: Requirements 2.1, 2.2, 2.3, 6.1 (9Router integration).
    """

    def __init__(
        self,
        *,
        connection_id: str,
        quota_key: str = "session (5h)",
        base_dir: Optional[str] = None,
        timeout: float = 10.0,
        base_url: Optional[str] = None,  # accepted for config compat; unused
        refresh_seconds: float = 120.0,
        stale_seconds: float = 900.0,
        fail_open: bool = True,
    ) -> None:
        self.connection_id = connection_id
        self.quota_key = quota_key or "session (5h)"
        self.base_dir = pathlib.Path(base_dir) if base_dir else _default_9router_dir()
        self.timeout = timeout
        # Anthropic's usage endpoint is rate-limited (HTTP 429), so we poll it at
        # most once per ``refresh_seconds`` and keep serving the last good value
        # for up to ``stale_seconds`` if a later refresh fails.
        self.refresh_seconds = refresh_seconds
        self.stale_seconds = stale_seconds
        # When True, a cold-start fetch failure (no value ever read) yields
        # CONTINUE (Ok(0.0)) instead of a fail-safe stop, so a transient 429 at
        # startup never kills a run at record 0. Enforcement still kicks in once
        # a real reading is obtained.
        self.fail_open = fail_open
        self._cached_value: Optional[float] = None
        self._cached_at: float = 0.0
        self._last_attempt: float = 0.0

    @classmethod
    def from_config(cls, config: MonitorConfig) -> "Router9SessionUsageProvider":
        return cls(
            connection_id=config.provider_connection_id or "",
            quota_key=config.provider_quota_key,
            base_dir=config.provider_base_dir,
            timeout=config.provider_timeout,
            refresh_seconds=config.provider_refresh_seconds,
            stale_seconds=config.provider_stale_seconds,
            fail_open=config.provider_fail_open,
        )

    def get_usage_percentage(self) -> UsageResult:
        import time

        now = time.monotonic()
        # Serve a fresh-enough cached value without hitting the network.
        if self._cached_value is not None and (now - self._cached_at) < self.refresh_seconds:
            return Ok(self._cached_value)

        # Rate-limit network attempts to once per refresh window, even on errors.
        if (now - self._last_attempt) < self.refresh_seconds:
            if self._cached_value is not None and (now - self._cached_at) < self.stale_seconds:
                return Ok(self._cached_value)
            return self._cold_start_result("within retry backoff")

        self._last_attempt = now
        result = self._fetch_with_retries()
        if isinstance(result, Ok):
            self._cached_value = result.value
            self._cached_at = now
            return result

        # Refresh failed (e.g. 429 rate limit or transient network): keep using
        # the last good value while it is still recent enough.
        if self._cached_value is not None and (now - self._cached_at) < self.stale_seconds:
            return Ok(self._cached_value)
        return self._cold_start_result(getattr(result, "detail", "unknown error"))

    def _cold_start_result(self, detail: str) -> UsageResult:
        """Decide what to return when usage is unknown and no value was ever read."""
        if self.fail_open:
            logger.warning(
                "session_monitor: session usage unavailable (%s); continuing "
                "(fail-open, no reading yet).",
                detail,
            )
            return Ok(0.0)
        return RetrievalError(f"router9 provider: {detail}")

    def _fetch_with_retries(self, attempts: int = 3) -> UsageResult:
        """Fetch usage, retrying transient failures (HTTP 429 / network) with backoff."""
        import time

        backoffs = [2.0, 5.0]
        last: UsageResult = RetrievalError("router9 provider: no attempt made")
        for i in range(attempts):
            last = self._fetch_once()
            if isinstance(last, (Ok, Invalid)):
                return last
            # last is RetrievalError; retry transient cases only.
            detail = getattr(last, "detail", "")
            transient = ("429" in detail) or ("network error" in detail) or ("timed out" in detail.lower())
            if not transient or i == attempts - 1:
                return last
            time.sleep(backoffs[min(i, len(backoffs) - 1)])
        return last

    def _fetch_once(self) -> UsageResult:
        if not self.connection_id:
            return RetrievalError("router9 provider: connection_id not configured")

        try:
            access_token, is_active = _read_connection(self.base_dir, self.connection_id)
        except Exception as exc:  # noqa: BLE001
            return RetrievalError(f"router9 provider: could not read access token: {exc}")

        # If the account is disabled in 9Router it is not serving traffic, so
        # there is nothing to constrain — report 0% used so the run continues.
        if not is_active:
            return Ok(0.0)

        field = _QUOTA_KEY_TO_ANTHROPIC_FIELD.get(self.quota_key, "five_hour")
        try:
            req = urllib.request.Request(
                _ANTHROPIC_OAUTH_USAGE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "anthropic-beta": _ANTHROPIC_BETA,
                    "anthropic-version": _ANTHROPIC_VERSION,
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return RetrievalError(f"router9 provider: Anthropic HTTP {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            return RetrievalError(f"router9 provider: network error: {exc.reason}")
        except json.JSONDecodeError as exc:
            return RetrievalError(f"router9 provider: invalid JSON response: {exc}")
        except Exception as exc:  # noqa: BLE001
            return RetrievalError(f"router9 provider: usage retrieval failed: {exc}")

        quota = payload.get(field) if isinstance(payload, dict) else None
        if not isinstance(quota, dict) or "utilization" not in quota:
            return RetrievalError(
                f"router9 provider: field {field!r} (for {self.quota_key!r}) "
                "missing in Anthropic usage response"
            )
        # ``utilization`` is already the percent used (0..100).
        return validate_usage(quota.get("utilization"))


def build_provider(config: MonitorConfig):
    """Build the usage provider implied by ``config.provider_type``.

    - ``"router9"`` → :class:`Router9SessionUsageProvider` (9Router proxy).
    - anything else → :class:`HttpSessionUsageProvider` (generic, config-driven).
    """
    if config.provider_type == "router9":
        return Router9SessionUsageProvider.from_config(config)
    return HttpSessionUsageProvider.from_config(config)
