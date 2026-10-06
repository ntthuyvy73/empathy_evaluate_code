# Requirements Document

## Introduction

The WAI (Working Alliance Inventory) evaluation path is currently fully sequential. For each
dialogue, the WAI runner iterates over `n_runs` (default 3) LLM calls one after another, and the
outer loop over dialogues is also serial — every call sends a single-element message list to the
inference engine. As a result, WAI evaluation is slow on large datasets.

Separately, the unified evaluation CLI (`evaluate.py`) already exposes `--max_workers` (default 5)
and `--batch_delay` (default 0.0) flags, but they have **no effect** on WAI. The CLI's `run_wai`
helper neither accepts nor forwards these flags, and the WAI runner script does not define them. A
command such as `python evaluate.py --eval wai --max_worker 1 --batch_delay 3` silently ignores
both flags for WAI, while the Mind-Eval path already honors them.

This feature wires `max_workers` and `batch_delay` through to the WAI path and parallelizes WAI
evaluation, mirroring the chunked-parallel pattern already implemented in the Mind-Eval runner
(`generate_judgments.py`): work is split into batches of at most `max_workers` units, each batch is
dispatched to the inference engine in a single concurrent call, results are saved after every
batch, and an optional `batch_delay` pause is inserted between batches.

The change must preserve all existing WAI behaviors: incremental save and resume via
`skip_existing`, session capacity monitor gating, per-dialogue and per-dimension aggregation
correctness, the separate Anthropic-batch path, and the output record schema. Defaults must keep
behavior backward compatible (`batch_delay` of 0 means no pause).

## Glossary

- **Evaluation_CLI**: The `evaluate.py` command-line entry point that dispatches Mind-Eval and/or
  WAI evaluation as subprocesses via `run_mind_eval` and `run_wai`.
- **WAI_Runner**: The WAI judgment generation process
  (`mindeval.scripts.generate_wai_judgments.main`) that evaluates dialogues against the 12 WAI
  questions and writes judgments to the output file.
- **Reference_Runner**: The Mind-Eval runner (`mindeval.scripts.generate_judgments.main`) whose
  chunked-parallel batching, incremental save, inter-batch delay, and monitor gating serve as the
  design reference for the WAI_Runner.
- **Sync_Path**: The standard per-dialogue synchronous code path in the WAI_Runner used when the
  judge is not configured for the Anthropic Batch API.
- **Anthropic_Batch_Path**: The existing code path in the WAI_Runner, selected by the judge config
  flag `use_anthropic_batch`, that submits all requests through the Anthropic Message Batches API.
- **Work_Unit**: A single unit of LLM work in the Sync_Path. One Work_Unit corresponds to one batch
  WAI call producing the 12-question result for one run of one dialogue.
- **Batch**: A group of up to `max_workers` Work_Units dispatched together to the Inference_Engine
  in a single concurrent call.
- **max_workers**: A positive integer controlling the maximum number of Work_Units the WAI_Runner
  dispatches concurrently in one Batch.
- **batch_delay**: A non-negative number of seconds the WAI_Runner pauses between consecutive
  Batches.
- **n_runs**: The number of LLM calls per dialogue used for score averaging (default 3, per
  Li et al. 2024).
- **Judgment_Record**: One output record for one dialogue, containing per-question scores
  (`questions`), per-dimension scores (`dimensions`), the `total` score, the run count (`n_runs`),
  and identifying metadata (`interaction_id`, `judge_name`, `judge_model`).
- **skip_existing**: The resume mechanism that omits dialogues whose `interaction_id` already
  appears in the output file.
- **Session_Monitor**: The `SessionCapacityMonitor` add-on that decides, before scheduled work,
  whether evaluation should continue or stop based on remaining shared session capacity.
- **Inference_Engine**: The `InferenceEngine` whose `batch_generate` method accepts a list of
  message lists and processes them concurrently via `litellm.batch_completion`.

## Requirements

### Requirement 1: Forward parallelism flags from the CLI to the WAI runner

**User Story:** As a researcher running WAI evaluation, I want the `--max_workers` and
`--batch_delay` flags on `evaluate.py` to apply to the WAI path, so that I can control WAI
parallelism and pacing from the same command I already use.

#### Acceptance Criteria

1. WHEN the Evaluation_CLI runs the WAI path, THE Evaluation_CLI SHALL pass the `max_workers` argument value to the WAI_Runner.
2. WHEN the Evaluation_CLI runs the WAI path, THE Evaluation_CLI SHALL pass the `batch_delay` argument value to the WAI_Runner.
3. WHERE the user does not supply `--max_workers`, THE Evaluation_CLI SHALL forward the default value of 5 to the WAI_Runner.
4. WHERE the user does not supply `--batch_delay`, THE Evaluation_CLI SHALL forward the default value of 0 to the WAI_Runner.

### Requirement 2: WAI runner accepts parallelism parameters

**User Story:** As a developer invoking the WAI runner directly, I want the runner to accept
`max_workers` and `batch_delay` parameters, so that I can control parallel execution without going
through the CLI.

#### Acceptance Criteria

