# Implementation Plan: WAI Parallel Evaluation

## Overview

This plan parallelizes the WAI Sync_Path and wires the `--max_workers` / `--batch_delay`
CLI flags through to the WAI_Runner, mirroring the chunked-parallel pattern already used by the
Mind-Eval Reference_Runner. Work proceeds in four code areas, smallest-blast-radius first:

1. Factor the WAI aggregation and batch-response parsing into shared pure helpers in
   `mindeval/wai/wai_evaluator.py` (no behavior change) so the new parallel path and the existing
   batch path share one implementation.
2. Forward `max_workers` / `batch_delay` from `evaluate.py` (`run_wai` + `main()`).
3. Add the two parameters and pre-path validation to `generate_wai_judgments.main()`.
4. Rewrite the Sync_Path into the Work_Unit chunked-parallel pipeline, then wire it shut with
   property/example/integration tests.

Each step builds on the previous one and ends integrated — no orphaned code. The
Anthropic_Batch_Path is left unchanged throughout.

Property-based tests use **Hypothesis** (min 100 iterations each, `@settings(max_examples=100)`),
substitute a `FakeInferenceEngine` for the real engine, and are each tagged with a comment
`# Feature: wai-parallel-evaluation, Property {n}: ...`.

## Tasks

- [x] 1. Factor shared pure helpers in `mindeval/wai/wai_evaluator.py`
  - [x] 1.1 Add `_aggregate_runs(all_run_results, n_runs)` pure helper
    - Add a module-level function next to `QUESTIONS` / `DIMENSIONS` that takes a list of completed
      run dicts (`{qid -> {evidence, analysis, score}}`) plus `n_runs` and returns
      `{n_runs, questions, dimensions, total}` using the exact existing math: per-question score =
      mean of available run scores (None if none), per-dimension score = mean of available
      constituent question scores, total = mean of available dimension scores
    - Each `questions[qid]` entry must contain `qid`, `question`, `score`, `individual_scores`,
      `runs` exactly as `evaluate_dialogue_batch` produces today
    - _Requirements: 5.1, 5.2, 5.3, 9.2_

  - [x] 1.2 Add `parse_batch_response(raw)` pure helper
    - Extract the JSON-array search / `json.loads` / 12-item + qid + score-range validation logic
      currently inside `call_llm_batch` into a standalone function `parse_batch_response(raw) ->
      dict[str, dict] | None` that performs no LLM call
    - Return the `{qid -> {evidence, analysis, score}}` mapping on success; signal failure (return
      `None` or raise, consumed consistently by callers) so a failed run contributes no scores
    - _Requirements: 5.1_

  - [x] 1.3 Refactor `evaluate_dialogue_batch` and `call_llm_batch` to use the new helpers
    - `call_llm_batch` issues the LLM call then delegates parsing to `parse_batch_response`
    - `evaluate_dialogue_batch` delegates aggregation to `_aggregate_runs`
    - Behavior must be byte-for-byte equivalent to the current implementation (pure refactor)
    - _Requirements: 5.1, 5.2, 5.3, 9.2_

  - [ ]* 1.4 Write aggregation-parity unit test
    - For a fixed known set of run dicts, assert `_aggregate_runs` returns a structure identical to
      the pre-refactor `evaluate_dialogue_batch` output (per-question means, per-dimension means,
      total, and exact field set), guarding the refactor
    - **Validates: Requirements 5.1, 5.2, 5.3 (Property 3 field-set spot check)**

