"""
Convert PsyDial raw data to the standardised Mind-Eval format.

Input  : data/PsyDial/raw/PsyDial-D4.json
Output : data/PsyDial/test/interactions_<N>.jsonl

PsyDial-D4 is a Chinese counselling corpus.  Each record contains a single
`messages` list whose turns have role "system" / "user" / "assistant".
The system turn (always present, always identical across all 2,382 records)
introduces the virtual counsellor "小天" and is excluded from the output.

Output format (one JSON object per line):
{
  "member_profile": { <18-field schema, mostly "Unknown"> },
  "interaction":    [ {"role": "user"|"assistant", "content": "<zh>"}, ... ],
  "metadata": {
      "source":         "PsyDial",
      "original_index": <int>,
      "language":       "zh",
      "turn_count":     <int>,
      "length_bucket":  "short|medium|long|very_long",
      "profile_extracted": false
  }
}

Sampling strategy (--stratified, default when --n > 0)
------------------------------------------------------
Because PsyDial carries no topic/category labels, stratification is by
dialogue-length bucket so that all conversation lengths are proportionally
represented in the sample:

  short      < 30 user+assistant turns   (  2.6 %  of dataset)
  medium     30-59 turns                 ( 32.7 %)
  long       60-99 turns                 ( 43.8 %)
  very_long  >= 100 turns                ( 20.9 %)

Usage:
    python mindeval/scripts/convert_psydial.py              # 10 records
    python mindeval/scripts/convert_psydial.py --n 200      # 200 records (stratified)
    python mindeval/scripts/convert_psydial.py --n 200 --no_stratified  # simple random
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

def _length_bucket(n_turns: int) -> str:
    if n_turns < 30:  return "short"
    if n_turns < 60:  return "medium"
    if n_turns < 100: return "long"
    return "very_long"


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(item: Dict[str, Any], original_index: int) -> Optional[Dict[str, Any]]:
    """
    Convert one raw PsyDial item into the output format.

    Skips the 'system' turn (counsellor persona).
    Returns None if the dialogue is empty after filtering.
    """
    messages = item.get("messages", [])
    turns = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
    ]
    if not turns:
        return None

    n_turns = len(turns)
    return {
        "dialogue": turns,
        "metadata": {
            "source":         "PsyDial",
            "original_index": original_index,
            "language":       "zh",
            "turn_count":     n_turns,
            "length_bucket":  _length_bucket(n_turns),
        },
    }


# ---------------------------------------------------------------------------
# Sampling
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


def stratified_sample(data: List[Dict[str, Any]], n: int, rng: random.Random) -> List[Dict[str, Any]]:
    """
    Sample n records stratified by dialogue-length bucket.

    Quotas are proportional to each bucket's size in the full dataset.
    Within each bucket, records are sampled randomly.
    """
    # Group indices by bucket
    buckets: Dict[str, List[int]] = defaultdict(list)
    for idx, item in enumerate(data):
        msgs = item.get("messages", [])
        turns = [m for m in msgs if m.get("role") in ("user", "assistant")]
        bucket = _length_bucket(len(turns))
        buckets[bucket].append(idx)

    # Compute quotas proportional to bucket sizes
    bucket_sizes = {k: len(v) for k, v in buckets.items()}
    quotas = _compute_quotas(bucket_sizes, n)

    print("  Bucket sizes (full dataset):")
    for bkt in ["short", "medium", "long", "very_long"]:
        sz = bucket_sizes.get(bkt, 0)
        q  = quotas.get(bkt, 0)
        print(f"    {bkt:<12} {sz:>5} records  ->  quota {q}")

    # Sample from each bucket
    selected_indices: List[int] = []
    for bkt, quota in quotas.items():
        pool = buckets.get(bkt, [])
        picked = rng.sample(pool, min(quota, len(pool)))
        if len(picked) < quota:
            print(f"  Warning: {bkt} bucket only has {len(pool)} records, need {quota}.")
        selected_indices.extend(picked)

    # Build records
    results = []
    for idx in selected_indices:
        rec = build_record(data[idx], idx)
        if rec:
            results.append(rec)

    rng.shuffle(results)
    return results


def simple_sample(data: List[Dict[str, Any]], n: int, rng: random.Random) -> List[Dict[str, Any]]:
    """Simple random sample without stratification."""
    indices = rng.sample(range(len(data)), min(n, len(data)))
    results = []
    for idx in indices:
        rec = build_record(data[idx], idx)
        if rec:
            results.append(rec)
    return results


# ---------------------------------------------------------------------------
# I/O helpers
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
        description="Convert PsyDial-D4 to Mind-Eval JSONL format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input_path",
        default="data/PsyDial/raw/PsyDial-D4.json",
        help="Path to PsyDial-D4.json.",
    )
    parser.add_argument(
        "--output_path",
        default=None,
        help="Output JSONL file (default: data/PsyDial/test/interactions_<N>.jsonl).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of records to sample (default: 10).  Use 0 for all records.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--no_stratified",
        action="store_true",
        default=False,
        help="Disable stratified sampling; use simple random sample instead.",
    )
    args = parser.parse_args()

    input_path  = Path(args.input_path)
    n           = args.n
    rng         = random.Random(args.seed)
    output_path = Path(args.output_path) if args.output_path else \
                  Path(f"data/PsyDial/test/interactions_{n if n > 0 else 'all'}.jsonl")

    print(f"Loading {input_path} ...")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data)} raw records loaded.")

    if n == 0 or n >= len(data):
        print("  Using all records (no sampling).")
        records = [build_record(item, idx) for idx, item in enumerate(data)]
        records = [r for r in records if r]
    elif args.no_stratified:
        print(f"  Simple random sample: n={n}, seed={args.seed}")
        records = simple_sample(data, n, rng)
    else:
        print(f"  Length-stratified sample: n={n}, seed={args.seed}")
        records = stratified_sample(data, n, rng)

    print(f"  Sampled {len(records)} records.")
    save_jsonl(records, output_path)
    print(f"Saved {len(records)} records -> {output_path}")


if __name__ == "__main__":
    main()
