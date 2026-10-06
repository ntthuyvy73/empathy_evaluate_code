"""
One-time backfill: add interaction_id to existing judgment files that pre-date
the generate_judgments.py fix.

Strategy: for each (dataset, setting) pair, read the corresponding input
interactions file and inject the interaction_id from position i into
judgment record i.  This is safe because the pilot N=20 records were run
sequentially with no gaps or retries.

The script:
  - Creates a .bak copy of each judgment file before modifying it.
  - Skips judgment records that already have interaction_id.
  - Skips if the input interactions file is missing.
  - Reports a count mismatch warning instead of silently proceeding.

Usage:
    python -m mindeval.scripts.backfill_interaction_ids [--dry_run]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Mapping: (dataset_folder_name, setting) → interactions input file
# Mirrors the DATASETS registry in evaluate.py
# ---------------------------------------------------------------------------
JUDGMENT_INPUT_MAP: dict[tuple[str, str], str] = {
    # simpsydial
    ("simpsydial", "S1"): "data/simpsydial/test/interactions_200_S1_en.jsonl",
    ("simpsydial", "S2"): "data/simpsydial/test/interactions_200_canonical.jsonl",
    ("simpsydial", "S3"): "data/simpsydial/test/interactions_200_canonical.jsonl",
    # KMI
    ("KMI", "S1"): "data/KMI/test/interactions_200_S1_en.jsonl",
    ("KMI", "S2"): "data/KMI/test/interactions_200_canonical_ko.jsonl",
    ("KMI", "S3"): "data/KMI/test/interactions_200_canonical_ko.jsonl",
    # SoulChat
    ("SoulChat", "S1"): "data/SoulChat/test/interactions_200_S1_en.jsonl",
    ("SoulChat", "S2"): "data/SoulChat/test/interactions_200_canonical.jsonl",
    ("SoulChat", "S3"): "data/SoulChat/test/interactions_200_canonical.jsonl",
    # cactus
    ("cactus", "S1"): "data/cactus/test/interactions_200_canonical.jsonl",
    ("cactus", "S3"): "data/cactus/test/interactions_200_canonical.jsonl",
    # Psy-Insight
    ("Psy-Insight", "S1"): "data/Psy-Insight/test/interactions_200_canonical.jsonl",
    ("Psy-Insight", "S3"): "data/Psy-Insight/test/interactions_200_canonical.jsonl",
    # PsyDial
    ("PsyDial", "S1"): "data/PsyDial/test/interactions_200_S1_en.jsonl",
    ("PsyDial", "S2"): "data/PsyDial/test/interactions_200_canonical.jsonl",
    ("PsyDial", "S3"): "data/PsyDial/test/interactions_200_canonical.jsonl",
}


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_jsonl(records: list[dict], path: pathlib.Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def backfill_file(
    judgment_path: pathlib.Path,
    input_path: pathlib.Path,
    dry_run: bool,
) -> str:
    """
    Returns a one-line status string.
    """
    if not input_path.exists():
        return f"SKIP  (input missing: {input_path.name})"

    judgments = _load_jsonl(judgment_path)
    interactions = _load_jsonl(input_path)

    # Check how many judgment records already have interaction_id
    already_have = sum(1 for j in judgments if "interaction_id" in j)
    if already_have == len(judgments):
        return f"OK    (all {len(judgments)} records already have interaction_id)"

    if len(judgments) > len(interactions):
        return (
            f"ERROR (judgment count {len(judgments)} > input count {len(interactions)})"
            " — manual review needed"
        )

    # Extract IDs from input, first N entries (N = len(judgments))
    ids_to_inject = [
        rec.get("interaction_id", f"record_{i}")
        for i, rec in enumerate(interactions[: len(judgments)])
    ]

    updated = []
    injected = 0
    for i, (jrec, iid) in enumerate(zip(judgments, ids_to_inject)):
        new_rec = dict(jrec)
        if "interaction_id" not in new_rec:
            # Insert interaction_id as the first key
            new_rec = {"interaction_id": iid, **new_rec}
            injected += 1
        updated.append(new_rec)

    if dry_run:
        return f"DRY   would inject {injected} IDs  (already had {already_have})"

    # Backup original
    bak_path = judgment_path.with_suffix(".jsonl.bak")
    if not bak_path.exists():
        shutil.copy2(judgment_path, bak_path)

    _write_jsonl(updated, judgment_path)
    return f"DONE  injected {injected} IDs  (bak: {bak_path.name})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry_run", action="store_true",
        help="Show what would be changed without writing files",
    )
    args = parser.parse_args()

    print("=" * 68)
    print("backfill_interaction_ids")
    if args.dry_run:
        print("DRY RUN — no files will be written")
    print("=" * 68)

    # Scan all existing mind_eval judgment files
    results_glob = sorted(ROOT.glob("data/*/results/mind_eval/*_judgments.jsonl"))

    for judgment_path in results_glob:
        # Extract dataset name and setting from path
        # data/<dataset>/results/mind_eval/<SETTING>_judgments.jsonl
        parts = judgment_path.parts
        dataset = parts[-4]        # e.g. "KMI"
        setting = parts[-1].split("_")[0]  # e.g. "S1"

        key = (dataset, setting)
        input_rel = JUDGMENT_INPUT_MAP.get(key)

        if input_rel is None:
            status = f"SKIP  (no input mapping for {dataset}/{setting})"
        else:
            input_path = ROOT / input_rel
            status = backfill_file(judgment_path, input_path, dry_run=args.dry_run)

        rel = judgment_path.relative_to(ROOT)
        print(f"  {str(rel):<55s}  {status}")

    print("=" * 68)
    if not args.dry_run:
        print("Backup files (.bak) saved alongside originals.")
        print("To remove backups after verifying: del data\\*\\results\\mind_eval\\*.bak")
    print("=" * 68)


if __name__ == "__main__":
    main()
