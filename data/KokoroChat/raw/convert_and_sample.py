"""
Convert KokoroChat dialogues to the canonical JSONL format used in mind-eval
and sample 200 records with the following layout:

  Rows 1–20   : SHORT dialogues (turn_count ≤ 30), randomly ordered — evaluated first
  Rows 21–200 : MEDIUM dialogues (31 ≤ turn_count ≤ 70), randomly ordered

Both groups are stratified by client feedback score across 5 bins so the
quality distribution is representative.  Long dialogues (> 70 turns) are
excluded from this sample.

Source schema (per line in Kokorochat_dialogues.jsonl):
  dialogue          : [{role, time, utterance}, ...]
  topic             : {main_jp, main_en, sub}
  review_by_client_en: {evaluation_id, score (0-100), 20 feedback dimensions, ...}

Output schema (interactions_200_canonical.jsonl):
  interaction_id : "kokorochat_{evaluation_id}"
  interaction    : [{role, content}, ...]  — consecutive same-role utterances merged
  metadata       : {source, language, turn_count, origin_type, original_id, length_bucket}
  extra          : {score, topic_main, topic_sub, + 20 feedback dimensions}
"""

import json
import random
from collections import defaultdict
from pathlib import Path

INPUT_JSONL  = Path(__file__).parent / "Kokorochat_dialogues.jsonl"
OUTPUT_DIR   = Path(__file__).parent.parent / "test"
OUTPUT_JSONL = OUTPUT_DIR / "interactions_200_canonical.jsonl"

N_SHORT  = 20   # first rows  — short dialogues (≤ 30 turns)
N_MEDIUM = 180  # remaining   — medium dialogues (31-70 turns)
SEED = 42

# Ethical-flag fields to omit from extra (empty strings, not useful for judge)
_OMIT_FIELDS = {
    "evaluation_id", "evaluation_created_at",
    "client_id", "counselor_id", "score",
    "harmful_due_to_ignorance", "other_potentially_unethical", "unwilling_to_continue",
}


def length_bucket(turn_count: int) -> str:
    if turn_count <= 30:
        return "short"
    elif turn_count <= 70:
        return "medium"
    else:
        return "long"


def merge_consecutive_turns(raw_turns: list[dict]) -> list[dict]:
    """Merge consecutive utterances from the same role into one content block."""
    merged: list[dict] = []
    for turn in raw_turns:
        role = turn.get("role", "")
        text = turn.get("utterance", "").strip()
        if not text:
            continue
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] += " " + text
        else:
            merged.append({"role": role, "content": text})
    return merged


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  Warning: JSON parse error on line {lineno}: {e}")
                continue

            eval_en = obj.get("review_by_client_en", {})
            score = eval_en.get("score")
            if score is None:
                continue

            interaction = merge_consecutive_turns(obj.get("dialogue", []))
            turn_count  = len(interaction)
            eval_id     = eval_en.get("evaluation_id", lineno)
            topic       = obj.get("topic", {})

            feedback_dims = {
                k: v for k, v in eval_en.items() if k not in _OMIT_FIELDS
            }

            record = {
                "interaction_id": f"kokorochat_{eval_id}",
                "interaction": interaction,
                "metadata": {
                    "source": "KokoroChat",
                    "language": "ja",
                    "turn_count": turn_count,
                    "origin_type": "human_roleplay",
                    "original_id": str(eval_id),
                    "length_bucket": length_bucket(turn_count),
                },
                "extra": {
                    "score": score,
                    "topic_main": topic.get("main_en", ""),
                    "topic_sub": topic.get("sub", ""),
                    **feedback_dims,
                },
            }
            records.append(record)
    return records


def stratified_sample(pool: list[dict], n: int, label: str) -> list[dict]:
    """
    Sample n records from pool, stratified over 5 score bins.
    Within each bin, round-robin by topic_main for topic diversity.
    Returns the sampled list in random order (shuffled after collection).
    """
    bins = [
        (0,   60),
        (60,  70),
        (70,  80),
        (80,  90),
        (90, 101),
    ]
    per_bin = n // len(bins)
    remainder = n % len(bins)   # distribute leftover to lower bins
    sampled: list[dict] = []

    for i, (lo, hi) in enumerate(bins):
        bin_pool = [r for r in pool if lo <= r["extra"]["score"] < hi]
        random.shuffle(bin_pool)
        target = per_bin + (1 if i < remainder else 0)

        by_topic: dict[str, list[dict]] = defaultdict(list)
        for r in bin_pool:
            by_topic[r["extra"]["topic_main"]].append(r)

        queues = list(by_topic.values())
        chosen: list[dict] = []
        qi = 0
        while len(chosen) < target:
            if all(len(q) == 0 for q in queues):
                break
            q = queues[qi % len(queues)]
            if q:
                chosen.append(q.pop(0))
            qi += 1

        print(
            f"  [{label}] Score [{lo:3d},{hi:3d}): "
            f"{len(bin_pool):5d} avail, "
            f"{len(chosen):3d} sampled, "
            f"{len(by_topic):2d} topics"
        )
        sampled.extend(chosen)

    random.shuffle(sampled)
    return sampled


def print_stats(sampled: list[dict]) -> None:
    scores  = [r["extra"]["score"] for r in sampled]
    topics  = defaultdict(int)
    lengths = defaultdict(int)
    for r in sampled:
        topics[r["extra"]["topic_main"]] += 1
        lengths[r["metadata"]["length_bucket"]] += 1

    print(f"\n  Total records   : {len(sampled)}")
    print(f"  Avg score       : {sum(scores)/len(scores):.1f}")
    print(f"  Min/Max score   : {min(scores)}/{max(scores)}")
    print(f"  Length buckets  : {dict(sorted(lengths.items()))}")
    print(f"  Topics ({len(topics)} total):")
    for t, cnt in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"    {cnt:3d}  {t}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading records from: {INPUT_JSONL}")
    all_records = load_records(INPUT_JSONL)
    print(f"  Loaded {len(all_records)} valid records")

    short_pool  = [r for r in all_records if r["metadata"]["length_bucket"] == "short"]
    medium_pool = [r for r in all_records if r["metadata"]["length_bucket"] == "medium"]
    long_pool   = [r for r in all_records if r["metadata"]["length_bucket"] == "long"]
    print(f"  short={len(short_pool)}, medium={len(medium_pool)}, long={len(long_pool)}")

    random.seed(SEED)

    print(f"\nSampling {N_SHORT} SHORT records (rows 1-{N_SHORT}):")
    short_sampled = stratified_sample(short_pool, N_SHORT, "short")

    print(f"\nSampling {N_MEDIUM} MEDIUM records (rows {N_SHORT+1}-200):")
    medium_sampled = stratified_sample(medium_pool, N_MEDIUM, "medium")

    # Final order: short first, then medium
    sampled = short_sampled + medium_sampled
    total = len(sampled)

    print(f"\nSample statistics ({total} total):")
    print_stats(sampled)

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for rec in sampled:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nWrote {total} records -> {OUTPUT_JSONL}")
    print(f"  Rows  1-{N_SHORT:3d} : short  (turn_count <= 30)")
    print(f"  Rows {N_SHORT+1:3d}-200 : medium (turn_count 31-70)")


if __name__ == "__main__":
    main()