- [x] 2. Forward parallelism flags through the CLI (`evaluate.py`)
  - [x] 2.1 Add `max_workers` / `batch_delay` params to `run_wai` and forward as subprocess args
    - Add `max_workers: int = 5` and `batch_delay: float = 0.0` to `run_wai`'s signature
    - Always append `--max_workers <value>` to the command (keeps CLI default and runner default
      aligned at 5); append `--batch_delay <value>` only when `batch_delay > 0`, mirroring
      `run_mind_eval`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.2 Pass `args.max_workers` / `args.batch_delay` in `main()`'s WAI dispatch branch
    - In the `if args.eval in ("wai", "both")` branch, forward `max_workers=args.max_workers` and
      `batch_delay=args.batch_delay` into the `run_wai(...)` call (no new argparse flags — both
      already exist)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 2.3 Write CLI forwarding example tests
    - Patch `subprocess.run`; assert `--max_workers` is always present with the expected value and
      that `--batch_delay` appears iff `> 0`; assert the defaults (5, 0) are forwarded when the CLI
      omits the flags
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 2.4_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Add parallelism parameters and validation to the WAI runner `main()`
  - [x] 4.1 Add `max_workers` / `batch_delay` parameters and pre-path validation
    - Add `max_workers: int = 5` and `batch_delay: float = 0.0` to
      `generate_wai_judgments.main()`'s signature (backward-compatible defaults)
    - Before path selection (before any LLM call or file write, on both paths): if `max_workers < 1`
      print an error naming the value and `sys.exit(1)`; if `batch_delay < 0` print an error naming
      the value and `sys.exit(1)`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 4.2 Write property test for invalid parameters
    - **Property 7: Invalid parallelism parameters cause a non-zero exit**
    - Hypothesis-generate `max_workers < 1` or `batch_delay < 0`; assert `SystemExit` with non-zero
      code and that no new Judgment_Record is written to the output file; assert the message names
      the offending parameter
    - **Validates: Requirements 2.5, 2.6**

