# Design Document

## Overview

This feature adds a **Session Capacity Monitor** that gates an in-progress evaluation run
against the usage of a shared 9router proxy session. The monitor is a thin, opt-in add-on:
it engages **only** when the selected judge is `claude_9router` (the `Target_Judge`), and it
makes a single decision — *continue* or *gracefully stop* — at each batch boundary, just
before the next batch of interactions is submitted to the judge model.

### Design intent: non-invasive add-on

The user's explicit constraint is that the existing evaluation behavior must not change. The
Mind-Eval and WAI judgment-generation logic (prompt building, batching, parsing, incremental
save, `skip_existing` resume, output format) stays exactly as it is today. The monitor is
layered on top as a **pre-batch capacity check hook**:

- When the monitor is disabled (any judge other than `claude_9router`, or no monitor config),
  the generators behave byte-for-byte as they do now. No HTTP calls, no time checks, no new
  branches taken.
- When the monitor is enabled, the only new behavior is: *before submitting a batch*, ask the
  monitor "may I proceed?" If the answer is "stop", the generator breaks out of its batch loop
  **after** the already-completed judgments have been saved (they are saved after every batch
  today), then exits normally so that a later re-run resumes via the existing `skip_existing`
  path.

This keeps the change surface tiny: a small new module (`mindeval/session_monitor.py`), a
single guarded call inside each generator's batch loop, and one optional config block. No
existing function signatures change in a way that affects current callers (new parameters are
optional and default to "monitor off").

### Key research findings (Router_Proxy investigation)

The requirements flagged the session-usage source as an open question. Direct probing of the
proxy at `http://localhost:20128` established the following facts:

- The proxy is a **Next.js web application** that also exposes an **OpenAI-compatible API**
  under `/v1` (`GET /v1/models` returns the model list; this is what the `claude_9router`
  judge calls).
- The configured judge API key (`Authorization: Bearer <key>`) authorizes `/v1/*` calls but
  is **rejected** for the dashboard API. Every probed `/api/*` path (`/api/session`,
  `/api/usage`, `/api/quota`, `/api/stats`, `/api/me`, …) returned **HTTP 401 Unauthorized**
  with the bearer key, while `/api/session` returned 401 (exists, auth-gated) rather than 404.
- This means a **session-usage value is surfaced by the proxy's web dashboard**, but it lives
  behind a **different auth mechanism** (web-session cookie / dashboard login) than the
  OpenAI API key, and the exact endpoint path, request shape, auth token, and response JSON
  schema **could not be confirmed** from the codebase or unauthenticated probing.

**Conclusion (honest unknown):** We will *not* hard-code a fabricated endpoint as if it were
confirmed. Instead, session-usage retrieval is placed behind a small, **pluggable, fully
configurable provider interface** (endpoint URL, HTTP method, auth header + token, and a JSON
field path to extract the percentage are all config-driven). A sensible default targets an
`/api/session`-style JSON endpoint, but the design treats the concrete wiring as a
**configuration value to be filled in once the dashboard's usage endpoint is identified**.
Until it is wired up, the monitor's documented error-handling behavior (Requirement 6) governs
what happens, so the feature degrades safely.

## Architecture

```mermaid
flowchart TD
    A[evaluate.py] -->|subprocess --judge_name| B[generate_judgments.py / generate_wai_judgments.py]
    B --> C{Monitor enabled?\njudge == claude_9router\n+ monitor config present}
    C -- no --> D[Existing batch loop\nUNCHANGED]
    C -- yes --> E[Per-batch hook: monitor.should_continue]
    E --> F[CapacityDecision]
    F -- CONTINUE --> G[Submit next batch\n(existing logic)]
    F -- STOP --> H[Save completed judgments\n+ print message + exit]
    E --> I[SessionUsageProvider]
    I -->|HTTP GET configurable endpoint| J[(Router_Proxy\nlocalhost:20128 dashboard)]
    subgraph Pure decision core (testable)
      K[evaluate_capacity time, usage, threshold, window, judge]
    end
    E --> K
```

