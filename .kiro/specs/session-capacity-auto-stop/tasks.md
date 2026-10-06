# Implementation Plan: Session Capacity Auto-Stop

## Overview

This plan implements the Session Capacity Monitor as a **non-invasive add-on** to the existing
Mind-Eval and WAI judgment generators. The work is split into a **pure decision core**
(`evaluate_capacity` plus small pure helpers in a new `mindeval/session_monitor.py`), a
**config-driven factory** (`from_config` / `MonitorConfig`), a **pluggable HTTP provider**
(`HttpSessionUsageProvider`), and a **minimal guarded hook** added to each generator's chunked
batch loop. The existing evaluation logic (prompt building, batching, parsing, incremental save,
`skip_existing` resume, output format) is left untouched.

Property-based tests (Hypothesis) cover the pure core for Properties 1–7. Example/integration
tests cover the wiring, and a regression guard locks in the non-invasiveness constraint.

Language: **Python** (matches the existing codebase and the design's code examples).

## Tasks

- [x] 1. Create `mindeval/session_monitor.py` module with core data models
  - [x] 1.1 Create the new module and data models
    - Create the new module file `mindeval/session_monitor.py` (does not touch any existing module)
    - Define `MonitorConfig` (frozen dataclass) with fields and defaults: `target_judge="claude_9router"`, `threshold_percent=50.0`, `unrestricted_start_hour=0`, `unrestricted_end_hour=3`, `provider_url=None`, `provider_method="GET"`, `provider_headers={}`, `provider_json_path=None`, `provider_timeout=10.0`
    - Define the `UsageResult` tagged union: `Ok(value: float)`, `Invalid(raw: object)`, `RetrievalError(detail: str)`
    - Define `CapacityDecision` NamedTuple: `should_continue: bool`, `reason: str`, `usage_percentage: float | None`, `message: str | None`
    - Create the test module `tests/test_session_monitor.py` and add Hypothesis to the dev/test setup if not already present
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Implement pure usage validation and window-membership helpers
  - [x] 2.1 Implement `validate_usage(raw) -> UsageResult` in `mindeval/session_monitor.py`
    - Parse a numeric value; return `Ok(v)` iff `0 <= v <= 100` (inclusive), else `Invalid(raw)`
    - Treat unparseable / out-of-range values as `Invalid`
    - _Requirements: 2.2, 2.3_

  - [x]* 2.2 Write property test for usage validation
    - **Property 4: Usage value range validation**
    - **Validates: Requirements 2.2, 2.3**
    - Use `@settings(max_examples=100)`; deliberately include the boundaries 0 and 100, out-of-range values, and non-numeric inputs
    - Tag: `# Feature: session-capacity-auto-stop, Property 4`

  - [x] 2.3 Implement `in_unrestricted_window(now, config) -> bool` helper in `mindeval/session_monitor.py`
    - Compare hour-of-day against `[start_hour, end_hour)` (start inclusive, end exclusive)
    - _Requirements: 3.1, 3.2, 8.2_

- [x] 3. Implement the pure decision core `evaluate_capacity`
  - [x] 3.1 Implement `evaluate_capacity(*, now, config, usage) -> CapacityDecision` in `mindeval/session_monitor.py`
    - Unrestricted window → CONTINUE with reason `unrestricted_window`, never inspecting `usage`
    - Restricted window + `Ok(v)` and `v < threshold` → CONTINUE (`below_threshold`)
    - Restricted window + `Ok(v)` and `v >= threshold` → STOP (`at_or_above_threshold`)
    - Restricted window + `RetrievalError` → STOP (`retrieval_error_restricted`)
    - Restricted window + `Invalid` → STOP (`invalid_value_restricted`)
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 6.1, 6.2, 2.3_

  - [x]* 3.2 Write property test for the unrestricted window
    - **Property 2: Unrestricted window always continues without retrieval**
    - **Validates: Requirements 3.1, 3.2, 6.2, 8.2**
    - Generate arbitrary windows, times inside the window, and a `UsageResult` strategy yielding `Ok`/`Invalid`/`RetrievalError`; assert CONTINUE in all cases
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 2`

  - [x]* 3.3 Write property test for the restricted-window threshold boundary
    - **Property 3: Restricted-window threshold boundary**
    - **Validates: Requirements 4.1, 4.2, 8.1**
    - For arbitrary threshold T, times outside the window, and `Ok(v)`: CONTINUE iff `v < T`; include v exactly at T, 0, and 100
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 3`

  - [x]* 3.4 Write property test for the restricted-window fail-safe stop
    - **Property 5: Restricted-window fail-safe stop on abnormal usage**
    - **Validates: Requirements 6.1, 2.3**
    - For times outside the window with `RetrievalError` or `Invalid`: assert STOP and that the reason identifies the retrieval/validation failure
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 5`

- [x] 4. Implement the config factory, `SessionCapacityMonitor`, and stop messages
  - [x] 4.1 Implement `MonitorConfig` parsing and `SessionCapacityMonitor.from_config(judge_name, config_path)`
    - Parse the optional `session_monitor` block from config.json; apply defaults for missing values (threshold 50, window 00:00–03:00)
    - Return an **enabled** monitor only when `judge_name == target_judge` AND a `session_monitor` block is present; otherwise a **disabled** no-op monitor whose `should_continue` always returns CONTINUE and never calls the provider
    - On malformed config, log a warning and fall back to defaults; mismatched `target_judge` keeps the monitor disabled
    - Expose the `enabled` property
    - _Requirements: 1.1, 1.2, 8.1, 8.2, 8.3_

  - [x]* 4.2 Write property test for activation scope
    - **Property 1: Activation scope is exactly the Target_Judge**
    - **Validates: Requirements 1.1, 1.2**
    - For arbitrary judge identifiers with a present config: enabled iff identifier == `target_judge`; for non-target judges assert `should_continue` returns CONTINUE and the provider (spy) is never invoked
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 1`

  - [x] 4.3 Implement `should_continue(completed_count, output_path)` with message formatting
    - Disabled monitor → CONTINUE immediately (no time check, no provider call)
    - Enabled monitor → get `now`; in the restricted window query the provider once and `validate_usage`; in the unrestricted window skip retrieval; delegate the verdict to `evaluate_capacity`
    - On threshold stop, format a message including the observed usage percentage and the configured threshold; on any graceful stop, format a message including `completed_count` and `output_path`
    - _Requirements: 2.1, 5.2, 7.1, 7.2_

  - [x]* 4.4 Write property test for stop messages
    - **Property 6: Stop messages contain required information**
    - **Validates: Requirements 7.1, 7.2**
    - Threshold-stop message contains both usage and threshold; graceful-stop message contains both completed count and output path
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 6`

- [x] 5. Checkpoint - pure core and factory complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement the pluggable HTTP usage provider
  - [x] 6.1 Implement `SessionUsageProvider` protocol and `HttpSessionUsageProvider` in `mindeval/session_monitor.py`
    - `get_usage_percentage() -> UsageResult`; config-driven `url`, `method`, `headers`, `json_path`, `timeout`
    - Extract the percentage via a simple dotted `json_path`, then route through `validate_usage`
    - Catch all network/HTTP/timeout/auth exceptions inside the provider and convert to `RetrievalError` (never propagate raw exceptions)
    - If `url` or `json_path` is unset (unconfigured), return `RetrievalError` (fail-safe stop in the restricted window)
    - _Requirements: 2.1, 2.2, 2.3, 6.1_

  - [x]* 6.2 Write mock-based provider tests in `tests/test_session_provider.py`
    - Stub HTTP responses; assert `json_path` extraction and the `Ok` / `Invalid` / `RetrievalError` mapping for non-200, timeout, auth failure, out-of-range payload, and unconfigured provider
    - _Requirements: 2.1, 2.2, 2.3, 6.1_

  - [x]* 6.3 Write an opt-in smoke test in `tests/test_session_provider.py`
    - Skipped by default; once the real dashboard endpoint is confirmed, hits `http://localhost:20128` and asserts a parseable percentage is returned (wiring-confirmation test, not a property test)
    - _Requirements: 2.1_

- [x] 7. Wire the monitor into `generate_judgments.py` (minimal guarded hook)
  - [x] 7.1 Add the pre-batch capacity hook to the chunked sync path
    - Build the monitor once via `SessionCapacityMonitor.from_config(judge_name, config_path)` (new optional params default to monitor-off)
    - Inside the existing chunked loop, immediately before `judge_model.batch_generate_with_thinking(batch_messages)`, call `monitor.should_continue(completed_count=len(accumulated_outputs), output_path=output_path)`; on STOP `print(decision.message)` and `break` (completed judgments are already saved each batch). Leave the Anthropic-batch path untouched.
    - _Requirements: 1.3, 2.1, 5.1, 5.2_

  - [x]* 7.2 Write integration test for `generate_judgments.py` stop behavior
    - Use a fake monitor that returns STOP after N batches; assert the judge model is not invoked for batch N+1 and the output file contains exactly the judgments from batches 1..N
    - _Requirements: 5.1, 5.2_

- [x] 8. Wire the monitor into `generate_wai_judgments.py` (minimal guarded hook)
  - [x] 8.1 Add the same pre-batch capacity hook to the WAI chunked sync path
    - Mirror the `generate_judgments.py` hook at the per-batch boundary of the standard sync path; leave the Anthropic-batch path untouched
    - _Requirements: 1.3, 2.1, 5.1, 5.2_

  - [x]* 8.2 Write integration test for `generate_wai_judgments.py` stop behavior
    - Fake monitor returns STOP after N batches; assert no batch N+1 submission and output contains only batches 1..N
    - _Requirements: 5.1, 5.2_

- [x] 9. Implement and property-test the ID-based resume helper
  - [x] 9.1 Implement `compute_todo_ids(all_ids, existing_ids)` pure helper in `mindeval/session_monitor.py`
    - Returns exactly the complement of `existing_ids` within `all_ids`, mirroring the generators' existing `skip_existing` ID-based resume semantics (no change to existing generator logic)
    - _Requirements: 5.3_

  - [x]* 9.2 Write property test for resume completeness
    - **Property 7: Resume processes exactly the un-judged interactions**
    - **Validates: Requirements 5.3**
    - For arbitrary id sets and arbitrary already-present subsets, the todo list equals exactly the complement; include empty and full subsets
    - `@settings(max_examples=100)`; tag: `# Feature: session-capacity-auto-stop, Property 7`

- [x] 10. Add the optional config block and the non-invasiveness regression guard
  - [x] 10.1 Add an optional `session_monitor` block to `config.example.json`
    - Include `target_judge`, `threshold_percent`, `unrestricted_window` (start_hour/end_hour), and a `provider` sub-block with placeholder `url`/`headers`/`json_path`/`timeout` clearly marked as unconfirmed; document that an absent block disables the monitor
    - _Requirements: 8.1, 8.2, 8.3_

  - [x]* 10.2 Write the non-invasiveness regression guard test in `tests/test_non_invasiveness.py`
    - Assert that with no `session_monitor` config (or a non-`claude_9router` judge) neither generator performs any HTTP call, and the batch loop, `skip_existing` resume, and output schema are unchanged (disabled-monitor no-op produces output identical to the monitor being absent)
    - _Requirements: 1.2, 1.3_

- [x] 11. Final checkpoint - ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; they cover unit,
  property, and integration tests.
- Each task references specific requirements (granular sub-requirement clauses) for traceability.
- Property tests target the pure decision core and helpers; the unconfirmed HTTP provider is
  covered by mock/integration tests, not property tests.
- The provider ships with placeholder `url`/`headers`/`json_path` because the real dashboard
  usage endpoint is not yet confirmed; until it is wired up, restricted-window runs fail safe
  (stop) and unrestricted-window runs proceed.
- Non-invasiveness is enforced structurally (new module + guarded optional hook) and verified by
  the regression guard in task 10.2.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.3", "2.2"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["4.1", "3.2"] },
    { "id": 5, "tasks": ["4.3", "3.3"] },
    { "id": 6, "tasks": ["6.1", "3.4"] },
    { "id": 7, "tasks": ["9.1", "4.2"] },
    { "id": 8, "tasks": ["4.4", "6.2", "7.1"] },
    { "id": 9, "tasks": ["9.2", "6.3", "8.1", "10.1"] },
    { "id": 10, "tasks": ["7.2", "8.2", "10.2"] }
  ]
}
```
