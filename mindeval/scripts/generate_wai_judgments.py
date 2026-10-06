"""
Generate WAI (Working Alliance Inventory) judgments for interactions.

Evaluates therapeutic dialogues using the WAI framework from Li et al. (2024),
"Understanding the Therapeutic Relationship between Counselors and Clients
in Online Text-based Counseling using LLMs" (Findings of EMNLP 2024,
arXiv:2402.11958).

WAI evaluates 3 dimensions of therapeutic alliance:
- Goal           : Agreement on therapy goals      (Q1-Q4)
- Approach       : Agreement on therapy tasks      (Q5-Q8)
- Affective Bond : Emotional connection            (Q9-Q12)

Pipeline: for each dialogue, 12 questions × n_runs LLM calls (default 3).
Total LLM calls per dialogue = 36.

Uses English prompts (S3 setting: original-language dialogue + English judge).

Usage:
    python -m mindeval.scripts.generate_wai_judgments \\
        --interactions_path data/simpsydial/test/interactions_200_canonical.jsonl \\
        --output_path data/simpsydial/results/wai/S3_gpt_wai_judgments.jsonl \\
        --config_path config.json \\
        --n_runs 3 \\
        --max_dialogues 5
"""

from __future__ import annotations

import json
import re
import sys
import time

# Ensure stdout can handle Unicode on Windows (cp1252 would fail on → ✓ etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import statistics
from pathlib import Path
from typing import Optional

from jsonargparse import CLI
from tqdm import tqdm

from mindeval.config import get_judge_config, get_named_judge_config
from mindeval.inference import InferenceEngine
from mindeval.utils import load_jsonl, messages_to_convo_str, save_to_jsonl
from mindeval.wai import evaluate_dialogue
from mindeval.wai.wai_evaluator import (
    build_prompt_batch,
    QUESTIONS,
    DIMENSIONS,
    _JSON_ARRAY_RE,
    _aggregate_runs,
    parse_batch_response,
)


