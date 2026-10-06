"""
Sample Psy-Insight raw data → structured output format.

Input  : data/Psy-Insight/raw/en_data_version7.json
Output : data/Psy-Insight/test/interactions_<N>.jsonl

Each record in Psy-Insight has rich annotations:
  - dialog_id, theme, psychotherapy, topic, background, reasoning, summary
  - dialog: list of turns with speaker/participant/content/id and per-turn
    annotations (observation, emotional label for Client; reasoning, strategy
    for Therapist).

Output format — preserves all raw fields:
{
  "dialog_id":    "...",
  "psychotherapy": "...",
  "topic":        "...",
  "background":   "...",
  "theme":        "...",
  "reasoning":    "...",       <- top-level session reasoning
  "dialog": [
      {
        "speaker":     "Seeker"|"Supporter",
        "participant": "Client"|"Therapist",
        "content":     "...",
        "id":          "...",
        "observation": "...",        <- Client turns only
        "emotional label": [...],   <- Client turns only
        "reasoning": "...",          <- Therapist turns only
        "strategy":  [...]           <- Therapist turns only
        "reference_labels": [...]    <- if present
      }
  ],
  "summary":  "...",
  "metadata": {
      "source":           "Psy-Insight",
      "language":         "en",
      "turn_count":       <int>,
      "is_same_session":  0|1,
      "is_same_qa":       0|1
  }
}

Sampling strategy
-----------------
Primary  : proportional by `psychotherapy` (13 types, largest-remainder method)
Secondary: within each psychotherapy bucket, balance `topic` where possible

Length buckets (informational):
  micro   <= 4 turns  (29.2 %)
  short    5-10       (35.2 %)
  medium  11-20       (21.9 %)
  long    >20         (13.7 %)

Usage:
    python mindeval/scripts/sample_psyinsight.py               # 10 records
    python mindeval/scripts/sample_psyinsight.py --n 200       # 200 (stratified)
    python mindeval/scripts/sample_psyinsight.py --n 200 --no_stratified
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert one raw Psy-Insight item — keep all meaningful raw fields."""
    dialog = item.get("dialog", [])
    if not dialog:
        return None

    # Preserve all per-turn annotation fields as-is
    cleaned_turns = []
    for turn in dialog:
        if not isinstance(turn, dict):
            continue
        t: Dict[str, Any] = {
            "speaker":     turn.get("speaker", ""),
            "participant": turn.get("participant", ""),
            "content":     turn.get("content", ""),
            "id":          turn.get("id", ""),
        }
        # Optional annotation fields
        for opt in ("observation", "emotional label", "reasoning", "strategy",
                    "reference_labels"):
            if opt in turn:
                t[opt] = turn[opt]
        cleaned_turns.append(t)

    if not cleaned_turns:
        return None

    topic = (item.get("topic") or "").strip() or "Unspecified"

    return {
        "dialog_id":    item.get("dialog_id", ""),
        "psychotherapy": item.get("psychotherapy", ""),
        "topic":        topic,
        "background":   item.get("background", ""),
        "theme":        item.get("theme", ""),
        "reasoning":    item.get("reasoning", ""),
        "dialog":       cleaned_turns,
        "summary":      item.get("summary", ""),
        "metadata": {
            "source":          "Psy-Insight",
            "language":        "en",
            "turn_count":      len(cleaned_turns),
            "is_same_session": item.get("is_same_session", 0),
            "is_same_qa":      item.get("is_same_qa", 0),
        },
    }


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------

def _compute_quotas(weights: Dict[str, int], total: int) -> Dict[str, int]:
    """Largest-remainder (Hamilton) proportional allocation."""
    grand = sum(weights.values())
    if grand == 0:
        return {k: 0 for k in weights}
    exact  = {k: total * v / grand for k, v in weights.items()}
    floors = {k: int(v) for k, v in exact.items()}
    deficit = total - sum(floors.values())
    by_rem = sorted(weights.keys(), key=lambda k: exact[k] - floors[k], reverse=True)
    for i in range(deficit):
        floors[by_rem[i % len(by_rem)]] += 1
    return floors


def stratified_sample(
    data: List[Dict[str, Any]], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """
    Stratify by psychotherapy (primary) with topic-balanced sub-sampling.

    Within each psychotherapy bucket, records are sampled while trying to
    cover all available topics proportionally.
    """
    # Group indices by psychotherapy
    psy_groups: Dict[str, List[int]] = defaultdict(list)
    for idx, item in enumerate(data):
        pt = item.get("psychotherapy", "Unknown")
        psy_groups[pt].append(idx)

    psy_sizes = {k: len(v) for k, v in psy_groups.items()}
    quotas = _compute_quotas(psy_sizes, n)

    print(f"  Psychotherapy stratification:")
    for pt in sorted(psy_sizes, key=lambda x: -psy_sizes[x]):
        sz = psy_sizes[pt]
        q  = quotas.get(pt, 0)
        pct = 100 * sz / len(data)
        print(f"    {pt:<45} {sz:>3} ({pct:5.1f}%)  ->  quota {q}")

    results = []
    for pt, quota in quotas.items():
        if quota == 0:
            continue
        pool = psy_groups[pt]

        # Within this psychotherapy bucket, sub-sample balancing topics
        topic_sub: Dict[str, List[int]] = defaultdict(list)
        for idx in pool:
            t = (data[idx].get("topic") or "").strip() or "Unspecified"
            topic_sub[t].append(idx)

        if len(topic_sub) > 1:
            sub_quotas = _compute_quotas({t: len(v) for t, v in topic_sub.items()}, quota)
            picked_indices = []
            for t, sq in sub_quotas.items():
                candidates = list(topic_sub[t])
                rng.shuffle(candidates)
                picked_indices.extend(candidates[:sq])
        else:
            candidates = list(pool)
            rng.shuffle(candidates)
            picked_indices = candidates[:quota]

        for idx in picked_indices:
            rec = build_record(data[idx])
            if rec:
                results.append(rec)

    rng.shuffle(results)
    return results


def simple_sample(
    data: List[Dict[str, Any]], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """Simple random sample."""
    indices = rng.sample(range(len(data)), min(n, len(data)))
    results = []
    for idx in indices:
        rec = build_record(data[idx])
        if rec:
            results.append(rec)
    return results


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def save_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample Psy-Insight to structured JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input_path",
        default="data/Psy-Insight/raw/en_data_version7.json",
    )
    parser.add_argument("--output_path", default=None)
    parser.add_argument("--n",     type=int, default=10)
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--no_stratified", action="store_true", default=False)
    args = parser.parse_args()

    n   = args.n
    rng = random.Random(args.seed)
    out = Path(args.output_path) if args.output_path else \
          Path(f"data/Psy-Insight/test/interactions_{n if n > 0 else 'all'}.jsonl")

    print(f"Loading {args.input_path} ...")
    with open(args.input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data)} raw records loaded.")

    if n == 0 or n >= len(data):
        print("  Using all records.")
        records = [r for item in data for r in [build_record(item)] if r]
    elif args.no_stratified:
        print(f"  Simple random sample: n={n}, seed={args.seed}")
        records = simple_sample(data, n, rng)
    else:
        print(f"  Psychotherapy-stratified sample: n={n}, seed={args.seed}")
        records = stratified_sample(data, n, rng)

    print(f"  Sampled {len(records)} records.")
    save_jsonl(records, out)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