- [x] 5. Rewrite the Sync_Path into the Work_Unit chunked-parallel pipeline
  - [x] 5.1 Build per-dialogue prompts, flatten Work_Units, and group into Batches
    - In the `else` (non-Anthropic) branch of `main()`, replace the
      `for pkg in tqdm(records_to_process)` loop opening with: build one `build_prompt_batch` prompt
      per dialogue; flatten into parallel lists `work_messages` / `work_owner` of `(dialogue_idx,
      run_idx)` for every `(dialogue, run)` combination; compute Batches as contiguous slices of at
      most `max_workers` Work_Units
    - Keep `wai_batch=False` (per-question mode) on the existing per-dialogue path (out of scope)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 5.2 Build the shared property-test harness (`tests/_wai_fakes.py`)
    - Implement `FakeInferenceEngine` whose `batch_generate(list_of_messages)` returns one
      deterministic JSON-array string per input, derived from a seeded score table keyed by
      `(dialogue, run)`, and can be configured to raise or return garbage for specific dialogues to
      exercise error isolation; add a simple sequential reference aggregator for model-based checks
    - _Requirements: 5.1, 8.1_

  - [ ]* 5.3 Write property test for Work_Unit partition
    - **Property 2: Work_Unit partition covers every (dialogue, run) exactly once**
    - For random `D`, `n_runs`, `max_workers`, collect all Work_Units across all Batches; assert the
      multiset equals the full `(d, r)` grid (none omitted/duplicated) and every Batch size
      `<= max_workers`
    - **Validates: Requirements 3.1, 3.2, 3.4**

  - [x] 5.4 Dispatch Batches with monitor gating, fan-in, finalize-once, delay, and error isolation
    - For each Batch: query `monitor.should_continue(completed_count, output_path)` first and break
      on a stop decision (printing `decision.message`, keeping saved records); dispatch the Batch's
      `work_messages` via a single `inference_engine.batch_generate(...)` call; parse each returned
      string with `parse_batch_response` and scatter results back to the owning dialogue via
      `work_owner`; when a dialogue has received all `n_runs` results, aggregate via
      `_aggregate_runs`, attach `interaction_id` / `judge_name` / `judge_model`, append it to the
      output file exactly once, and mark it done; on a per-dialogue finalize error, append the
      existing-shape error record (empty `questions`, null dimensions/total, `error`) and continue;
      sleep `batch_delay` between non-final Batches only when `batch_delay > 0`
    - _Requirements: 3.2, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1, 8.2, 9.2_

  - [ ]* 5.5 Write property test for aggregation independence
    - **Property 1: Aggregation is independent of max_workers**
    - Generate random dialogues/scores/`n_runs`; run the pipeline for several `max_workers` values
      (1, 2, large) and assert identical aggregated records, compared against the sequential
      reference aggregator (model-based)
    - **Validates: Requirements 3.1, 3.3, 5.1, 5.2**

  - [ ]* 5.6 Write property test for output record field set
    - **Property 3: Output record field set is preserved**
    - For random successful dialogues, assert each record's key set is exactly `{n_runs, questions,
      dimensions, total, interaction_id, judge_name, judge_model}` and each `questions[qid]` entry's
      keys are exactly `{qid, question, score, individual_scores, runs}`
    - **Validates: Requirements 5.3, 9.2**

  - [ ]* 5.7 Write property test for interaction_id mapping
    - **Property 4: Each record carries its source dialogue's interaction_id**
    - For random dialogues with distinct `interaction_id`s, assert each aggregated record's
      `interaction_id` matches the dialogue it was derived from
    - **Validates: Requirements 5.4**

  - [ ]* 5.8 Write property test for inter-batch delay count
    - **Property 5: Inter-batch delay applies only between non-final batches**
    - Patch `time.sleep` with a counter; for random batch counts `B` and `batch_delay` in `{0, >0}`,
      assert the pause count equals `B - 1` when `batch_delay > 0` and `0` when `batch_delay == 0`,
      with no pause after the final Batch
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]* 5.9 Write property test for save-once-when-complete
    - **Property 6: A dialogue is saved exactly once, only when all its runs complete**
    - Instrument the append; over random schedules assert each dialogue is appended at most once and
      only after all `n_runs` of its Work_Units have been processed (or it errored)
    - **Validates: Requirements 6.1, 8.1**

  - [ ]* 5.10 Write property test for per-dialogue error isolation
    - **Property 8: Per-dialogue error isolation**
    - Configure a random subset of dialogues to fail; assert one error record (null/empty scores +
      `error` field) per failed dialogue, a normal record per success, and total output record count
      equal to the number of processed dialogues
    - **Validates: Requirements 8.1, 8.2**

  - [ ]* 5.11 Write `max_workers == 1` example test
    - Confirm each Batch holds exactly one Work_Unit and the output equals the sequential baseline
    - _Requirements: 3.3_

  - [ ]* 5.12 Write Anthropic-path-untouched example test
    - With `use_anthropic_batch=True`, assert the runner takes the Anthropic_Batch_Path and never
      applies Sync_Path batching (no `max_workers` grouping, no inter-batch `time.sleep`) and that
      the output schema is unchanged
    - _Requirements: 9.1, 9.2_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Integration / wiring
  - [ ]* 7.1 Write end-to-end smoke test
    - Drive `evaluate.py` → `run_wai` → `generate_wai_judgments.main` on a tiny fixture dataset
      (`--max_dialogues 2`, `--max_workers 2`, `--batch_delay 0`) with a fake/cheap judge; assert an
      output JSONL of valid Judgment_Records is produced and the flags flow through. Not run at PBT
      scale
    - _Requirements: 1.1, 1.2, 3.1, 6.1_

## Notes

- Tasks marked with `*` are optional (tests/harness) and can be skipped for a faster MVP.
- The Anthropic_Batch_Path block in `generate_wai_judgments.py` is left unchanged in every task.
- `_aggregate_runs` and `parse_batch_response` are the single shared implementations that guarantee
  result equivalence (Requirement 5) between the parallel Sync_Path and the existing batch path.
- Each property test references its design property number and the requirements clause it validates.
- Checkpoints provide incremental validation between code areas.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "4.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "5.1"] },
    { "id": 2, "tasks": ["1.3", "5.4", "2.3", "4.2", "5.2"] },
    { "id": 3, "tasks": ["1.4", "5.3", "5.5", "5.6", "5.7", "5.8", "5.9", "5.10", "5.11", "5.12"] },
    { "id": 4, "tasks": ["7.1"] }
  ]
}
```