The monitor cleanly separates a **pure decision core** (no I/O — takes the current time, an
optional usage value or a retrieval error, the threshold, the window, and returns a decision)
from an **I/O shell** (the HTTP `SessionUsageProvider` and the wiring into the generators).
This separation is deliberate: the decision logic — which is where all the requirements live —
is a pure function that is exhaustively property-testable, while the unconfirmed HTTP layer is
isolated, mockable, and covered by a couple of integration/example tests.

### Activation flow

1. `evaluate.py` already passes `--judge_name` to each generator (unchanged).
2. Each generator constructs a monitor via a factory: `SessionCapacityMonitor.from_config(judge_name, config_path)`.
3. The factory returns a **disabled** monitor (a no-op whose `should_continue()` always returns
   CONTINUE) unless `judge_name == Target_Judge` **and** a monitor config block is present. This
   guarantees zero behavioral change for every other judge.
4. Inside the batch loop, before submitting batch *k*, the generator calls
   `monitor.should_continue(completed_count, output_path)`. On STOP it saves (already done after
   each batch) and breaks.

## Components and Interfaces

### Component 1: `SessionCapacityMonitor` (mindeval/session_monitor.py — new)

The orchestrator and the single integration point exposed to the generators.

```python
class CapacityDecision(NamedTuple):
    should_continue: bool
    reason: str                  # machine-readable: "disabled" | "unrestricted_window"
                                 # | "below_threshold" | "at_or_above_threshold"
                                 # | "retrieval_error_restricted" | "retrieval_error_unrestricted"
                                 # | "invalid_value_restricted" | "invalid_value_unrestricted"
    usage_percentage: float | None
    message: str | None          # human-facing message when stopping

class SessionCapacityMonitor:
    @classmethod
    def from_config(cls, judge_name: str | None, config_path: str | None) -> "SessionCapacityMonitor":
        """Returns an enabled monitor only when judge_name == Target_Judge AND a
        'session_monitor' config block exists; otherwise a disabled (no-op) monitor."""

    @property
    def enabled(self) -> bool: ...

    def should_continue(self, completed_count: int, output_path: str) -> CapacityDecision:
        """Called once before each batch. Disabled monitor always returns CONTINUE.
        Enabled monitor: applies window logic, retrieves usage (restricted only),
        compares to threshold, and produces a decision + user-facing messages."""
```

`should_continue` delegates the verdict to the pure core `evaluate_capacity(...)` and is only
responsible for: getting `now`, calling the provider when needed, and formatting the messages
required by Requirement 7.

### Component 2: pure decision core — `evaluate_capacity(...)`

A free function with **no I/O**, holding all requirement logic. This is the property-tested
heart of the feature.

```python
def evaluate_capacity(
    *,
    now: datetime,                 # local time
    config: MonitorConfig,
    usage: UsageResult,            # Ok(value) | Invalid(value) | RetrievalError(detail)
) -> CapacityDecision: ...
```

Logic (mirrors Requirements 3, 4, 6):
- If `now` ∈ Unrestricted_Window → CONTINUE (never inspects `usage`). *(R3.1, R3.2)*
- Else (Restricted_Window):
  - `usage` is `RetrievalError` or `Invalid` → STOP with retrieval/validation reason. *(R6.1, R2.3)*
  - `usage` is `Ok(v)` and `v < threshold` → CONTINUE. *(R4.1)*
  - `usage` is `Ok(v)` and `v >= threshold` → STOP. *(R4.2)*

Note: in the Unrestricted_Window the provider is **not called** (R3.2), so an unretrievable
usage there is simply never observed — consistent with R6.2 (continue).

### Component 3: `SessionUsageProvider` (pluggable, configurable)

Isolates the **unconfirmed** HTTP retrieval. Defined as a small interface so the concrete
endpoint can be wired/changed via config (or swapped for a mock in tests) without touching the
monitor or the generators.

