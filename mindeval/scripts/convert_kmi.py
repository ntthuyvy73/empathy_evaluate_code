"""
Convert KMI raw data to a structured Mind-Eval format.

Input  : data/KMI/raw/kmi.json
Output : data/KMI/test/interactions_<N>.jsonl

Each output record has the following shape:

{
  "id":          <int>,
  "category_en": "<category>",
  "dialogue": [
      {"role": "Therapist", "content": "<utterance_en>", "label": "<MI label>"},
      {"role": "Client",    "content": "<utterance_en>"},
      ...
  ]
}

Sampling strategy
-----------------
By default (--stratified, which is on by default) the script uses stratified
random sampling so that every category is represented proportionally to its
size in the full dataset.  This guarantees diversity even for small N.

When --no_stratified is passed, a simple random sample is drawn instead.

Usage:
    # 200 records, proportional per category (default)
    python mindeval/scripts/convert_kmi.py --n 200

    # 100 records, simple random
    python mindeval/scripts/convert_kmi.py --n 100 --no_stratified

    # Custom paths + seed
    python mindeval/scripts/convert_kmi.py \\
        --input_path data/KMI/raw/kmi.json \\
        --output_path data/KMI/test/kmi_200.jsonl \\
        --n 200 --seed 0

    # All records (no sampling)
    python mindeval/scripts/convert_kmi.py --n 0
"""

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert one raw KMI dialogue to the target format.

    Keeps only utterance_en for each turn.
    For Therapist turns, the 'label' field is included when present.
    Returns None if the dialogue list is empty or missing.
    """
    raw_turns = item.get("dialogue")
    if not raw_turns:
        return None

    turns = []
    for t in raw_turns:
        role = t.get("role", "")
        content = t.get("utterance_en", "").strip()
        if not content:
            continue

        turn: Dict[str, Any] = {"role": role, "content": content}

        # Include MI technique label for Therapist turns
        if role == "Therapist" and "label" in t:
            turn["label"] = t["label"]

        turns.append(turn)

    if not turns:
        return None

    return {
        "id":          item["id"],
        "category_en": item.get("category_en", "Unknown"),
        "dialogue":    turns,
    }


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------

def stratified_sample(
    records: List[Dict[str, Any]],
    n: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Sample exactly n records with category proportions matching the full dataset.

    Algorithm:
    1. Group records by category.
    2. Compute the ideal (floating-point) quota per category.
    3. Use the "largest remainder" method to allocate integer slots that sum to n.
    4. Draw randomly within each category up to its slot.
    5. If rounding left short, fill remaining slots from the largest categories.

    Returns a shuffled list of n records (or all records if n >= total).
    """
    if n <= 0 or n >= len(records):
        result = list(records)
        rng.shuffle(result)
        return result

    # Group by category
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        groups[rec["category_en"]].append(rec)

    total = len(records)
    categories = list(groups.keys())

    # Compute exact (float) quota per category
    exact = {cat: n * len(groups[cat]) / total for cat in categories}

    # Floor allocations
    floors = {cat: math.floor(exact[cat]) for cat in categories}
    remainders = {cat: exact[cat] - floors[cat] for cat in categories}
    allocated = sum(floors.values())
    deficit = n - allocated

    # Distribute remaining slots to categories with the largest remainders
    sorted_by_remainder = sorted(categories, key=lambda c: remainders[c], reverse=True)
    for i in range(deficit):
        floors[sorted_by_remainder[i]] += 1

    # Sample within each category
    result: List[Dict[str, Any]] = []
    for cat in categories:
        quota = floors[cat]
        pool = groups[cat]
        sampled = rng.sample(pool, min(quota, len(pool)))
        result.extend(sampled)

    rng.shuffle(result)
    return result


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
        description="Convert KMI raw data to structured Mind-Eval JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input_path",
        default="data/KMI/raw/kmi.json",
        help="Path to kmi.json (default: data/KMI/raw/kmi.json).",
    )
    parser.add_argument(
        "--output_path",
        default=None,
        help="Output JSONL file (default: data/KMI/test/interactions_<N>.jsonl).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=200,
        help="Number of records to sample (default: 200). Use 0 for all records.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42).",
    )
    parser.add_argument(
        "--no_stratified",
        action="store_true",
        default=False,
        help="Use simple random sampling instead of stratified sampling.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    n = args.n
    rng = random.Random(args.seed)
    stratified = not args.no_stratified

    label = n if n > 0 else "all"
    output_path = Path(args.output_path or f"data/KMI/test/interactions_{label}.jsonl")

    # Load raw data
    print(f"Loading {input_path} ...")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data)} raw dialogues loaded.")

    # Convert all records first
    records: List[Dict[str, Any]] = []
    skipped = 0
    for item in data:
        rec = build_record(item)
        if rec is None:
            skipped += 1
        else:
            records.append(rec)
    print(f"  Converted: {len(records)}  Skipped: {skipped}")

    # Sample
    if n > 0 and n < len(records):
        if stratified:
            sampled = stratified_sample(records, n, rng)
            print(f"  Stratified sample: {len(sampled)} records (seed={args.seed}).")
        else:
            sampled = rng.sample(records, n)
            print(f"  Simple random sample: {len(sampled)} records (seed={args.seed}).")
    else:
        sampled = records
        rng.shuffle(sampled)
        print(f"  Using all {len(sampled)} records.")

    # Print category distribution in the sample
    from collections import Counter
    cat_dist = Counter(r["category_en"] for r in sampled)
    print("\n  Category distribution in sample:")
    for cat, cnt in sorted(cat_dist.items(), key=lambda x: -x[1]):
        pct = cnt / len(sampled) * 100
        print(f"    {cnt:4d} ({pct:5.1f}%)  {cat}")

    # Save
    save_jsonl(sampled, output_path)
    print(f"\nSaved {len(sampled)} records -> {output_path}")


if __name__ == "__main__":
    main()
