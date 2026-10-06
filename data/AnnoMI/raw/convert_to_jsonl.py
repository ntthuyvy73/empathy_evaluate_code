"""
Convert AnnoMI-full.csv to JSONL format consistent with other datasets in the project.

Mapping:
  - interlocutor "therapist" -> role "counselor"
  - interlocutor "client"    -> role "client"

Each record = one transcript (conversation), grouped by transcript_id.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

INPUT_CSV  = Path(__file__).parent / "AnnoMI-full.csv"
OUTPUT_JSONL = Path(__file__).parent / "AnnoMI.jsonl"


def length_bucket(turn_count: int) -> str:
    if turn_count <= 15:
        return "short"
    elif turn_count <= 30:
        return "medium"
    else:
        return "long"


def convert():
    # Read all rows
    rows = []
    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # Group by transcript_id
    transcripts: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        transcripts[row["transcript_id"]].append(row)

    records = []
    for tid, t_rows in sorted(transcripts.items(), key=lambda x: int(x[0])):
        # Sort utterances by utterance_id (numeric)
        t_rows.sort(key=lambda r: int(r["utterance_id"]))

        # Pick metadata from first row (shared across utterances)
        first = t_rows[0]
        mi_quality   = first["mi_quality"]
        video_title  = first["video_title"]
        video_url    = first["video_url"]
        topic        = first["topic"]
        annotator_id = first["annotator_id"]

        # Build interaction turns
        interaction = []
        for r in t_rows:
            role = "counselor" if r["interlocutor"] == "therapist" else "client"
            interaction.append({
                "role": role,
                "content": r["utterance_text"],
            })

            # (utterance-level annotation fields omitted from output —
        #  they are not sent to the judge and inflate file size)

        turn_count = len(interaction)

        record = {
            "interaction_id": f"annomi_{tid}",
            "interaction": interaction,
            "metadata": {
                "source": "AnnoMI",
                "language": "en",
                "turn_count": turn_count,
                "origin_type": "real",
                "original_id": tid,
                "length_bucket": length_bucket(turn_count),
            },
            "extra": {
                "mi_quality": mi_quality,
                "topic": topic,
                "video_title": video_title,
                "video_url": video_url,
                "annotator_id": annotator_id,
            },
        }
        records.append(record)

    # Write JSONL
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} records to {OUTPUT_JSONL}")

    # Summary stats
    buckets = defaultdict(int)
    qualities = defaultdict(int)
    for rec in records:
        buckets[rec["metadata"]["length_bucket"]] += 1
        qualities[rec["extra"]["mi_quality"]] += 1
    print(f"Length buckets: {dict(buckets)}")
    print(f"MI quality:     {dict(qualities)}")


if __name__ == "__main__":
    convert()
