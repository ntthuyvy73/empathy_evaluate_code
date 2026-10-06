# Requirements Document

## Introduction

When running the evaluation commands (`mind_eval` or `wai`) through `evaluate.py` with the
`claude_9router` judge, the run consumes capacity on a shared 9router proxy "session"
(reachable at `http://localhost:20128/v1`). To avoid exhausting that shared session during
normal working hours, this feature adds a Session Capacity Monitor that watches the proxy's
session usage and automatically stops the evaluation once usage reaches a configurable
threshold (default 50%). During an off-peak window (00:00–03:00 local time) the monitor is
disabled so long runs can complete without interruption.

The monitor activates only when the selected judge is `claude_9router`. All other judges
(`gpt`, `claude`, `gemini`, `qwen`, etc.) run exactly as they do today, with no capacity
checks and no behavioral change.

## Glossary

- **Evaluation_Runner**: The `evaluate.py` orchestration layer plus the underlying judgment
  generators (`mindeval.scripts.generate_judgments` for Mind-Eval and
  `mindeval.scripts.generate_wai_judgments` for WAI) that issue judge model calls in batches.
- **Session_Capacity_Monitor**: The new component that queries session usage and decides
  whether the Evaluation_Runner may continue or must stop.
- **Router_Proxy**: The 9router proxy service exposed at `http://localhost:20128/v1` that the
  `claude_9router` judge calls.
- **Session_Usage_Percentage**: A numeric value in the range 0–100 reported by the
  Router_Proxy that represents how much of the current session quota has been consumed.
- **Capacity_Threshold**: The Session_Usage_Percentage value at or above which the monitor
  stops the run during the Restricted_Window. Default value is 50 (percent).
- **Unrestricted_Window**: The local-time interval from 00:00:00 up to (but not including)
  03:00:00, during which the Capacity_Threshold is not enforced.
- **Restricted_Window**: Any local time outside the Unrestricted_Window, during which the
  Capacity_Threshold is enforced.
- **Target_Judge**: The judge identifier that activates the monitor. Default value is
  `claude_9router`.
- **Graceful_Stop**: Terminating the evaluation between work units so that all judgments
  completed before the stop are persisted to the output file and can be resumed later.

## Requirements

### Requirement 1: Monitor activation scope

**User Story:** As a researcher running evaluations, I want the capacity monitor to engage only
for the `claude_9router` judge, so that runs using other judges are completely unaffected.

#### Acceptance Criteria

1. WHEN an evaluation is started with the selected judge equal to the Target_Judge, THE Session_Capacity_Monitor SHALL be enabled for that run.
2. WHEN an evaluation is started with a selected judge other than the Target_Judge, THE Session_Capacity_Monitor SHALL remain disabled and THE Evaluation_Runner SHALL run without any capacity check.
3. THE Session_Capacity_Monitor SHALL apply identically to both the `mind_eval` evaluation and the `wai` evaluation.

### Requirement 2: Query session usage

**User Story:** As a researcher, I want the system to read the current session usage from the
Router_Proxy, so that capacity decisions are based on real usage data.

#### Acceptance Criteria

1. WHILE the Session_Capacity_Monitor is enabled, THE Session_Capacity_Monitor SHALL retrieve the Session_Usage_Percentage from the Router_Proxy before processing each batch of interactions.
2. WHEN the Session_Capacity_Monitor retrieves the Session_Usage_Percentage, THE Session_Capacity_Monitor SHALL interpret the value as a number in the range 0 to 100 inclusive.
3. IF the retrieved Session_Usage_Percentage is outside the range 0 to 100, THEN THE Session_Capacity_Monitor SHALL treat the value as invalid and apply the error-handling behavior defined in Requirement 6.

### Requirement 3: Off-peak unrestricted behavior

**User Story:** As a researcher, I want long evaluation runs to proceed without a capacity limit
between midnight and 3 AM, so that I can complete large jobs during off-peak hours.

#### Acceptance Criteria

1. WHILE the current local time is within the Unrestricted_Window, THE Session_Capacity_Monitor SHALL allow the Evaluation_Runner to continue regardless of the Session_Usage_Percentage.
2. WHILE the current local time is within the Unrestricted_Window, THE Session_Capacity_Monitor SHALL skip retrieval of the Session_Usage_Percentage.

### Requirement 4: Restricted-window capacity enforcement

