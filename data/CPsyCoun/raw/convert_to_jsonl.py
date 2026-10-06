"""
Convert CPsyCounE evaluation data (45 conversations, 9 topics x 5 files) to
a 200-record JSONL file for mind_eval and WAI evaluation.

Sampling strategy:
  - All 9 topics are equally represented (~22 records each, >20 per topic)
  - All 5 files per topic are used (at least 4 records per file)
  - Within each topic, SHORT and MEDIUM records are prioritised over LONG ones:
      short  (<=4 turns) : all available
      medium (5-10 turns): as many as needed to reach quota
      long   (>10 turns) : only used if short+medium cannot fill the quota
  - Final output is sorted globally by turn_count ascending so the cheapest
    (shortest) records come first -- ready for priority evaluation runs.

Output: test/interactions_200_canonical.jsonl
"""

import json
from collections import Counter
from pathlib import Path

RAW_DIR = Path(__file__).parent / "CPsyCounE"
OUTPUT_DIR = Path(__file__).parent.parent / "test"
OUTPUT_JSONL = OUTPUT_DIR / "interactions_200_canonical.jsonl"

TOPICS = [
    "Career",
    "Education",
    "Emotion&Stress",
    "Family Relationship",
    "Love&Marriage",
    "Mental Disease",
    "Self-growth",
    "Sex",
    "Social Relationship",
]

TARGET_TOTAL = 200
BUCKET_ORDER = {"short": 0, "medium": 1, "long": 2}


def length_bucket(turn_count: int) -> str:
    if turn_count <= 4:
        return "short"
    elif turn_count <= 10:
        return "medium"
    else:
        return "long"


def topic_slug(topic: str) -> str:
    return topic.lower().replace(" ", "_").replace("&", "_")


def parse_turns(raw: list) -> list[dict]:
    """Parse flat alternating list into role/content dicts."""
    turns = []
    for item in raw:
        s = item.strip()
        if s.startswith("\u6c42\u52a9\u8005\uff1a"):
            turns.append({"role": "client", "content": s[4:]})
        elif s.startswith("\u652f\u6301\u8005\uff1a"):
            turns.append({"role": "counselor", "content": s[4:]})
        else:
            role = "client" if len(turns) % 2 == 0 else "counselor"
            turns.append({"role": role, "content": s})
    return turns


def sub_records_for_file(topic: str, file_num: int, turns: list[dict]) -> list[dict]:
    """One record per counselor turn: full context up to and including that turn."""
    slug = topic_slug(topic)
    records = []
    full_len = len(turns)
    for i, turn in enumerate(turns):
        if turn["role"] != "counselor":
            continue
        sub = turns[: i + 1]
        tc = len(sub)
        records.append(
            {
                "interaction_id": f"cpscycoun_{slug}_{file_num}_{i + 1:02d}",
                "interaction": sub,
                "metadata": {
                    "source": "CPsyCoun",
                    "language": "zh",
                    "turn_count": tc,
                    "origin_type": "semi_real",
                    "original_id": f"{topic}/{file_num}.json",
                    "length_bucket": length_bucket(tc),
                },
                "extra": {
                    "topic": topic,
                    "file_num": file_num,
                    "turn_idx": i + 1,
                    "is_final_turn": (i == full_len - 1),
                },
            }
        )
    return records


def pick_short_medium_first(pool: list[dict], n: int) -> list[dict]:
    """
    Take n records from pool, strongly preferring short then medium then long.
    Within each bucket, records are spread evenly across all 5 files so no
    single file dominates.
    """
    by_bucket: dict[str, list[dict]] = {"short": [], "medium": [], "long": []}
    for r in pool:
        by_bucket[r["metadata"]["length_bucket"]].append(r)

    chosen: list[dict] = []
    for bucket in ("short", "medium", "long"):
        remaining = n - len(chosen)
        if remaining <= 0:
            break
        candidates = by_bucket[bucket]
        if not candidates:
            continue
        if len(candidates) <= remaining:
            chosen.extend(candidates)
        else:
            # Evenly-spaced sampling to keep diversity across files
            step = len(candidates) / remaining
            indices = sorted({min(round(i * step), len(candidates) - 1)
                              for i in range(remaining)})
            while len(indices) < remaining:
                nxt = indices[-1] + 1
                if nxt < len(candidates):
                    indices.append(nxt)
            chosen.extend(candidates[i] for i in indices[:remaining])

    return chosen


def main() -> None:
    # ── Load & generate all sub-records per topic ──────────────────────────
    all_by_topic: dict[str, list[dict]] = {}
    for topic in TOPICS:
        topic_dir = RAW_DIR / topic
        pool: list[dict] = []
        for fn in range(1, 6):
            fpath = topic_dir / f"{fn}.json"
            raw: list = json.loads(fpath.read_text(encoding="utf-8"))
            turns = parse_turns(raw)
            pool.extend(sub_records_for_file(topic, fn, turns))
        all_by_topic[topic] = pool

    # ── Distribute 200 records: 22 or 23 per topic, short/medium first ─────
    base = TARGET_TOTAL // len(TOPICS)          # 22
    extra = TARGET_TOTAL - base * len(TOPICS)   # 2

    selected: list[dict] = []
    for idx, topic in enumerate(TOPICS):
        target = base + (1 if idx < extra else 0)
        chosen = pick_short_medium_first(all_by_topic[topic], target)
        selected.extend(chosen)

    # ── Sort globally: round-robin across turn_count groups ────────────────
    # Group by turn_count; within each group sort by (topic, file_num) for
    # consistent ordering. Then interleave groups so that ANY prefix of N
    # records contains a representative mix of dialogue lengths — important
    # for pilot evaluation runs (e.g. --limit 20).
    from collections import defaultdict
    by_turn: dict[int, list[dict]] = defaultdict(list)
    for r in selected:
        by_turn[r["metadata"]["turn_count"]].append(r)
    for tc in by_turn:
        by_turn[tc].sort(key=lambda r: (r["extra"]["topic"], r["extra"]["file_num"]))

    interleaved: list[dict] = []
    groups = [by_turn[tc] for tc in sorted(by_turn)]
    max_len = max(len(g) for g in groups)
    for i in range(max_len):
        for g in groups:
            if i < len(g):
                interleaved.append(g[i])
    selected = interleaved

    # ── Write JSONL ────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for rec in selected:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"Wrote {len(selected)} records to {OUTPUT_JSONL}\n")

    topic_counts = Counter(r["extra"]["topic"] for r in selected)
    bucket_counts = Counter(r["metadata"]["length_bucket"] for r in selected)
    final_counts = Counter(r["extra"]["is_final_turn"] for r in selected)

    print("Records per topic:")
    for t in TOPICS:
        print(f"  {t:<22s}: {topic_counts[t]}")

    print("\nLength buckets (output order: short -> medium -> long):")
    for bucket in ("short", "medium", "long"):
        print(f"  {bucket:<8s}: {bucket_counts[bucket]}")

    print(f"\nFull-conversation records : {final_counts[True]}")
    print(f"Partial-context records   : {final_counts[False]}")


if __name__ == "__main__":
    main()
