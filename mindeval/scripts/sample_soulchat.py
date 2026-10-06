"""
Sample SoulChat raw data → Mind-Eval JSONL format.

SoulChat has 258,353 records with fields: id, topic, messages.
Each record has Chinese user/assistant turns and a topic label (13 categories).

Output format:
{
  "member_profile": { "race": "Asian", "region": "urban", rest "Unknown" },
  "interaction":    [ {"role": "user"|"assistant", "content": "..."}, ... ],
  "metadata": {
      "source":      "SoulChat",
      "original_id": "<id>",
      "topic":       "<topic>",
      "language":    "zh",
      "turn_count":  <int>,
      "profile_extracted": false
  }
}

Sampling strategy
-----------------
Stratify by topic (proportional to full-dataset distribution, largest-remainder).
Empty dialogues (turn_count == 0) are excluded before sampling.

Topics (13 categories):
  婚恋  情绪  人际  家庭  治疗  成长  行为  自我
  社会  职场  心理学知识  未明确  性心理

Usage:
    python mindeval/scripts/sample_soulchat.py            # 10 records
    python mindeval/scripts/sample_soulchat.py --n 200    # 200 (stratified by topic)
    python mindeval/scripts/sample_soulchat.py --n 200 --no_stratified
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
    """Convert one raw SoulChat item — keep id, topic, dialogue as-is."""
    messages = item.get("messages", [])
    turns = [
        {"role": m["role"], "content": m["content"].strip()}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
    ]
    if not turns:
        return None

    return {
        "id":       item.get("id", ""),
        "topic":    item.get("topic", ""),
        "dialogue": turns,
        "metadata": {
            "source":     "SoulChat",
            "language":   "zh",
            "turn_count": len(turns),
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
    data: List[Dict[str, Any]], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """
    Sample n records stratified proportionally by topic.
    Records with empty dialogues are excluded before sampling.
    """
    # Group valid records by topic
    topic_groups: Dict[str, List[int]] = defaultdict(list)
    for idx, item in enumerate(data):
        msgs = item.get("messages", [])
        valid_turns = [m for m in msgs
                       if m.get("role") in ("user", "assistant") and m.get("content", "").strip()]
        if valid_turns:
            topic = item.get("topic", "Unknown")
            topic_groups[topic].append(idx)

    total_valid = sum(len(v) for v in topic_groups.values())
    topic_sizes = {k: len(v) for k, v in topic_groups.items()}
    quotas = _compute_quotas(topic_sizes, n)

    print(f"  Valid records (non-empty): {total_valid}")
    print("  Topic quotas:")
    for topic in sorted(topic_sizes, key=lambda x: -topic_sizes[x]):
        sz = topic_sizes[topic]
        q  = quotas.get(topic, 0)
        pct = 100 * sz / total_valid
        print(f"    {topic:<12} {sz:>7} ({pct:5.1f}%)  ->  quota {q}")

    results = []
    for topic, quota in quotas.items():
        if quota == 0:
            continue
        pool = list(topic_groups[topic])
        picked = rng.sample(pool, min(quota, len(pool)))
        for idx in picked:
            rec = build_record(data[idx])
            if rec:
                results.append(rec)

    rng.shuffle(results)
    return results


def simple_sample(
    data: List[Dict[str, Any]], n: int, rng: random.Random
) -> List[Dict[str, Any]]:
    """Simple random sample (filters empty dialogues first)."""
    valid = [i for i, item in enumerate(data)
             if any(m.get("role") in ("user", "assistant") and m.get("content", "").strip()
                    for m in item.get("messages", []))]
    picked = rng.sample(valid, min(n, len(valid)))
    results = []
    for idx in picked:
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
        description="Sample SoulChat raw data to Mind-Eval JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input_path",
        default="data/SoulChat/raw/SoulChatCorpus-sft-multi-Turn.json",
    )
    parser.add_argument("--output_path", default=None)
    parser.add_argument("--n",     type=int, default=10)
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--no_stratified", action="store_true", default=False)
    args = parser.parse_args()

    n   = args.n
    rng = random.Random(args.seed)
    out = Path(args.output_path) if args.output_path else \
          Path(f"data/SoulChat/test/interactions_{n if n > 0 else 'all'}.jsonl")

    print(f"Loading {args.input_path} (may take a moment)...")
    with open(args.input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data):,} raw records loaded.")

    if n == 0 or n >= len(data):
        print("  Converting all records...")
        records = [r for item in data for r in [build_record(item)] if r]
    elif args.no_stratified:
        print(f"  Simple random sample: n={n}, seed={args.seed}")
        records = simple_sample(data, n, rng)
    else:
        print(f"  Topic-stratified sample: n={n}, seed={args.seed}")
        records = stratified_sample(data, n, rng)

    print(f"  Sampled {len(records)} records.")
    save_jsonl(records, out)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
