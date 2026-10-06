"""
One-time migration: add judge metadata to existing judgment files and rename them
to the new consistent naming convention.

New convention: {setting}_{judge_name}_judgments.jsonl
  e.g. S1_gpt_judgments.jsonl, S2_gpt_judgments.jsonl, S3_gpt_judgments.jsonl

Special case (KMI translation experiment):
  S1_ko_translated_judgments.jsonl → S1_ko_translated_gpt_judgments.jsonl

Properties added to each record (inserted after interaction_id):
  judge_name  : "gpt"       (short identifier matching config 'judges' section key)
  judge_model : "gpt-5.1"   (actual model name from config)

The script:
  - Creates a .bak copy of each file before modifying.
  - Skips records that already have judge_name.
  - Reads judge_model from config.json (judges.gpt.model or judge.model).
  - Prints a dry-run plan when --dry_run is given.

Usage:
    python -m mindeval.scripts.migrate_add_judge_metadata [--dry_run]
    python -m mindeval.scripts.migrate_add_judge_metadata --config_path config.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Rename map: old_name → (new_stem, judge_name)
# All existing files were generated with the default GPT judge.
# ---------------------------------------------------------------------------
# Pattern: (dataset_folder, old_stem) → new_stem
RENAME_MAP: dict[tuple[str, str], str] = {
    # Standard S1/S2/S3 files
    ("cactus",      "S1_judgments"):            "S1_gpt_judgments",
    ("cactus",      "S3_judgments"):            "S3_gpt_judgments",
    ("KMI",         "S1_judgments"):            "S1_gpt_judgments",
    ("KMI",         "S2_judgments"):            "S2_gpt_judgments",
    ("KMI",         "S3_judgments"):            "S3_gpt_judgments",
    ("KMI",         "S1_ko_translated_judgments"): "S1_ko_translated_gpt_judgments",
    ("Psy-Insight", "S1_judgments"):            "S1_gpt_judgments",
    ("Psy-Insight", "S3_judgments"):            "S3_gpt_judgments",
    ("PsyDial",     "S1_judgments"):            "S1_gpt_judgments",
    ("PsyDial",     "S2_judgments"):            "S2_gpt_judgments",
    ("PsyDial",     "S3_judgments"):            "S3_gpt_judgments",
    ("simpsydial",  "S1_judgments"):            "S1_gpt_judgments",
    ("simpsydial",  "S2_judgments"):            "S2_gpt_judgments",
    ("simpsydial",  "S3_judgments"):            "S3_gpt_judgments",
    ("SoulChat",    "S1_judgments"):            "S1_gpt_judgments",
    ("SoulChat",    "S2_judgments"):            "S2_gpt_judgments",
    ("SoulChat",    "S3_judgments"):            "S3_gpt_judgments",
}

DEFAULT_JUDGE_NAME  = "gpt"


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


def _resolve_judge_model(config_path: pathlib.Path, judge_name: str) -> str:
    """Read judge model string from config.json."""
    if not config_path.exists():
        return "unknown"
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    # Try named judge first, then default judge section
    named = cfg.get("judges", {}).get(judge_name, {})
    if named.get("model"):
        return named["model"]
    return cfg.get("judge", {}).get("model", "unknown")


def migrate_file(
    src: pathlib.Path,
    dst: pathlib.Path,
    judge_name: str,
    judge_model: str,
    dry_run: bool,
) -> str:
    records = _load_jsonl(src)
    already = sum(1 for r in records if "judge_name" in r)
    if already == len(records) and src == dst:
        return f"SKIP   (all {len(records)} records already have judge_name)"

    updated = []
    injected = 0
    for rec in records:
        if "judge_name" not in rec:
            # Insert judge fields after interaction_id
            new_rec: dict = {}
            for k, v in rec.items():
                new_rec[k] = v
                if k == "interaction_id":
                    new_rec["judge_name"]  = judge_name
                    new_rec["judge_model"] = judge_model
            injected += 1
        else:
            new_rec = dict(rec)
        updated.append(new_rec)

    rename_note = f"  rename: {src.name} -> {dst.name}" if src != dst else ""
    if dry_run:
        return f"DRY    inject={injected}/{len(records)}{rename_note}"

    # Backup original (only once)
    bak = src.with_suffix(".jsonl.bak")
    if not bak.exists():
        shutil.copy2(src, bak)

    _write_jsonl(updated, dst)
    # Remove old file only after successfully writing new one
    if src != dst and src.exists():
        src.unlink()

    return f"DONE   inject={injected}/{len(records)}{rename_note}  (bak: {bak.name})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry_run", action="store_true",
                        help="Print plan without writing files")
    parser.add_argument("--config_path", default="config.json")
    args = parser.parse_args()

    config_path = ROOT / args.config_path
    judge_model = _resolve_judge_model(config_path, DEFAULT_JUDGE_NAME)

    print("=" * 70)
    print("migrate_add_judge_metadata")
    if args.dry_run:
        print("DRY RUN — no files will be modified")
    print(f"judge_name  : {DEFAULT_JUDGE_NAME}")
    print(f"judge_model : {judge_model}  (from {args.config_path})")
    print("=" * 70)

    for (dataset, old_stem), new_stem in RENAME_MAP.items():
        results_dir = ROOT / "data" / dataset / "results" / "mind_eval"
        src = results_dir / f"{old_stem}.jsonl"
        dst = results_dir / f"{new_stem}.jsonl"

        if not src.exists():
            # Check if already migrated (dst exists, src gone)
            if dst.exists():
                status = "ALREADY_MIGRATED"
            else:
                status = "MISSING"
            print(f"  {dataset}/{old_stem}.jsonl  ->  {new_stem}.jsonl  [{status}]")
            continue

        status = migrate_file(src, dst, DEFAULT_JUDGE_NAME, judge_model, args.dry_run)
        print(f"  {dataset}/{old_stem:<40s}  [{status}]")

    print("=" * 70)
    if not args.dry_run:
        print("Migration complete. Backups (.bak) saved alongside originals.")
        print("Remove backups after verifying: del data\\*\\results\\mind_eval\\*.bak")
    print("=" * 70)


if __name__ == "__main__":
    main()