1. THE WAI_Runner SHALL accept a `max_workers` parameter that is a positive integer.
2. THE WAI_Runner SHALL accept a `batch_delay` parameter that is a non-negative number of seconds.
3. WHERE `max_workers` is not supplied, THE WAI_Runner SHALL use a default value of 5.
4. WHERE `batch_delay` is not supplied, THE WAI_Runner SHALL use a default value of 0.
5. IF `max_workers` is less than 1, THEN THE WAI_Runner SHALL terminate with a non-zero exit code and an error message identifying the invalid `max_workers` value.
6. IF `batch_delay` is negative, THEN THE WAI_Runner SHALL terminate with a non-zero exit code and an error message identifying the invalid `batch_delay` value.

### Requirement 3: Parallel execution of WAI work units

**User Story:** As a researcher with large datasets, I want WAI work to run in parallel across
dialogues and runs, so that evaluation completes faster than sequential execution.

#### Acceptance Criteria

1. WHEN the WAI_Runner has more than one Work_Unit to process on the Sync_Path, THE WAI_Runner SHALL group Work_Units into Batches of at most `max_workers` Work_Units each.
2. WHEN the WAI_Runner processes a Batch, THE WAI_Runner SHALL dispatch the Batch's Work_Units to the Inference_Engine in a single concurrent call.
3. WHERE `max_workers` equals 1, THE WAI_Runner SHALL process exactly one Work_Unit per Batch.
4. THE WAI_Runner SHALL produce one Work_Unit for each combination of dialogue and run, so that the `n_runs` calls for a dialogue are eligible to execute concurrently across Batches.

### Requirement 4: Inter-batch delay

**User Story:** As a researcher hitting provider rate limits, I want a configurable pause between
batches, so that I can stay under tokens-per-minute limits.

#### Acceptance Criteria

1. WHERE `batch_delay` is greater than 0, WHEN the WAI_Runner finishes a Batch that is not the final Batch, THE WAI_Runner SHALL pause for `batch_delay` seconds before starting the next Batch.
2. WHERE `batch_delay` equals 0, THE WAI_Runner SHALL start the next Batch without an inter-batch pause.
3. WHEN the WAI_Runner finishes the final Batch, THE WAI_Runner SHALL start no further pause.

### Requirement 5: Result equivalence regardless of parallelism

**User Story:** As a researcher comparing results, I want parallel WAI output to be equivalent to
sequential output, so that enabling parallelism does not change the scientific results.

#### Acceptance Criteria

1. THE WAI_Runner SHALL compute the per-question score for each dialogue as the mean of that question's available run scores, regardless of the `max_workers` value.
2. THE WAI_Runner SHALL compute the per-dimension score for each dialogue as the mean of its constituent question scores, and the total score as the mean of the available dimension scores, regardless of the `max_workers` value.
3. WHERE the same dialogues, judge configuration, and `n_runs` are used, THE WAI_Runner SHALL produce a Judgment_Record for each dialogue whose set of fields is identical to the set produced under sequential execution.
4. THE WAI_Runner SHALL associate each aggregated Judgment_Record with the `interaction_id` of the dialogue from which the result was produced.

### Requirement 6: Incremental save and resume preserved

**User Story:** As a researcher running long jobs, I want completed dialogues saved as work
progresses and re-runs to skip them, so that interrupted runs can resume without recomputation.

#### Acceptance Criteria

1. WHEN all Work_Units for a dialogue have completed, THE WAI_Runner SHALL append that dialogue's Judgment_Record to the output file before the run ends.
2. WHERE `skip_existing` is enabled and the output file already contains a Judgment_Record for a dialogue's `interaction_id`, THE WAI_Runner SHALL exclude that dialogue from processing.
3. WHEN a run is restarted after an interruption, THE WAI_Runner SHALL retain the Judgment_Records that were written before the interruption.

### Requirement 7: Session monitor compatibility

**User Story:** As a researcher using session capacity limits, I want the parallel WAI runner to
respect the session monitor, so that evaluation stops cleanly when capacity is exhausted.

#### Acceptance Criteria

1. WHEN the WAI_Runner is about to process a Batch on the Sync_Path, THE WAI_Runner SHALL query the Session_Monitor for a continue-or-stop decision.
2. IF the Session_Monitor returns a stop decision, THEN THE WAI_Runner SHALL stop scheduling further Batches and print the decision message.
3. WHEN the WAI_Runner stops on a Session_Monitor stop decision, THE WAI_Runner SHALL retain all Judgment_Records written for previously completed dialogues.

### Requirement 8: Per-dialogue error isolation

**User Story:** As a researcher running large batches, I want a failure on one dialogue to not
abort the whole run, so that I still get results for the dialogues that succeed.

#### Acceptance Criteria

1. IF processing a dialogue's Work_Units raises an error, THEN THE WAI_Runner SHALL record a Judgment_Record for that dialogue containing an error indicator and null scores.
2. WHEN a dialogue fails with an error, THE WAI_Runner SHALL continue processing the remaining dialogues.

### Requirement 9: Anthropic batch path and output schema preserved

**User Story:** As a researcher using an Anthropic batch judge, I want the existing Anthropic-batch
WAI path and the output record schema to remain unchanged, so that the parallelism change does not
break existing judges or downstream analysis.

#### Acceptance Criteria

1. WHERE the judge configuration enables `use_anthropic_batch`, THE WAI_Runner SHALL use the Anthropic_Batch_Path and SHALL NOT apply the Sync_Path batching controlled by `max_workers` and `batch_delay`.
2. THE WAI_Runner SHALL write each Judgment_Record with the same field structure (`n_runs`, `questions`, `dimensions`, `total`, `interaction_id`, `judge_name`, `judge_model`) as the current implementation.
