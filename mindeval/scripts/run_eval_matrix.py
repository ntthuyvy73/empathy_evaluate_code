"""
Run the S1 / S2 / S3 evaluation matrix across datasets.

Wraps evaluate.py so you can launch pilot or full runs without typing
each command manually.

Pilot mode (--pilot, default):
    Uses --max_dialogues N (default 5, override with --pilot_n) so S2/S3/KMI/EN
    datasets align with the ZH S1 translation pilot. ZH S1 files are capped by
    translate_to_en --limit N, so no max_dialogues is applied there.

Full mode (--full):
    Evaluates every record in each interactions file. Requires full S1
    translation for ZH datasets first:
        python -m mindeval.scripts.translate_to_en

WAI settings:
    WAI always uses English prompts, so S2 (native-language judge) is not
    applicable. When --eval wai, only S1 and S3 jobs are generated.
    S1 WAI uses the EN-translated dialogue file (interactions_200_S1_en.jsonl).
    --wai_pilot_n controls the WAI pilot size (default 20, matching S3 WAI pilot).
    ZH S1 files are pre-sized at 20 records by translate_to_en, so no cap needed.

Usage
-----
    # Pilot: Dim-A only, all applicable dataset × setting pairs
    python -m mindeval.scripts.run_eval_matrix --pilot --eval mind-eval

    # Pilot: Dim-A + Dim-B (WAI is token-heavy)
    python -m mindeval.scripts.run_eval_matrix --pilot --eval both

    # WAI S1 pilot only (non-EN datasets: EN-translated dialogue + EN WAI prompts)
    python -m mindeval.scripts.run_eval_matrix --pilot --eval wai --settings S1

    # WAI S1 + S3 pilot
    python -m mindeval.scripts.run_eval_matrix --pilot --eval wai --settings S1 S3

    # Single dataset, all settings
    python -m mindeval.scripts.run_eval_matrix --pilot --datasets kmi --eval mind-eval

    # Full run (after S1 translation complete)
    python -m mindeval.scripts.run_eval_matrix --full --eval mind-eval

    # Dry-run: print commands without executing
    python -m mindeval.scripts.run_eval_matrix --pilot --dry_run
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# WAI uses English prompts for all settings; S2 (native judge) is not meaningful.
# Only S1 (EN dialogue + EN WAI prompts) and S3 (native dialogue + EN WAI prompts)
# are generated when --eval wai.
WAI_SETTINGS: frozenset[str] = frozenset({"S1", "S3"})

# (dataset_key, list of settings to RUN, language)
# EN datasets: run S1; S3 is added so --settings S3 includes them (S1=S3 for EN).
# copy_en_results() copies mind_eval S1 → S3 after all jobs complete.
# For WAI: EN datasets run with S3 directly (same canonical file, EN prompts).
MATRIX: list[tuple[str, list[str], str]] = [
    ("simpsydial",  ["S1", "S2", "S3"], "zh"),
    ("psydial",     ["S1", "S2", "S3"], "zh"),
    ("soulchat",    ["S1", "S2", "S3"], "zh"),
    ("cpscycoun",   ["S1", "S2", "S3"], "zh"),  # ZH semi-real: S1 file pre-sized at 20 records
    ("smile",       ["S1", "S2", "S3"], "zh"),  # ZH LLM-expanded: S1 file pre-sized at 20 records
    ("kmi",         ["S1", "S2", "S3"], "ko"),
    ("kokorochat",  ["S1", "S2", "S3"], "ja"),  # JA human role-play: S1 file pre-sized at 20 records
    ("cactus",      ["S1", "S3"],       "en"),  # EN: S1=S3 conceptually; copy_en_results handles mind_eval
    ("psy_insight", ["S1", "S3"],       "en"),  # EN: same as cactus
    ("annomi",      ["S1", "S3"],       "en"),  # EN: real MI transcripts, S1=S3
    ("esconv",      ["S1", "S3"],       "en"),  # EN: crowdsourced emotional support, S1=S3
]

# Folder names under data/ for each dataset key
DATASET_DIRS = {
    "simpsydial":  "simpsydial",
    "psydial":     "PsyDial",
    "soulchat":    "SoulChat",
    "cpscycoun":   "CPsyCoun",
    "smile":       "smile",
    "kmi":         "KMI",
    "kokorochat":  "KokoroChat",
    "cactus":      "cactus",
    "psy_insight": "Psy-Insight",
    "annomi":      "AnnoMI",
    "esconv":      "ESConv",
}


def copy_en_results(root: Path, judge_name: str | None = None) -> None:
    """
    For EN datasets, copy mind_eval and WAI S1 → S3 (same input + same EN judge).

    S1 (EN↔EN) = S3 (NL→EN) for EN datasets because NL = EN.
    S2 (NL↔NL) is NOT created for EN datasets.

    File naming convention: <dataset_folder>_<setting>_<judge>_judgments.jsonl
    e.g. cactus_S1_gpt_judgments.jsonl → cactus_S3_gpt_judgments.jsonl
    """
    effective_judge = judge_name or "gpt"
    for ds_key, _, lang in MATRIX:
        if lang != "en":
            continue
        ds_dir = root / "data" / DATASET_DIRS[ds_key]
        ds_folder = ds_dir.name  # actual folder name (e.g. "cactus", "AnnoMI")
        # ── mind_eval: copy S1 → S3 ──────────────────────────────────────
        me_src = ds_dir / "results" / "mind_eval" / f"{ds_folder}_S1_{effective_judge}_judgments.jsonl"
        if me_src.exists():
            me_dst = me_src.parent / f"{ds_folder}_S3_{effective_judge}_judgments.jsonl"
            shutil.copy2(me_src, me_dst)
            print(f"  [copy] {me_src.name} -> {me_dst.name}  ({ds_folder}) [mind_eval]")
        # ── WAI: copy S1 → S3 ────────────────────────────────────────────
        wai_src = ds_dir / "results" / "wai" / f"{ds_folder}_S1_{effective_judge}_wai_judgments.jsonl"
        if wai_src.exists():
            wai_dst = wai_src.parent / f"{ds_folder}_S3_{effective_judge}_wai_judgments.jsonl"
            if not wai_dst.exists():
                shutil.copy2(wai_src, wai_dst)
                print(f"  [copy] {wai_src.name} -> {wai_dst.name}  ({ds_folder}) [wai]")
        # ── Remove stale S2 for EN datasets ──────────────────────────────
        for results_subdir in ("mind_eval", "wai"):
            stale_suffix = "_wai_judgments.jsonl" if results_subdir == "wai" else "_judgments.jsonl"
            stale = ds_dir / "results" / results_subdir / f"{ds_folder}_S2_{effective_judge}{stale_suffix}"
            if stale.exists():
                stale.unlink()
                print(f"  [rm]   Removed stale {results_subdir}/{stale.name}  ({ds_folder})")

DEFAULT_PILOT_N = 5
DEFAULT_WAI_PILOT_N = 20


def build_jobs(
    datasets: list[str],
    settings: list[str] | None,
    pilot: bool,
    pilot_n: int,
    eval_type: str = "mind-eval",
    wai_pilot_n: int = DEFAULT_WAI_PILOT_N,
) -> list[tuple[str, str, int | None]]:
    """Return list of (dataset, setting, max_dialogues).

    eval_type controls pilot-size logic and setting filtering:
      - "mind-eval": classic logic; S2 included; pilot_n applies.
      - "wai"       : skip S2 (WAI always uses EN prompts); wai_pilot_n applies;
                      ZH/JA S1 files are pre-sized at 20 → no cap needed.
      - "both"      : use mind-eval sizing (S2 included); WAI portion of each
                      job mirrors mind-eval since evaluate.py handles both in one call.

    EN datasets: S1 = S3 (same canonical file, no translation).
      For both mind-eval and WAI, only S1 is scheduled — copy_en_results()
      copies S1 → S3 after all jobs complete, avoiding duplicate API calls.
    """
    # Datasets whose S1 translation files are pre-sized (translate_to_en --limit N)
    PRE_SIZED_S1 = {"simpsydial", "psydial", "soulchat", "cpscycoun", "smile", "kokorochat"}
    jobs: list[tuple[str, str, int | None]] = []
    for ds, opts, lang in MATRIX:
        if ds not in datasets:
            continue
        for opt in opts:
            if settings and opt not in settings:
                continue
            # WAI: skip S2 — native-language judge not applicable to WAI prompts
            if eval_type == "wai" and opt not in WAI_SETTINGS:
                continue
            # WAI + EN: S1 = S3 (same canonical file, EN prompts). Skip S3 when user
            # did NOT explicitly request S3 (i.e. default/no --settings flag).
            # If user explicitly passes --settings S3, honour it to create _S3_ files.
            if eval_type == "wai" and lang == "en" and opt == "S3" and not settings:
                continue
            # Pilot sizing
            if eval_type == "wai":
                if pilot and opt == "S1" and lang in ("zh", "ja"):
                    # ZH/JA S1 files pre-sized at 20 records by translate_to_en
                    max_d = None
                elif pilot:
                    max_d = wai_pilot_n
                else:
                    max_d = None
            else:
                # mind-eval (and "both"): pre-sized S1 files → judge all in file
                if pilot and opt == "S1" and ds in PRE_SIZED_S1:
                    max_d = None
                elif pilot:
                    max_d = pilot_n
                else:
                    max_d = None
            jobs.append((ds, opt, max_d))
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run S1/S2/S3 evaluation matrix.")
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=[ds for ds, _, _ in MATRIX],
        choices=[ds for ds, _, _ in MATRIX],
        help="Datasets to evaluate (default: all)",
    )
    parser.add_argument(
        "--settings",
        nargs="+",
        choices=["S1", "S2", "S3"],
        default=None,
        help="Settings to run (default: all available per dataset)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pilot", action="store_true",
                      help="Pilot run with max_dialogues=N (default if neither flag given)")
    mode.add_argument("--full", action="store_true",
                      help="Full run — all records in each file")
    parser.add_argument(
        "--pilot_n",
        type=int,
        default=DEFAULT_PILOT_N,
        help=f"Pilot size for mind-eval S2/S3/KMI/EN (default: {DEFAULT_PILOT_N})",
    )
    parser.add_argument(
        "--wai_pilot_n",
        type=int,
        default=DEFAULT_WAI_PILOT_N,
        help=f"Pilot size for WAI S1/S3 (KO/EN datasets). "
             f"ZH S1 files are pre-sized by translate_to_en. (default: {DEFAULT_WAI_PILOT_N})",
    )
    parser.add_argument("--eval", choices=["mind-eval", "wai", "both"], default="mind-eval",
                        help="Evaluation type (default: mind-eval)")
    parser.add_argument("--config_path", default="config.json")
    parser.add_argument("--max_workers", type=int, default=3,
                        help="Parallel workers for Dim-A (default: 3)")
    parser.add_argument("--wai_n_runs", type=int, default=3)
    parser.add_argument("--judge_name", default=None,
                        help="Named judge from config 'judges' section (e.g. 'claude'). "
                             "Output: <S>_<judge>_judgments.jsonl for all settings.")
    parser.add_argument("--batch_delay", type=float, default=0.0,
                        help="Seconds to sleep between batches (default: 0). "
                             "Use 3-5 for Anthropic Tier-1 (30k tokens/min limit).")
    parser.add_argument("--dry_run", action="store_true",
                        help="Print commands without executing")
    parser.add_argument("--no_skip", action="store_true",
                        help="Re-evaluate already-judged dialogues")
    parser.add_argument("--no_wai_batch", action="store_true",
                        help="Disable WAI batch mode (12 questions per call). "
                             "Use for models that reject long batch prompts (e.g. some Gemini).")
    args = parser.parse_args()

    pilot = not args.full  # default: pilot mode
    jobs = build_jobs(
        args.datasets,
        args.settings,
        pilot=pilot,
        pilot_n=args.pilot_n,
        eval_type=args.eval,
        wai_pilot_n=args.wai_pilot_n,
    )

    print("=" * 60)
    print("run_eval_matrix")
    print("=" * 60)
    pilot_label = f"pilot (N={args.pilot_n}, WAI N={args.wai_pilot_n})" if pilot else "full (all records)"
    print(f"mode       : {pilot_label}")
    print(f"eval       : {args.eval}")
    print(f"judge      : {args.judge_name or 'gpt (default)'}")
    print(f"jobs       : {len(jobs)}")
    print(f"config     : {args.config_path}")
    print("=" * 60)

    root = Path(__file__).resolve().parents[2]  # mind-eval/
    evaluate_py = root / "evaluate.py"

    if not evaluate_py.exists():
        print(f"ERROR: evaluate.py not found at {evaluate_py}")
        sys.exit(1)

    if not args.dry_run and not Path(args.config_path).exists():
        print(f"ERROR: config not found: {args.config_path}")
        sys.exit(1)

    results: list[tuple[str, str, int]] = []
    for i, (ds, opt, max_d) in enumerate(jobs, 1):
        limit_str = f"max={max_d}" if max_d else "all"
        print(f"\n[{i}/{len(jobs)}] {ds} / {opt}  ({limit_str})")

        cmd = [
            sys.executable, str(evaluate_py),
            "--dataset", ds,
            "--option", opt,
            "--eval", args.eval,
            "--config_path", args.config_path,
            "--max_workers", str(args.max_workers),
            "--wai_n_runs", str(args.wai_n_runs),
        ]
        if max_d is not None:
            cmd += ["--max_dialogues", str(max_d)]
        if args.judge_name:
            cmd += ["--judge_name", args.judge_name]
        if args.batch_delay > 0:
            cmd += ["--batch_delay", str(args.batch_delay)]
        if args.no_skip:
            cmd += ["--no_skip"]
        if args.no_wai_batch:
            cmd += ["--no_wai_batch"]
        if not pilot:
            cmd += ["--output_suffix", "_full"]

        print("  " + " ".join(cmd))

        if args.dry_run:
            results.append((ds, opt, 0))
            continue

        rc = subprocess.run(cmd, cwd=str(root)).returncode
        results.append((ds, opt, rc))
        if rc != 0:
            print(f"  [FAILED] exit code {rc}")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if args.dry_run:
        print(f"  {len(jobs)} commands printed (dry run)")
    else:
        ok = sum(1 for _, _, rc in results if rc == 0)
        fail = len(results) - ok
        print(f"  OK: {ok}  FAILED: {fail}")
        for ds, opt, rc in results:
            status = "OK" if rc == 0 else f"FAILED ({rc})"
            print(f"    {ds:14s} {opt}  {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
