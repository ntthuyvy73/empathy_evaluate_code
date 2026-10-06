"""
Convert SMILE dataset (200 individual conversation JSON files) to a single
200-record canonical JSONL file for mind_eval evaluation.

Dataset: SmileChat (EMNLP 2024 Findings)
  - 200 files named <id>.json in the raw/ directory (ids are not contiguous:
    13, 27, and 182 are absent from the 0-202 range)
  - Each file is a list of turns: {role, content, annotation}
  - Language: Chinese (zh)
  - Origin: synthetic — ChatGPT rewrote public single-turn QA into multi-turn
    counseling dialogues using the SMILE method

Output schema per record:
  interaction_id : "smile_<file_id>"
  interaction    : [{role, content}, ...]   (annotation stripped)
  metadata       : {source, language, turn_count, origin_type,
                    original_id, length_bucket}
  extra          : {}

Output: test/interactions_200_canonical.jsonl
Sorted globally by turn_count ascending so the shortest (cheapest) records
come first — ready for priority evaluation runs.
"""

import json
from pathlib import Path

RAW_DIR = Path(__file__).parent
OUTPUT_DIR = RAW_DIR.parent / "test"
OUTPUT_JSONL = OUTPUT_DIR / "interactions_200_canonical.jsonl"


def length_bucket(turn_count: int) -> str:
    if turn_count <= 4:
        return "short"
    elif turn_count <= 10:
        return "medium"
    else:
        return "long"


def parse_turns(raw: list) -> list[dict]:
    """Strip annotation; keep only role and content."""
    turns = []
    for item in raw:
        turns.append({"role": item["role"], "content": item["content"]})
    return turns


def main() -> None:
    json_files = sorted(
        [f for f in RAW_DIR.glob("*.json") if f.stem.isdigit()],
        key=lambda f: int(f.stem),
    )

    records: list[dict] = []
    for fpath in json_files:
        raw: list = json.loads(fpath.read_text(encoding="utf-8"))
        turns = parse_turns(raw)
        tc = len(turns)
        records.append(
            {
                "interaction_id": f"smile_{fpath.stem}",
                "interaction": turns,
                "metadata": {
                    "source": "smile",
                    "language": "zh",
                    "turn_count": tc,
                    "origin_type": "synthetic",
                    "original_id": fpath.stem,
                    "length_bucket": length_bucket(tc),
                },
                "extra": {},
            }
        )

    # Sort by turn_count ascending (shortest first)
    records.sort(key=lambda r: r["metadata"]["turn_count"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} records to {OUTPUT_JSONL}\n")

    from collections import Counter
    bucket_counts = Counter(r["metadata"]["length_bucket"] for r in records)
    print("Length buckets:")
    for bucket in ("short", "medium", "long"):
        print(f"  {bucket:<8s}: {bucket_counts[bucket]}")

    turn_counts = [r["metadata"]["turn_count"] for r in records]
    print(f"\nTurn count  min={min(turn_counts)}  max={max(turn_counts)}"
          f"  mean={sum(turn_counts)/len(turn_counts):.1f}")


if __name__ == "__main__":
    main()
