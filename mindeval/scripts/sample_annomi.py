"""
Sample AnnoMI for test evaluation.

AnnoMI has only 133 conversations (< 200), so we take ALL of them (after
applying an optional max_turns cap to exclude very long transcripts that
would exceed typical LLM judge context budgets).

Length-bucket thresholds (canonical, shared across all Mind-Eval datasets):
  short     : turn_count <= 10
  medium    : turn_count <= 30
  long      : turn_count <= 70
  very_long : turn_count  > 70

The output is sorted by stratified interleaving (mi_quality × length_bucket ×
topic_group) so that the first N records are representative for pilot runs
(evaluate.py --max_dialogues N takes the first N lines of the file).

Outputs
-------
  data/AnnoMI/test/interactions_<N>_canonical.jsonl

Usage
-----
    python mindeval/scripts/sample_annomi.py
    python mindeval/scripts/sample_annomi.py --max_turns 150 --seed 42
    python mindeval/scripts/sample_annomi.py --max_turns 0   # keep all 133
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _length_bucket(turn_count: int) -> str:
    """Canonical bucket thresholds used across all Mind-Eval datasets."""
    if turn_count <= 10:
        return "short"
    if turn_count <= 30:
        return "medium"
    if turn_count <= 70:
        return "long"
    return "very_long"


def _load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _save_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _topic_group(topic: str) -> str:
    """Coarse grouping to avoid over-representing a single topic."""
    t = topic.lower()
    if any(k in t for k in ["alcohol", "drug", "substanc", "smoking"]):
        return "substance_use"
    if any(k in t for k in ["weight", "diet", "eating", "food", "physical"]):
        return "physical_health"
    if any(k in t for k in ["anxiety", "stress", "worry"]):
        return "anxiety"
    if any(k in t for k in ["depress", "mood", "sadness"]):
        return "depression"
    if any(k in t for k in ["relation", "family", "partner", "marriage"]):
        return "relationships"
    if any(k in t for k in ["exercise", "fitness", "activ"]):
        return "exercise"
    if any(k in t for k in ["work", "career", "job"]):
        return "work"
    if any(k in t for k in ["sleep"]):
        return "sleep"
    return "other"


# ---------------------------------------------------------------------------
# Sampling logic
# ---------------------------------------------------------------------------

def sample_annomi(src: Path, seed: int, max_turns: int = 150) -> list[dict]:
    """
    Load AnnoMI records, optionally cap by max_turns, fix length_bucket,
    then sort by stratified interleaving for representative pilot-run ordering.

    Args:
        max_turns: Drop records with turn_count > this value.
                   Set to 0 (or any negative int) to keep all records.
    """
    raw_records = _load_jsonl(src)
    rng = random.Random(seed)

    if max_turns > 0:
        before = len(raw_records)
        raw_records = [r for r in raw_records if r['metadata']['turn_count'] <= max_turns]
        dropped = before - len(raw_records)
        if dropped:
            print(f"  Dropped {dropped} records with turn_count > {max_turns} "
                  f"(kept {len(raw_records)}/{before})")

    out: list[dict] = []
    for rec in raw_records:
        tc = rec["metadata"]["turn_count"]
        bucket = _length_bucket(tc)

        mi_quality = rec["extra"].get("mi_quality", "unknown")
        topic      = rec["extra"].get("topic", "")
        tgroup     = _topic_group(topic)

        # Update bucket to canonical thresholds
        updated = dict(rec)
        updated["metadata"] = dict(rec["metadata"])
        updated["metadata"]["length_bucket"] = bucket

        # Attach topic_group to extra for downstream analysis
        updated["extra"] = dict(rec["extra"])
        updated["extra"]["topic_group"] = tgroup

        out.append((mi_quality, bucket, tgroup, updated))

    # Sort by (mi_quality, bucket, topic_group) then shuffle within each cell
    # to produce a deterministic representative ordering
    cells: dict[tuple, list] = defaultdict(list)
    for mi, bk, tg, rec in out:
        cells[(mi, bk, tg)].append(rec)

    for cell_recs in cells.values():
        rng.shuffle(cell_recs)

    # Interleave cells: cycle through all cells in sorted order
    sorted_cells = [cells[k] for k in sorted(cells.keys())]
    final: list[dict] = []
    while any(sorted_cells):
        for cell_recs in sorted_cells:
            if cell_recs:
                final.append(cell_recs.pop(0))

    return final


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Sample AnnoMI for test evaluation.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--max_turns",
        type=int,
        default=150,
        help=(
            "Drop records with turn_count > this value to stay within LLM context budgets "
            "(default: 150). Set to 0 to keep all records."
        ),
    )
    parser.add_argument(
        "--data_dir",
        default="data",
        help="Base data directory relative to project root (default: data)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    src  = data_dir / "AnnoMI" / "raw" / "AnnoMI.jsonl"

    if not src.exists():
        print(f"ERROR: source not found: {src}")
        return

    print(f"Source    : {src}")
    print(f"Seed      : {args.seed}")
    print(f"Max turns : {args.max_turns if args.max_turns > 0 else 'unlimited'}")

    records = sample_annomi(src, args.seed, max_turns=args.max_turns)

    n = len(records)
    dst = data_dir / "AnnoMI" / "test" / f"interactions_{n}_canonical.jsonl"

    # ---- Stats ----
    from collections import Counter
    quality_counts: Counter = Counter()
    bucket_counts:  Counter = Counter()
    tgroup_counts:  Counter = Counter()
    topic_counts:   Counter = Counter()

    for r in records:
        quality_counts[r["extra"]["mi_quality"]] += 1
        bucket_counts[r["metadata"]["length_bucket"]] += 1
        tgroup_counts[r["extra"]["topic_group"]] += 1
        topic_counts[r["extra"]["topic"]] += 1

    print(f"\nTotal records      : {len(records)}")
    print(f"MI quality         : {dict(quality_counts)}")
    print(f"Length buckets     : {dict(bucket_counts)}")
    print(f"Topic groups       : {dict(tgroup_counts)}")
    print(f"\nAll topics ({len(topic_counts)} unique):")
    for topic, cnt in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {cnt:3d}  {topic}")

    _save_jsonl(records, dst)
    print(f"\nWritten -> {dst}")
    print(f"(File name encodes count: interactions_{n}_canonical.jsonl)")


if __name__ == "__main__":
    main()