```python
class SessionUsageProvider(Protocol):
    def get_usage_percentage(self) -> UsageResult:
        """Return Ok(float 0..100), Invalid(raw) if out of range/unparseable,
        or RetrievalError(detail) on network/HTTP/timeout/auth failure."""

class HttpSessionUsageProvider:
    """Default provider. Fully config-driven because the proxy's real usage endpoint
    is NOT yet confirmed (see Overview > research findings)."""
    def __init__(self, *, url: str, method: str, headers: dict, json_path: str, timeout: float): ...
```

`json_path` is a simple dotted path (e.g. `data.session.usage_percent`) used to pluck the
percentage out of the response body, so adapting to the real schema is a config edit, not a
code change. **`url`, `headers`, and `json_path` are intentionally unset by default and MUST be
filled in once the dashboard endpoint is identified;** if the provider is invoked while
unconfigured it returns `RetrievalError`, which the restricted-window logic treats as STOP
(fail-safe).

### Component 4: integration hook in the generators (minimal edit)

In `generate_judgments.py`, inside the existing synchronous chunked loop, immediately before
`judge_model.batch_generate_with_thinking(batch_messages)`:

```python
decision = monitor.should_continue(completed_count=len(accumulated_outputs), output_path=output_path)
if not decision.should_continue:
    print(decision.message)              # Requirement 7
    break                                # completed judgments already saved each batch
```

The analogous hook is added to `generate_wai_judgments.py` at the per-dialogue/per-batch
boundary of the standard sync path. The Anthropic-batch paths submit everything as one batch
and have no per-batch boundary; for `claude_9router` (an OpenAI-compatible, non-Anthropic-batch
judge) the standard chunked path is the one that executes, so the hook lands exactly where the
`Target_Judge` runs. The monitor is consulted only on the chunked path; the Anthropic-batch path
is left untouched.

## Data Models

### MonitorConfig

```python
@dataclass(frozen=True)
class MonitorConfig:
    target_judge: str = "claude_9router"
    threshold_percent: float = 50.0
    unrestricted_start_hour: int = 0      # 00:00 inclusive
    unrestricted_end_hour: int = 3        # 03:00 exclusive
    provider_url: str | None = None       # UNCONFIRMED — must be wired up
    provider_method: str = "GET"
    provider_headers: dict = field(default_factory=dict)
    provider_json_path: str | None = None # UNCONFIRMED — must be wired up
    provider_timeout: float = 10.0
```

### UsageResult (tagged union)

```python
@dataclass(frozen=True)
class Ok:            value: float          # validated 0..100
@dataclass(frozen=True)
class Invalid:       raw: object           # retrieved but out of [0,100] or unparseable
@dataclass(frozen=True)
class RetrievalError: detail: str          # network / HTTP / timeout / auth / unconfigured
UsageResult = Ok | Invalid | RetrievalError
```

### Config block (config.json — new, optional `session_monitor` key)

```jsonc
{
  "session_monitor": {
    "target_judge": "claude_9router",
    "threshold_percent": 50,
    "unrestricted_window": { "start_hour": 0, "end_hour": 3 },
    "provider": {
      "url": "http://localhost:20128/api/session",   // PLACEHOLDER — confirm real endpoint
      "method": "GET",
      "headers": { "Authorization": "Bearer <dashboard-token>" }, // PLACEHOLDER
      "json_path": "usage_percent",                   // PLACEHOLDER — confirm real field
      "timeout": 10
    }
  }
}
```

Absent block → monitor disabled. Present block with missing values → defaults applied per
Requirement 8.3; an unconfigured provider yields `RetrievalError` (fail-safe in the restricted
window).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties serve
as the bridge between human-readable specifications and machine-verifiable correctness
guarantees.*

These properties target the **pure decision core** (`evaluate_capacity`), the **config/factory
logic** (`from_config`, `MonitorConfig`), the **usage validation**, and the **existing ID-based
resume logic**. The unconfirmed HTTP provider is intentionally excluded from property tests
(see Testing Strategy) because its behavior does not vary meaningfully with input and depends on
an endpoint that is not yet confirmed.

