from typing import Any, Optional
import sys
from pathlib import Path

from jsonargparse import CLI
from mindeval.inference import InferenceEngine
from mindeval.judge_prompts import JUDGE_PROMPT_TEMPLATE_VERSION_DICT
from mindeval.config import get_judge_config
from mindeval.utils import (
    load_jsonl,
    messages_to_convo_str,
    parse_judge_scores,
    save_to_jsonl,
)
from tqdm import tqdm


def main(
    interactions_path: str,
    max_workers: int,
    output_path: str,
    judge_model_api_params: Optional[dict[str, Any]] = None,
    config_path: Optional[str] = None,
    judge_name: Optional[str] = None,
    judge_template_version: Optional[str] = None,
    judge_template_path: Optional[str] = None,
    skip_existing: bool = True,
    max_dialogues: Optional[int] = None,
    batch_delay: float = 0.0,
):
    """
    Generate judgments for interactions using a judge model.

    Args:
        interactions_path: Path to interactions JSONL file
        max_workers: Number of parallel workers for batch processing
        output_path: Path to save judgments JSONL file
        judge_model_api_params: API parameters for judge model (overrides everything)
        config_path: Path to config.json
        judge_name: Named judge from config 'judges' section (e.g. 'gpt', 'claude').
                    Overrides the default 'judge' section when specified.
        judge_template_version: Version of built-in judge template (e.g., "v0_1")
        judge_template_path: Path to custom judge template Python file
        skip_existing: If True, skip interactions that already have judgments (default: True)
        max_dialogues: If set, evaluate only the first N dialogues (for pilot runs)
        batch_delay: Seconds to sleep between batches (default: 0). Use ~3–5 for
                     Anthropic Tier-1 to stay under 30k tokens/min rate limit.

    Note: Provide either judge_template_version OR judge_template_path, not both.
          Priority for judge config: judge_model_api_params > judge_name > config_path default.
    """
    from mindeval.config import get_named_judge_config

    # Resolve judge model config
    if judge_model_api_params:
        pass  # use as-is
    elif judge_name and config_path:
        judge_model_api_params = get_named_judge_config(judge_name, config_path)
        print(f"Loaded judge config '{judge_name}' from: {config_path} "
              f"(model: {judge_model_api_params.get('model')})")
    elif config_path:
        judge_model_api_params = get_judge_config(config_path)
        print(f"Loaded judge config from: {config_path}")
    else:
        raise ValueError("Must provide either judge_model_api_params or config_path")

    # Resolve the short judge identifier and actual model string for embedding in output
    effective_judge_name  = judge_name or "gpt"
    effective_judge_model = (judge_model_api_params or {}).get("model", "unknown")

    # load interactions
    all_packages = load_jsonl(interactions_path)
    if max_dialogues is not None:
        all_packages = all_packages[:max_dialogues]
        print(f"Limiting to first {max_dialogues} dialogues (pilot mode)")

    # Extract interaction_id for every record (fallback to positional index)
    all_ids = [
        p.get("interaction_id", f"record_{i}")
        for i, p in enumerate(all_packages)
    ]

    # Load existing judgments if skip_existing is True — use ID-based matching
    existing_judgments = []
    output_file = Path(output_path)
    if skip_existing and output_file.exists():
        print(f"Loading existing judgments from: {output_path}")
        existing_judgments = load_jsonl(output_path)
        print(f"Found {len(existing_judgments)} existing judgments")

    # Determine which records still need judgment (ID-based, not positional)
    if skip_existing and existing_judgments:
        existing_ids = {
            j["interaction_id"]
            for j in existing_judgments
            if "interaction_id" in j
        }
        if existing_ids:
            # ID-based skip: safe against gaps from retries / partial runs
            todo_indices = [i for i, iid in enumerate(all_ids) if iid not in existing_ids]
        else:
            # Fallback: old files without interaction_id → positional skip
            n_existing = len(existing_judgments)
            todo_indices = list(range(n_existing, len(all_packages)))
            print(
                f"  [warn] Existing file has no interaction_id fields — "
                f"falling back to positional skip (first {n_existing} records)."
            )

        if not todo_indices:
            print(f"[OK] All {len(all_packages)} interactions already have judgments. Skipping generation.")
            return

        print(f"Skipping {len(all_packages) - len(todo_indices)} interactions (already judged by ID)")
        print(f"Generating judgments for {len(todo_indices)} new interactions")
    else:
        existing_judgments = []
        todo_indices = list(range(len(all_packages)))
        print(f"Generating judgments for {len(todo_indices)} interactions")

    todo_packages = [all_packages[i] for i in todo_indices]
    todo_ids = [all_ids[i] for i in todo_indices]
    all_interactions = [p["interaction"] for p in todo_packages]
    n_interactions = len(all_interactions)
    
    # load judge prompt (user prompt!)
    if judge_template_path:
        # Load from custom file path
        print(f"Loading judge template from: {judge_template_path}")
        template_path = Path(judge_template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Judge template file not found: {judge_template_path}")
        
        # Add parent directory to sys.path to import the module
        sys.path.insert(0, str(template_path.parent))
        module_name = template_path.stem  # e.g., "judge_prompts_zh"
        
        # Import the module
        judge_module = __import__(module_name)
        judge_prompt_template = judge_module.JUDGE_PROMPT_TEMPLATE
        print(f"[OK] Loaded template from {module_name}.JUDGE_PROMPT_TEMPLATE")
        
    elif judge_template_version:
        # Load from built-in version dictionary
        print(f"Loading built-in judge template version: {judge_template_version}")
        judge_prompt_template = JUDGE_PROMPT_TEMPLATE_VERSION_DICT[judge_template_version]
        print(f"[OK] Loaded template version {judge_template_version}")
        
    else:
        raise ValueError("Must provide either judge_template_version or judge_template_path")
    
    # instantiate judge model
    judge_model = InferenceEngine(judge_model_api_params)
    use_anthropic_batch = judge_model_api_params.get("use_anthropic_batch", False)

    import time as _time

    # Build all messages upfront (needed for both flows)
    all_messages = []
    for interaction in all_interactions:
        convo_str   = messages_to_convo_str(interaction)
        user_prompt = judge_prompt_template.substitute(conversation_str=convo_str)
        all_messages.append([{"role": "user", "content": user_prompt}])

    # Incremental save: start from existing judgments, append after every batch
    # so partial runs are recoverable without re-evaluating already-done records.
    accumulated_outputs = list(existing_judgments)

    # Session capacity monitor (non-invasive add-on). Disabled for every judge
    # other than the configured target_judge, in which case `should_continue`
    # always returns CONTINUE and never performs any HTTP call. When enabled,
    # rebuild the monitor with a concrete HTTP usage provider wired from config.
    from mindeval.session_monitor import SessionCapacityMonitor

    monitor = SessionCapacityMonitor.from_config(judge_name, config_path)
    if monitor.enabled:
        from mindeval.session_monitor import build_provider

        monitor = SessionCapacityMonitor.from_config(
            judge_name,
            config_path,
            provider=build_provider(monitor.config),
        )

    if use_anthropic_batch:
        # ── Anthropic Message Batches API (50% token discount) ──────────────
        # Submits all remaining records as one batch; polls until complete.
        print(f"[anthropic-batch] Using Anthropic Batch API for {n_interactions} interactions …")
        all_judgments, all_thinking = judge_model.batch_generate_all_with_thinking_anthropic(
            all_messages
        )
        for iid, u, t in zip(todo_ids, all_judgments, all_thinking):
            accumulated_outputs.append({
                "interaction_id":    iid,
                "judge_name":        effective_judge_name,
                "judge_model":       effective_judge_model,
                "parsed_judgment":   parse_judge_scores(u)[0],
                "unparsed_judgment": u,
                "thinking_trace":    t,
            })
        save_to_jsonl(accumulated_outputs, output_path)

    else:
        # ── Standard chunked synchronous flow ───────────────────────────────
        n_batches = (n_interactions + max_workers - 1) // max_workers
        for batch_idx, batch_start in enumerate(tqdm(
            range(0, n_interactions, max_workers),
            total=n_batches,
            desc="Judging interactions",
        )):
            batch_slice = slice(batch_start, min(batch_start + max_workers, n_interactions))
            batch_messages = all_messages[batch_slice]
            batch_ids      = todo_ids[batch_slice]

            # Pre-batch capacity check (no-op when the monitor is disabled).
            # On STOP, completed judgments are already saved after the previous
            # batch, so breaking here preserves progress; a re-run resumes via
            # the existing skip_existing path.
            decision = monitor.should_continue(
                completed_count=len(accumulated_outputs) - len(existing_judgments),
                output_path=output_path,
            )
            if not decision.should_continue:
                print(decision.message)
                break

            judgments, thinking = judge_model.batch_generate_with_thinking(batch_messages)

            for iid, u, t in zip(batch_ids, judgments, thinking):
                accumulated_outputs.append({
                    "interaction_id":    iid,
                    "judge_name":        effective_judge_name,
                    "judge_model":       effective_judge_model,
                    "parsed_judgment":   parse_judge_scores(u)[0],
                    "unparsed_judgment": u,
                    "thinking_trace":    t,
                })

            # Save after every batch — tolerates crashes mid-run
            save_to_jsonl(accumulated_outputs, output_path)

            # Optional inter-batch delay (e.g. Anthropic Tier-1 rate limit)
            if batch_delay > 0 and batch_idx < n_batches - 1:
                _time.sleep(batch_delay)

    all_outputs = accumulated_outputs
    
    n_new = len(all_outputs) - len(existing_judgments)
    print(f"\n[OK] Judgment generation complete!")
    print(f"  Total judgments: {len(all_outputs)}")
    print(f"  Existing: {len(existing_judgments)}")
    print(f"  New: {n_new}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    CLI([main], as_positional=False)