**User Story:** As a researcher, I want the run to stop automatically when the session is half
used during working hours, so that I do not exhaust the shared session for others.

#### Acceptance Criteria

1. WHILE the current local time is within the Restricted_Window AND the Session_Usage_Percentage is below the Capacity_Threshold, THE Session_Capacity_Monitor SHALL allow the Evaluation_Runner to continue.
2. WHILE the current local time is within the Restricted_Window AND the Session_Usage_Percentage is greater than or equal to the Capacity_Threshold, THE Session_Capacity_Monitor SHALL initiate a Graceful_Stop of the Evaluation_Runner.

### Requirement 5: Graceful stop and progress preservation

**User Story:** As a researcher, I want completed judgments saved when the run stops, so that I
can resume later without losing work.

#### Acceptance Criteria

1. WHEN the Session_Capacity_Monitor initiates a Graceful_Stop, THE Evaluation_Runner SHALL persist all judgments completed before the stop to the output file.
2. WHEN the Session_Capacity_Monitor initiates a Graceful_Stop, THE Evaluation_Runner SHALL stop before submitting the next batch of interactions to the judge model.
3. WHEN a Graceful_Stop has occurred and the evaluation is started again with the same output file, THE Evaluation_Runner SHALL resume by evaluating only interactions that do not yet have judgments.

### Requirement 6: Session retrieval error handling

**User Story:** As a researcher, I want predictable behavior when the session usage cannot be
read, so that a monitoring failure does not silently waste session capacity.

#### Acceptance Criteria

1. IF the Session_Capacity_Monitor cannot retrieve the Session_Usage_Percentage from the Router_Proxy while in the Restricted_Window, THEN THE Session_Capacity_Monitor SHALL initiate a Graceful_Stop and report the retrieval failure.
2. IF the Session_Capacity_Monitor cannot retrieve the Session_Usage_Percentage from the Router_Proxy while in the Unrestricted_Window, THEN THE Session_Capacity_Monitor SHALL allow the Evaluation_Runner to continue.

### Requirement 7: User feedback on stop

**User Story:** As a researcher, I want a clear message when a run stops due to capacity, so that
I understand why the run ended and how much was completed.

#### Acceptance Criteria

1. WHEN the Session_Capacity_Monitor initiates a Graceful_Stop due to reaching the Capacity_Threshold, THE Session_Capacity_Monitor SHALL emit a message stating the observed Session_Usage_Percentage and the Capacity_Threshold.
2. WHEN the Session_Capacity_Monitor initiates a Graceful_Stop, THE Session_Capacity_Monitor SHALL emit a message stating the number of interactions completed and the output file path.

### Requirement 8: Configurable threshold and window

**User Story:** As a researcher, I want to adjust the threshold and the off-peak window, so that
I can tune the behavior without changing code.

#### Acceptance Criteria

1. WHERE a Capacity_Threshold value is provided in configuration, THE Session_Capacity_Monitor SHALL enforce that value instead of the default value of 50.
2. WHERE an Unrestricted_Window start hour and end hour are provided in configuration, THE Session_Capacity_Monitor SHALL use the provided interval instead of the default interval of 00:00 to 03:00.
3. WHERE no Capacity_Threshold or Unrestricted_Window configuration is provided, THE Session_Capacity_Monitor SHALL use the default Capacity_Threshold of 50 and the default Unrestricted_Window of 00:00 to 03:00 local time.

## Open Questions / Assumptions

These items need confirmation and may change the requirements above:

1. **Source of Session_Usage_Percentage (Requirement 2):** The exact Router_Proxy
   API/endpoint that reports session usage is unknown. The requirements assume the proxy at
   `http://localhost:20128` exposes a queryable usage value. Need: endpoint path, request
   method, auth, and response shape.
2. **Timezone (Requirement 3):** Assumed to be the local system time of the machine running
   `evaluate.py`. Confirm whether a fixed timezone should be used instead.
3. **Stop semantics (Requirement 5):** Assumed to be a Graceful_Stop at batch boundaries that
   preserves completed judgments. Confirm this is preferred over an immediate hard stop.
4. **Activation scope (Requirement 1):** Assumed to apply only to `claude_9router`. Confirm
   whether other 9router judges (e.g., `gpt_9router`) that share the same proxy should also be
   monitored.
5. **Check frequency (Requirement 2):** Assumed to be once per batch. Confirm whether a
   time-based interval or per-dialogue check is preferred.