Reasoning from the prework: several criteria were consolidated to remove redundancy. R6.2
(continue on retrieval failure in the unrestricted window) is subsumed by the unrestricted-window
property whose generator includes `RetrievalError`. R4.1/R4.2/R8.1 collapse into one
threshold-boundary property quantified over the configured threshold. R3.1/R3.2/R8.2 collapse
into one window property quantified over the configured interval. R1.1/R1.2 form one activation
property. R2.2/R2.3 form one validation property, and the restricted-window abnormal-usage cases
(R2.3 + R6.1) form one fail-safe-stop property.

### Property 1: Activation scope is exactly the Target_Judge

*For any* judge identifier, a monitor built with a present `session_monitor` config is enabled
if and only if that identifier equals the configured `target_judge`; and *for any* non-target
judge the monitor is disabled, its `should_continue` always returns CONTINUE, and it never
invokes the usage provider.

**Validates: Requirements 1.1, 1.2**

### Property 2: Unrestricted window always continues without retrieval

*For any* configured unrestricted window `[start_hour, end_hour)`, *for any* local time inside
that window, and *for any* `UsageResult` (including `Ok`, `Invalid`, and `RetrievalError`), the
decision is CONTINUE and the usage provider is not invoked.

**Validates: Requirements 3.1, 3.2, 6.2, 8.2**

### Property 3: Restricted-window threshold boundary

*For any* configured `threshold_percent` T, *for any* local time outside the unrestricted
window, and *for any* validly retrieved usage value v (`Ok(v)`), the decision is CONTINUE if and
only if v < T (equivalently, the run stops exactly when v >= T).

**Validates: Requirements 4.1, 4.2, 8.1**

### Property 4: Usage value range validation

*For any* retrieved numeric value v, the validator classifies it as `Ok(v)` if and only if
0 <= v <= 100 (boundaries 0 and 100 inclusive), and classifies every other value (out of range
or unparseable) as `Invalid`.

**Validates: Requirements 2.2, 2.3**

### Property 5: Restricted-window fail-safe stop on abnormal usage

*For any* local time outside the unrestricted window, if the usage result is `RetrievalError`
or `Invalid`, the decision is STOP and the decision's reason identifies the retrieval/validation
failure.

**Validates: Requirements 6.1, 2.3**

### Property 6: Stop messages contain required information

*For any* stop caused by reaching the threshold, the emitted message contains both the observed
usage percentage and the configured threshold; and *for any* graceful stop, the emitted message
contains both the number of completed interactions and the output file path.

**Validates: Requirements 7.1, 7.2**

### Property 7: Resume processes exactly the un-judged interactions

*For any* set of interaction ids and *for any* subset of them already present in the output
file, a resumed run's todo list equals exactly the complement of the already-present subset —
no already-judged interaction is reprocessed and no un-judged interaction is omitted.

**Validates: Requirements 5.3**

## Error Handling

The monitor is designed to **fail safe**: a monitoring failure must never silently consume the
shared session during working hours, and must never block a legitimate off-peak run.

| Situation | Window | Behavior | Reason code |
|-----------|--------|----------|-------------|
| Provider raises (network/timeout/HTTP/auth) | Restricted | Graceful stop + report failure (R6.1) | `retrieval_error_restricted` |
| Provider raises | Unrestricted | Continue; provider not even called (R3.2, R6.2) | `unrestricted_window` |
| Value out of `[0,100]` or unparseable | Restricted | Treat as invalid → graceful stop (R2.3, R6.1) | `invalid_value_restricted` |
| Provider unconfigured (`url`/`json_path` unset) | Restricted | Returns `RetrievalError` → graceful stop | `retrieval_error_restricted` |
| Provider unconfigured | Unrestricted | Continue (not called) | `unrestricted_window` |
| Malformed `session_monitor` config | n/a | Log a warning, apply defaults per R8.3; if `target_judge` mismatch, monitor stays disabled | `disabled` |