def main(
    interactions_path: str,
    output_path: str,
    config_path: Optional[str] = None,
    judge_name: Optional[str] = None,
    n_runs: int = 3,
    skip_existing: bool = True,
    max_dialogues: Optional[int] = None,
    wai_batch: bool = True,
    max_workers: int = 5,
    batch_delay: float = 0.0,
):
    """
    Generate WAI judgments for interactions (English prompts, S3 setting).

    Args:
        interactions_path : Path to canonical interactions JSONL file.
        output_path       : Path to save WAI judgments JSONL file.
        config_path       : Path to config.json. If None, uses env vars.
        judge_name        : Named judge from config 'judges' section (e.g. 'gpt').
                            Written to each output record as judge_name.
        n_runs            : LLM calls per question (default 3, per Li et al. 2024).
        skip_existing     : Skip interaction_ids already present in output file.
        max_dialogues     : Cap number of dialogues to process (None = all).
        wai_batch         : If True (default), send all 12 questions in one LLM call
                            per run (~70% token savings). Set to False to use
                            per-question mode (12 calls/run) for models that reject
                            long batch prompts (e.g. some Gemini deployments).
        max_workers       : Max Work_Units dispatched concurrently per batch on the
                            sync path (default 5). Must be >= 1.
        batch_delay       : Seconds to pause between consecutive batches on the sync
                            path (default 0.0 = no pause). Must be >= 0.
    """
    # ── Parameter validation (before any LLM call or file write, on both paths) ──
    if max_workers < 1:
        print(f"ERROR: max_workers must be >= 1, got {max_workers}")
        sys.exit(1)
    if batch_delay < 0:
        print(f"ERROR: batch_delay must be >= 0, got {batch_delay}")
        sys.exit(1)

    print(f"Loading interactions from: {interactions_path}")
    all_packages = load_jsonl(interactions_path)
    print(f"Found {len(all_packages)} interactions")

    # ── ID-based skip ──────────────────────────────────────────────────────
    existing_judgments: list[dict] = []
    existing_ids: set[str] = set()
    output_file = Path(output_path)

    if skip_existing and output_file.exists():
        existing_judgments = load_jsonl(output_path)
        for j in existing_judgments:
            iid = j.get("interaction_id")
            if iid:
                existing_ids.add(iid)
        print(f"Loaded {len(existing_judgments)} existing judgments "
              f"({len(existing_ids)} with interaction_id)")

    records_to_process = [
        pkg for pkg in all_packages
        if not (skip_existing and pkg.get("interaction_id") in existing_ids)
    ]

    if max_dialogues is not None and max_dialogues > 0:
        records_to_process = records_to_process[:max_dialogues]

    n_todo = len(records_to_process)
    if n_todo == 0:
        print("✓ All interactions already have judgments. Nothing to do.")
        return
    print(f"Generating judgments for {n_todo} interaction(s) "
          f"(skipped {len(all_packages) - n_todo})")

    # ── Judge setup ────────────────────────────────────────────────────────
    if judge_name and config_path:
        judge_config = get_named_judge_config(judge_name, config_path)
    else:
        judge_config = get_judge_config(config_path)
    judge_model_name = judge_config.get("model", "")
    effective_judge = judge_name or "gpt"

    print(f"\nJudge       : {effective_judge}  ({judge_model_name})")
    print(f"Temperature : {judge_config.get('temperature', 1.0)}")
    print(f"n_runs/Q    : {n_runs}  →  {12 * n_runs} LLM calls per dialogue\n")

    use_anthropic_batch = judge_config.get("use_anthropic_batch", False)
    inference_engine = InferenceEngine(judge_config)

    # ── Evaluation loop ────────────────────────────────────────────────────
    new_judgments: list[dict] = []

    if use_anthropic_batch:
        # ── Anthropic Batch API path (50% token discount) ─────────────────
        # Build all messages: N_dialogues × n_runs in one flat list.
        all_messages: list[list[dict]] = []
        message_index: list[tuple[int, int]] = []  # (dialogue_idx, run_idx)
        convo_strings: list[str] = []

        for d_idx, pkg in enumerate(records_to_process):
            convo_str = messages_to_convo_str(pkg.get("interaction", []))
            convo_strings.append(convo_str)
            prompt = build_prompt_batch(convo_str)
            for r_idx in range(n_runs):
                all_messages.append([{"role": "user", "content": prompt}])
                message_index.append((d_idx, r_idx))

        print(f"[anthropic-batch] Submitting {len(all_messages)} WAI requests "
              f"({len(records_to_process)} dialogues × {n_runs} runs) …")
        raw_responses = inference_engine.batch_generate_all_anthropic(all_messages)

        # Parse responses and group by dialogue
        dialogue_runs: list[list[dict]] = [[] for _ in records_to_process]
        for (d_idx, _r_idx), raw in zip(message_index, raw_responses):
            m = _JSON_ARRAY_RE.search(raw)
            if m is None:
                dialogue_runs[d_idx].append({})
                continue
            try:
                items = json.loads(m.group(0))
                run_result = {
                    item["qid"]: {
                        "evidence": item.get("evidence", ""),
                        "analysis": item.get("analysis", ""),
                        "score":    int(item["score"]),
                    }
                    for item in items
                    if item.get("qid") in QUESTIONS
                }
            except Exception:
                run_result = {}
            dialogue_runs[d_idx].append(run_result)

        # Aggregate per dialogue (same logic as evaluate_dialogue_batch)
        for pkg, runs in zip(records_to_process, dialogue_runs):
            per_q: dict = {}
            for qid in QUESTIONS:
                run_scores = [r[qid]["score"] for r in runs if qid in r]
                per_q[qid] = {
                    "qid":              qid,
                    "question":         QUESTIONS[qid],
                    "score":            statistics.mean(run_scores) if run_scores else None,
                    "individual_scores": run_scores,
                    "runs":             [r.get(qid, {}) for r in runs],
                }
            dim_scores: dict = {}
            for dim, qids in DIMENSIONS.items():
                scs = [per_q[q]["score"] for q in qids if per_q[q]["score"] is not None]
                dim_scores[dim] = statistics.mean(scs) if scs else None
            valid_dims = [v for v in dim_scores.values() if v is not None]
            result = {
                "n_runs":           n_runs,
                "questions":        per_q,
                "dimensions":       dim_scores,
                "total":            statistics.mean(valid_dims) if valid_dims else None,
                "interaction_id":   pkg.get("interaction_id", ""),
                "judge_name":       effective_judge,
                "judge_model":      judge_model_name,
            }
            new_judgments.append(result)

    else:
        # ── Standard sync path ─────────────────────────────────────────────
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Session capacity monitor (non-invasive add-on). Disabled for every
        # judge other than the configured target_judge, in which case
        # `should_continue` always returns CONTINUE and never performs any HTTP
        # call. When enabled, rebuild the monitor with a concrete HTTP usage
        # provider wired from config.
        from mindeval.session_monitor import SessionCapacityMonitor

        monitor = SessionCapacityMonitor.from_config(judge_name, config_path)
        if monitor.enabled:
            from mindeval.session_monitor import build_provider

            monitor = SessionCapacityMonitor.from_config(
                judge_name,
                config_path,
                provider=build_provider(monitor.config),
            )

        if wai_batch:
            # ── Work_Unit chunked-parallel pipeline (batch mode) ───────────
            # Build one batch prompt per dialogue (reused across that
            # dialogue's runs). build_prompt_batch / messages_to_convo_str are
            # already imported at module scope.
            prompts = [
                build_prompt_batch(messages_to_convo_str(pkg.get("interaction", [])))
                for pkg in records_to_process
            ]

            # Flatten into Work_Units of (dialogue_idx, run_idx): one batch WAI
            # call per (dialogue, run) combination, so a single dialogue's
            # n_runs calls are eligible to execute concurrently across Batches.
            work_messages: list[list[dict]] = []
            work_owner: list[tuple[int, int]] = []
            for d_idx, _pkg in enumerate(records_to_process):
                for r_idx in range(n_runs):
                    work_messages.append([{"role": "user", "content": prompts[d_idx]}])
                    work_owner.append((d_idx, r_idx))

            # Per-dialogue fan-in accumulators consumed by the dispatch loop
            # (task 5.4): parsed run dicts collect here until a dialogue has all
            # n_runs results, at which point it is aggregated, saved once, and
            # marked done so it is never written twice.
            dialogue_runs: list[list[dict]] = [[] for _ in records_to_process]
            dialogue_done: list[bool] = [False] * len(records_to_process)
            # Number of this dialogue's Work_Units processed across all Batches
            # so far; a dialogue is complete once this reaches n_runs.
            processed_count: list[int] = [0] * len(records_to_process)

            # Group Work_Units into Batches of at most max_workers, dispatched
            # as contiguous slices. When max_workers == 1 each Batch holds
            # exactly one Work_Unit.
            n_units = len(work_messages)
            # Progress bar tracks completed dialogues (not Work_Units), so the
            # percentage is meaningful regardless of n_runs / max_workers.
            progress = tqdm(total=len(records_to_process), desc="WAI evaluation")
            for start in range(0, n_units, max_workers):
                batch_messages = work_messages[start:start + max_workers]
                batch_owner = work_owner[start:start + max_workers]

                # ── Session monitor gating (before dispatching the Batch) ──
                # On STOP, completed dialogues are already saved incrementally,
                # so breaking here preserves progress; a re-run resumes via
                # the existing skip_existing path.
                decision = monitor.should_continue(
                    completed_count=len(new_judgments),
                    output_path=output_path,
                )
                if not decision.should_continue:
                    print(decision.message)
                    break

                # ── Dispatch the whole Batch in one concurrent call ────────
                # Returns one raw string per Work_Unit, positionally aligned
                # with batch_owner.
                raw_responses = inference_engine.batch_generate(batch_messages)

                # ── Scatter results back to the owning dialogues ───────────
                # A run whose response cannot be parsed contributes no scores
                # (nothing is appended), matching evaluate_dialogue_batch which
                # drops failed runs. Every Work_Unit counts toward its
                # dialogue's processed_count regardless of parse success.
                for (d_idx, _r_idx), raw in zip(batch_owner, raw_responses):
                    run_result = parse_batch_response(raw)
                    if run_result is not None:
                        dialogue_runs[d_idx].append(run_result)
                    processed_count[d_idx] += 1

                # ── Fan-in / finalize-once ─────────────────────────────────
                # Any dialogue whose Work_Units are now all processed and not
                # yet saved is aggregated, annotated, appended once, and marked
                # done. Per-dialogue try/except isolates finalize failures so
                # one bad dialogue never aborts the run (Req 8).
                for d_idx, _o_idx in batch_owner:
                    if dialogue_done[d_idx]:
                        continue
                    if processed_count[d_idx] < n_runs:
                        continue

                    interaction_id = records_to_process[d_idx].get("interaction_id", "")
                    try:
                        result = _aggregate_runs(dialogue_runs[d_idx], n_runs)
                        result["interaction_id"] = interaction_id
                        result["judge_name"]     = effective_judge
                        result["judge_model"]    = judge_model_name
                    except Exception as exc:
                        print(f"\n  [{interaction_id}] ERROR: {exc}")
                        result = {
                            "n_runs":     n_runs,
                            "questions":  {},
                            "dimensions": {"Goal": None, "Approach": None, "Affective Bond": None},
                            "total":      None,
                            "error":      str(exc),
                            "interaction_id": interaction_id,
                            "judge_name":     effective_judge,
                            "judge_model":    judge_model_name,
                        }

                    new_judgments.append(result)
                    dialogue_done[d_idx] = True
                    progress.update(1)

                    # Incremental save: append the completed record immediately
                    # so a partial run can be resumed via skip_existing.
                    with open(output_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")

                # ── Inter-batch delay (between non-final Batches only) ─────
                is_final_batch = start + max_workers >= n_units
                if batch_delay > 0 and not is_final_batch:
                    time.sleep(batch_delay)

            progress.close()
        else:
            # ── Per-question sequential path (out of scope for parallelization) ──
            # wai_batch=False keeps the existing per-dialogue sequential
            # approach (12 prompts × n_runs per dialogue via evaluate_dialogue).
            for pkg in tqdm(records_to_process, desc="WAI evaluation"):
                # Pre-dialogue capacity check (no-op when the monitor is disabled).
                # On STOP, completed records are already saved incrementally, so
                # breaking here preserves progress; a re-run resumes via the
                # existing skip_existing path.
                decision = monitor.should_continue(
                    completed_count=len(new_judgments),
                    output_path=output_path,
                )
                if not decision.should_continue:
                    print(decision.message)
                    break

                interaction_id = pkg.get("interaction_id", "")
                interaction    = pkg.get("interaction", [])
                convo_str      = messages_to_convo_str(interaction)

                try:
                    result = evaluate_dialogue(
                        conversation=convo_str,
                        inference_engine=inference_engine,
                        n_runs=n_runs,
                        verbose=False,
                        batch=wai_batch,
                    )
                except Exception as exc:
                    print(f"\n  [{interaction_id}] ERROR: {exc}")
                    result = {
                        "n_runs":     n_runs,
                        "questions":  {},
                        "dimensions": {"Goal": None, "Approach": None, "Affective Bond": None},
                        "total":      None,
                        "error":      str(exc),
                    }

                result["interaction_id"] = interaction_id
                result["judge_name"]     = effective_judge
                result["judge_model"]    = judge_model_name
                new_judgments.append(result)

                # Incremental save: append the new record immediately so that
                # a partial run can be resumed via skip_existing on re-run.
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # ── Final save (batch path only; sync path already saved incrementally) ──
    if use_anthropic_batch:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        all_outputs = existing_judgments + new_judgments
        save_to_jsonl(all_outputs, output_path)

    total_count = len(existing_judgments) + len(new_judgments)
    print(f"\n✓ WAI evaluation complete!")
    print(f"  Total    : {total_count}")
    print(f"  Existing : {len(existing_judgments)}")
    print(f"  New      : {len(new_judgments)}")
    print(f"  Output   : {output_path}")

    # ── Summary statistics ─────────────────────────────────────────────────
    valid = [r for r in new_judgments if r.get("total") is not None]
    if valid:
        totals = [r["total"] for r in valid]
        print(f"\n=== New judgments summary (n={len(valid)}) ===")
        print(f"  Total WAI : {statistics.mean(totals):.3f}  "
              f"[{min(totals):.2f} – {max(totals):.2f}]")
        for dim in ("Goal", "Approach", "Affective Bond"):
            scores = [r["dimensions"][dim] for r in valid
                      if r.get("dimensions", {}).get(dim) is not None]
            if scores:
                print(f"  {dim:<15s}: {statistics.mean(scores):.3f}")


if __name__ == "__main__":
    CLI([main], as_positional=False)
