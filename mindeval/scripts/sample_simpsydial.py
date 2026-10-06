"""
Sample SimPsyDial raw dialogues → Mind-Eval JSONL format.

SimPsyDial contains 1,000 individual JSON files (data/simpsydial/raw/<id>.json).
Each file is a list of turns with roles "client" / "counselor".

Output format:
{
  "member_profile": { "race": "Asian", "region": "urban", rest "Unknown" },
  "interaction":    [ {"role": "user"|"assistant", "content": "..."}, ... ],
  "metadata": {
      "source": "SimPsyDial",
      "original_file": "<id>.json",
      "language": "zh",
      "turn_count": <int>,
      "length_bucket": "short|medium|long",
      "profile_extracted": false
  }
}

Sampling strategy
-----------------
No topic labels exist, so stratification is by dialogue-length bucket
(proportional to bucket sizes in the full 1,000-file corpus):

  short   < 25 turns
  medium  25-34 turns
  long    >= 35 turns

Usage:
    python mindeval/scripts/sample_simpsydial.py             # 10 records
    python mindeval/scripts/sample_simpsydial.py --n 200     # 200 records (stratified)
    python mindeval/scripts/sample_simpsydial.py --n 200 --no_stratified
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

ROLE_MAP: Dict[str, str] = {}  # Keep original roles: client / counselor


def _length_bucket(n: int) -> str:
    if n < 25:  return "short"
    if n < 35:  return "medium"
    return "long"


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(fpath: Path) -> Optional[Dict[str, Any]]:
    """Load one SimPsyDial JSON file and return minimal output."""
    with open(fpath, encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        return None

    # Keep original roles (client / counselor) — do not remap to user/assistant
    turns = [
        {"role": t.get("role", ""), "content": t.get("content", "").strip()}
        for t in raw
        if t.get("content", "").strip()
    ]
    if not turns:
        return None

    n = len(turns)
    return {
        "dialogue": turns,
        "metadata": {
            "source":         "SimPsyDial",
            "original_file":  fpath.name,
            "language":       "zh",
            "turn_count":     n,
            "length_bucket":  _length_bucket(n),
        },
    }


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _compute_quotas(weights: Dict[str, int], total: int) -> Dict[str, int]:
    """Largest-remainder proportional allocation."""
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
    all_files: List[Path], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """Sample n records stratified by dialogue-length bucket."""
    # Pre-scan turn counts
    buckets: Dict[str, List[Path]] = defaultdict(list)
    for fp in all_files:
        with open(fp, encoding="utf-8") as f:
            raw = json.load(f)
        n_turns = sum(1 for t in raw if isinstance(t, dict) and t.get("content", "").strip())
        buckets[_length_bucket(n_turns)].append(fp)

    bucket_sizes = {k: len(v) for k, v in buckets.items()}
    quotas = _compute_quotas(bucket_sizes, n)

    print("  Bucket sizes (full dataset):")
    for bkt in ["short", "medium", "long"]:
        sz = bucket_sizes.get(bkt, 0)
        q  = quotas.get(bkt, 0)
        print(f"    {bkt:<8} {sz:>5} files  ->  quota {q}")

    results = []
    for bkt, quota in quotas.items():
        pool = list(buckets.get(bkt, []))
        rng.shuffle(pool)
        for fp in pool[:quota]:
            rec = build_record(fp)
            if rec:
                results.append(rec)

    rng.shuffle(results)
    return results


def simple_sample(
    all_files: List[Path], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """Simple random sample."""
    picked = rng.sample(all_files, min(n, len(all_files)))
    results = []
    for fp in picked:
        rec = build_record(fp)
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
        description="Sample SimPsyDial raw dialogues to Mind-Eval JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input_dir",   default="data/simpsydial/raw")
    parser.add_argument("--output_path", default=None)
    parser.add_argument("--n",     type=int, default=10)
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--no_stratified", action="store_true", default=False)
    args = parser.parse_args()

    raw_dir = Path(args.input_dir)
    n       = args.n
    rng     = random.Random(args.seed)
    out     = Path(args.output_path) if args.output_path else \
              Path(f"data/simpsydial/test/interactions_{n if n > 0 else 'all'}.jsonl")

    all_files = sorted(raw_dir.glob("*.json"),
                       key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
    print(f"Found {len(all_files)} dialogue files in {raw_dir}")

    if n == 0 or n >= len(all_files):
        print("  Using all files.")
        records = [r for fp in all_files for r in [build_record(fp)] if r]
    elif args.no_stratified:
        print(f"  Simple random sample: n={n}, seed={args.seed}")
        records = simple_sample(all_files, n, rng)
    else:
        print(f"  Length-stratified sample: n={n}, seed={args.seed}")
        records = stratified_sample(all_files, n, rng)

    print(f"  Sampled {len(records)} records.")
    save_jsonl(records, out)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