Additional handling rules:
- **Graceful stop is always at a batch boundary.** The generator's existing per-batch
  `save_to_jsonl(...)` runs before the next `should_continue` check, so completed judgments are
  on disk before any stop (R5.1, R5.2).
- **Provider exceptions are caught inside the provider** and converted to `RetrievalError`; the
  monitor and generators never see a raw exception, so a monitoring bug cannot crash an
  evaluation run.
- **Clock/timezone:** the monitor uses the local system time (`datetime.now()`), matching the
  requirements' stated assumption. The window comparison uses the hour-of-day only.
- **Unconfirmed endpoint:** because the real usage endpoint is not yet confirmed, the default
  config ships with placeholder provider values. Operators must fill in the confirmed
  `url`/`headers`/`json_path`; until then, restricted-window runs fail safe (stop) and
  unrestricted-window runs proceed.

## Testing Strategy

### Why property-based testing applies here

The feature's core is a **pure decision function** (`evaluate_capacity`) plus small pure helpers
(usage validation, window membership, config parsing, ID-based resume). These have large input
spaces (arbitrary times, usage values, thresholds, window intervals, id sets) and clear
universal rules, which is exactly where property-based testing earns its keep. The HTTP
retrieval layer is the opposite — it talks to an external, not-yet-confirmed service and does
not vary meaningfully with generated input — so it is covered by mock-based and integration
tests, not properties.

### Property-based tests

- Library: **Hypothesis** (Python).
- Each of Properties 1–7 is implemented by a **single** property-based test.
- Each property test runs a **minimum of 100 iterations** (`@settings(max_examples=100)` or
  higher).
- Each test is tagged with a comment referencing the design property, in the format:
  **Feature: session-capacity-auto-stop, Property {number}: {property_text}**
- Generators must deliberately include edge cases: usage values at exactly 0, 100, and the
  threshold; times at the window boundaries (`start_hour`, `end_hour`, and `end_hour - 1`);
  empty and full id sets; and a `UsageResult` strategy that yields `Ok`, `Invalid`, and
  `RetrievalError` so window properties (P2) also exercise the error paths.
- The usage provider is replaced by an in-memory fake/spy in all property tests so the pure
  logic is tested in isolation and call-count assertions (P1, P2) are possible.

### Unit / example tests

- **R1.3** — both `generate_judgments.py` and `generate_wai_judgments.py` build the monitor via
  the same `from_config` factory and call `should_continue` before submitting a batch.
- **R2.1** — with an enabled monitor in the restricted window, the provider is queried once per
  batch, before submission (spy-based call-order assertion).
- **R5.1 / R5.2** — integration test using a fake monitor that returns STOP after *N* batches;
  assert (a) the judge model is not invoked for batch *N+1*, and (b) the output file contains
  exactly the judgments completed in batches 1..*N*.
- **R8.3** — config parsing: absent/empty `session_monitor` block yields the defaults
  (threshold 50, window 00:00–03:00) and a disabled monitor when the judge is not the target.
- **Disabled-monitor no-op** — for a non-target judge, an end-to-end small run produces output
  byte-identical to a run with the monitor module absent (guards the non-invasiveness
  constraint).

### Integration / smoke tests (HTTP provider — unconfirmed endpoint)

- Mock-based provider tests: given a stubbed HTTP response body, assert `json_path` extraction
  and the `Ok` / `Invalid` / `RetrievalError` mapping (covers timeouts, non-200, auth failure,
  and out-of-range payloads).
- A single **smoke test** (skipped by default / opt-in) that, once the real endpoint is
  confirmed, hits `http://localhost:20128` and asserts a parseable percentage is returned. This
  is the wiring-confirmation test for the currently-unknown endpoint and is explicitly *not* a
  property test.

### Regression guard for non-invasiveness

A test asserts that when no `session_monitor` config is present (or the judge is not
`claude_9router`), neither generator performs any HTTP call and the existing batch loop,
`skip_existing` resume, and output schema are unchanged.
