"""
Unified evaluation script for all datasets in the data/ folder.

Evaluates existing counseling dialogues using:
  - Mind-Eval 5-metric evaluation (Clinical Accuracy, Ethical Conduct,
    Assessment & Response, Therapeutic Relationship, AI-Specific Communication)
  - WAI 3-dimension evaluation (Goal, Approach, Affective Bond)

Each dataset supports three evaluation settings (S1 / S2 / S3):
    S1 : English dialogue  + English judge   (requires translation for ZH/KO)
    S2 : Native language   + native judge
    S3 : Native language   + English judge   (uses canonical file directly)

Usage examples:
    # Evaluate SimPsyDial (Chinese) with English judge (S3)
    python evaluate.py --dataset simpsydial --option S3 --eval mind-eval

    # Evaluate KMI with all eval types
    python evaluate.py --dataset kmi --option S1 --eval both

    # Evaluate SoulChat, 50 dialogues, WAI only
    python evaluate.py --dataset soulchat --option S3 --eval wai --max_dialogues 50

    # Evaluate cactus (English — S1 = S3)
    python evaluate.py --dataset cactus --option S1 --eval both

    # List available datasets
    python evaluate.py --list

Supported datasets: simpsydial, kmi, soulchat, cactus, psy_insight, psydial, annomi,
                   cpscycoun, kokorochat, smile, esconv
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Dataset registry
# Each dataset entry describes where the pre-converted interactions.jsonl
# lives and which judge template to use for each option.
# ---------------------------------------------------------------------------
DATASETS = {
    # ------------------------------------------------------------------
    # Existing datasets (ZH / KO — S1 needs translated files)
    # ------------------------------------------------------------------
    "simpsydial": {
        "display": "SimPsyDial (Chinese)",
        "options": {
            "S1": {
                "interactions": "data/simpsydial/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [needs translation]",
            },
            "S2": {
                "interactions": "data/simpsydial/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_zh.py",
                "description": "Chinese dialogue + Chinese judge",
            },
            "S3": {
                "interactions": "data/simpsydial/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Chinese dialogue + English judge",
            },
        },
    },
    "kmi": {
        "display": "KMI (Korean Mental Health Interview)",
        "options": {
            "S1": {
                "interactions": "data/KMI/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  (utterance_en from raw)",
            },
            "S2": {
                "interactions": "data/KMI/test/interactions_200_canonical_ko.jsonl",
                "judge_template_path": "mindeval/judge_prompts_ko.py",
                "description": "Korean dialogue + Korean judge",
            },
            "S3": {
                "interactions": "data/KMI/test/interactions_200_canonical_ko.jsonl",
                "judge_template_version": "v0_1",
                "description": "Korean dialogue + English judge",
            },
        },
    },
    "soulchat": {
        "display": "SoulChat (Chinese)",
        "options": {
            "S1": {
                "interactions": "data/SoulChat/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [needs translation]",
            },
            "S2": {
                "interactions": "data/SoulChat/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_zh.py",
                "description": "Chinese dialogue + Chinese judge",
            },
            "S3": {
                "interactions": "data/SoulChat/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Chinese dialogue + English judge",
            },
        },
    },
    # ------------------------------------------------------------------
    # EN datasets — S1 = S3 (canonical used directly, no translation)
    # ------------------------------------------------------------------
    "cactus": {
        "display": "cactus (English CBT)",
        "options": {
            "S1": {
                "interactions": "data/cactus/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge",
            },
            "S3": {
                "interactions": "data/cactus/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge (same as S1)",
            },
        },
    },
    "psy_insight": {
        "display": "Psy-Insight (English)",
        "options": {
            "S1": {
                "interactions": "data/Psy-Insight/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge",
            },
            "S3": {
                "interactions": "data/Psy-Insight/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge (same as S1)",
            },
        },
    },
    "psydial": {
        "display": "PsyDial (Chinese)",
        "options": {
            "S1": {
                "interactions": "data/PsyDial/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [needs translation]",
            },
            "S2": {
                "interactions": "data/PsyDial/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_zh.py",
                "description": "Chinese dialogue + Chinese judge",
            },
            "S3": {
                "interactions": "data/PsyDial/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Chinese dialogue + English judge",
            },
        },
    },
    # ------------------------------------------------------------------
    # AnnoMI — real MI counselling transcripts (EN), provenance bậc 1
    # S1 = S3 (EN dataset, no translation needed)
    # ------------------------------------------------------------------
    "annomi": {
        "display": "AnnoMI (English, real MI counselling)",
        "options": {
            "S1": {
                "interactions": "data/AnnoMI/test/interactions_112_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge",
            },
            "S3": {
                "interactions": "data/AnnoMI/test/interactions_112_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge (same as S1)",
            },
        },
    },
    # ------------------------------------------------------------------
    # CPsyCoun — semi-real ZH counselling from case reports (provenance bậc 2)
    # S1 file is pre-sampled at 20 records (LLM-translated EN subset)
    # ------------------------------------------------------------------
    "cpscycoun": {
        "display": "CPsyCoun (Chinese, semi-real counselling)",
        "options": {
            "S1": {
                "interactions": "data/CPsyCoun/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [LLM-translated, 20-sample subset]",
            },
            "S2": {
                "interactions": "data/CPsyCoun/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_zh.py",
                "description": "Chinese dialogue + Chinese judge",
            },
            "S3": {
                "interactions": "data/CPsyCoun/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Chinese dialogue + English judge",
            },
        },
    },
    # ------------------------------------------------------------------
    # KokoroChat — human role-play JA counselling (provenance bậc 3)
    # S1 file is pre-sampled at 20 records (LLM-translated EN subset)
    # S2 uses Japanese judge (judge_prompts_ja.py)
    # ------------------------------------------------------------------
    "kokorochat": {
        "display": "KokoroChat (Japanese, human role-play counselling)",
        "options": {
            "S1": {
                "interactions": "data/KokoroChat/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [LLM-translated, 20-sample subset]",
            },
            "S2": {
                "interactions": "data/KokoroChat/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_ja.py",
                "description": "Japanese dialogue + Japanese judge",
            },
            "S3": {
                "interactions": "data/KokoroChat/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Japanese dialogue + English judge",
            },
        },
    },
    # ------------------------------------------------------------------
    # SMILE (SmileChat) — LLM-expanded ZH (single-turn QA → multi-turn)
    # provenance bậc 4; S1 file pre-sampled at 20 records (LLM-translated EN subset)
    # ------------------------------------------------------------------
    "smile": {
        "display": "SMILE / SmileChat (Chinese, LLM-expanded)",
        "options": {
            "S1": {
                "interactions": "data/smile/test/interactions_200_S1_en.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge  [LLM-translated, 20-sample subset]",
            },
            "S2": {
                "interactions": "data/smile/test/interactions_200_canonical.jsonl",
                "judge_template_path": "mindeval/judge_prompts_zh.py",
                "description": "Chinese dialogue + Chinese judge",
            },
            "S3": {
                "interactions": "data/smile/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "Chinese dialogue + English judge",
            },
        },
    },
    # ------------------------------------------------------------------
    # ESConv — crowdsourced emotional support conversations (EN)
    # provenance bậc 1 (real human); S1 = S3 (EN dataset, no translation needed)
    # ------------------------------------------------------------------
    "esconv": {
        "display": "ESConv (English, crowdsourced emotional support)",
        "options": {
            "S1": {
                "interactions": "data/ESConv/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge",
            },
            "S3": {
                "interactions": "data/ESConv/test/interactions_200_canonical.jsonl",
                "judge_template_version": "v0_1",
                "description": "English dialogue + English judge (same as S1)",
            },
        },
    },
}


def load_judge_config(config_path: str) -> dict:
    """Legacy helper — kept for backward compat. Use mindeval.config.get_judge_config instead."""
    from mindeval.config import get_judge_config as _get_judge_config
    return _get_judge_config(config_path)


def run_mind_eval(
    interactions_path: str,
    output_path: str,
    option_cfg: dict,
    config_path: str,
    max_workers: int,
    skip_existing: bool,
    max_dialogues: int | None = None,
    judge_name: str | None = None,
    batch_delay: float = 0.0,
) -> bool:
    """Run Mind-Eval 5-metric evaluation. Returns True on success."""
    cmd = [
        sys.executable, "-m", "mindeval.scripts.generate_judgments",
        "--interactions_path", interactions_path,
        "--output_path", output_path,
        "--config_path", config_path,
        "--max_workers", str(max_workers),
    ]

    if "judge_template_version" in option_cfg:
        cmd += ["--judge_template_version", option_cfg["judge_template_version"]]
    elif "judge_template_path" in option_cfg:
        cmd += ["--judge_template_path", option_cfg["judge_template_path"]]

    if judge_name:
        cmd += ["--judge_name", judge_name]

    if not skip_existing:
        cmd += ["--skip_existing", "false"]

    if max_dialogues is not None:
        cmd += ["--max_dialogues", str(max_dialogues)]

    if batch_delay > 0:
        cmd += ["--batch_delay", str(batch_delay)]

    print(f"\n[Mind-Eval] Running: {' '.join(cmd)}\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return result.returncode == 0


def run_wai(
    interactions_path: str,
    output_path: str,
    config_path: str,
    n_runs: int,
    max_dialogues: int | None,
    skip_existing: bool,
    judge_name: str | None = None,
    wai_batch: bool = True,
    max_workers: int = 5,
    batch_delay: float = 0.0,
) -> bool:
    """Run WAI 3-dimension evaluation (English prompts). Returns True on success."""
    cmd = [
        sys.executable, "-m", "mindeval.scripts.generate_wai_judgments",
        "--interactions_path", interactions_path,
        "--output_path", output_path,
        "--config_path", config_path,
        "--n_runs", str(n_runs),
        "--max_workers", str(max_workers),
    ]

    if judge_name:
        cmd += ["--judge_name", judge_name]

    if max_dialogues is not None:
        cmd += ["--max_dialogues", str(max_dialogues)]

    if not skip_existing:
        cmd += ["--skip_existing", "false"]

    if not wai_batch:
        cmd += ["--wai_batch", "false"]

    if batch_delay > 0:
        cmd += ["--batch_delay", str(batch_delay)]

    print(f"\n[WAI] Running: {' '.join(cmd)}\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return result.returncode == 0


def list_datasets():
    print("\nAvailable datasets:\n")
    for key, ds in DATASETS.items():
        print(f"  {key}  ({ds['display']})")
        for opt, cfg in ds["options"].items():
            interactions = cfg["interactions"]
            exists = "[OK]" if Path(interactions).exists() else "[missing]"
            # Show where results will go
            results_dir = Path(interactions).parent.parent / "results"
            print(f"    option {opt}: {cfg['description']}")
            print(f"             interactions: {interactions}  {exists}")
            print(f"             results -> {results_dir}/mind_eval/  &  {results_dir}/wai/")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Unified evaluation for all datasets (Mind-Eval 5-metric + WAI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dataset", choices=list(DATASETS.keys()),
                        help="Dataset to evaluate")
    parser.add_argument("--option", choices=["S1", "S2", "S3"], default="S3",
                        help="Evaluation setting: S1=EN/EN, S2=native/native, S3=native/EN (default: S3)")
    parser.add_argument("--eval", choices=["mind-eval", "wai", "both"], default="both",
                        help="Which evaluation to run (default: both)")
    parser.add_argument("--config_path", default="config.json",
                        help="Path to config.json with API keys (default: config.json)")
    parser.add_argument("--max_workers", type=int, default=5,
                        help="Parallel workers for Mind-Eval (default: 5)")
    parser.add_argument("--wai_n_runs", type=int, default=3,
                        help="WAI runs per question (default: 3)")
    parser.add_argument("--max_dialogues", type=int, default=None,
                        help="Limit number of dialogues (default: all)")
    parser.add_argument("--no_skip", action="store_true",
                        help="Re-evaluate already-evaluated dialogues")
    parser.add_argument("--judge_name", default=None,
                        help="Named judge from config 'judges' section (e.g. 'gpt', 'claude'). "
                             "Output file becomes <option>_<judge_name>_judgments.jsonl")
    parser.add_argument("--batch_delay", type=float, default=0.0,
                        help="Seconds to sleep between batches (default: 0). "
                             "Use 3-5 for Anthropic Tier-1 rate limit.")
    parser.add_argument("--no_wai_batch", action="store_true",
                        help="Disable WAI batch mode (12 questions per call). "
                             "Use for models that reject long batch prompts (e.g. some Gemini).")
    parser.add_argument("--output_suffix", default="",
                        help="Suffix inserted before '_judgments.jsonl' in output filenames. "
                             "E.g. '_full' → KMI_S3_gpt_full_judgments.jsonl")
    parser.add_argument("--list", action="store_true",
                        help="List all datasets and their status, then exit")
    args = parser.parse_args()

    if args.list:
        list_datasets()
        return

    if not args.dataset:
        parser.error("--dataset is required (or use --list to see available datasets)")

    if not Path(args.config_path).exists():
        print(f"ERROR: config file not found: {args.config_path}")
        print("Copy config.example.json to config.json and fill in your API keys.")
        sys.exit(1)

    ds = DATASETS[args.dataset]
    option_cfg = ds["options"][args.option]
    interactions_path = option_cfg["interactions"]
    skip_existing = not args.no_skip

    print(f"\n{'='*60}")
    print(f"Dataset : {ds['display']}")
    print(f"Option  : {args.option.upper()} — {option_cfg['description']}")
    print(f"Eval    : {args.eval}")
    print(f"Config  : {args.config_path}")
    if args.max_dialogues:
        print(f"Limit   : {args.max_dialogues} dialogues")
    print(f"{'='*60}")

    if not Path(interactions_path).exists():
        print(f"\nERROR: interactions file not found: {interactions_path}")
        print("Run the canonical converter first:")
        print(f"  python mindeval/scripts/convert_to_canonical.py --datasets {args.dataset}")
        sys.exit(1)

    # Standard output structure:
    #   data/<dataset>/results/mind_eval/<dataset>_<option>_<judge>_judgments.jsonl
    #   data/<dataset>/results/wai/<dataset>_<option>_<judge>_wai_judgments.jsonl
    dataset_dir = Path(interactions_path).parent.parent  # data/<dataset>/
    stem = args.option  # e.g. S1, S2, S3

    mind_eval_dir = dataset_dir / "results" / "mind_eval"
    wai_dir = dataset_dir / "results" / "wai"
    mind_eval_dir.mkdir(parents=True, exist_ok=True)
    wai_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output dir: {dataset_dir / 'results'}")

    eval_results = {}

    # dataset_dir.name = actual folder name (e.g. "KMI", "SoulChat", "simpsydial")
    # used as prefix so output files are self-identifying when viewed outside their folder.
    ds_folder = dataset_dir.name  # e.g. "KMI", "SoulChat", "simpsydial"

    if args.eval in ("mind-eval", "both"):
        # Output: <dataset>_<option>_<judge_name>[suffix]_judgments.jsonl
        effective_judge = args.judge_name or "gpt"
        suffix = args.output_suffix
        out_stem = f"{ds_folder}_{stem}_{effective_judge}{suffix}_judgments.jsonl"
        output_path = str(mind_eval_dir / out_stem)
        # Pre-populate output file with existing pilot records so they are skipped
        if suffix and not Path(output_path).exists():
            pilot_path = mind_eval_dir / f"{ds_folder}_{stem}_{effective_judge}_judgments.jsonl"
            if pilot_path.exists():
                import shutil
                shutil.copy(pilot_path, output_path)
                print(f"  [pre-populate] Copied {pilot_path.name} → {Path(output_path).name}")
        ok = run_mind_eval(
            interactions_path=interactions_path,
            output_path=output_path,
            option_cfg=option_cfg,
            config_path=args.config_path,
            max_workers=args.max_workers,
            skip_existing=skip_existing,
            max_dialogues=args.max_dialogues,
            judge_name=effective_judge,
            batch_delay=args.batch_delay,
        )
        eval_results["mind-eval"] = ("[OK]" if ok else "[FAILED]") + f" -> {output_path}"

    if args.eval in ("wai", "both"):
        effective_judge = args.judge_name or "gpt"
        suffix = args.output_suffix
        wai_stem = f"{ds_folder}_{stem}_{effective_judge}{suffix}_wai_judgments.jsonl"
        output_path = str(wai_dir / wai_stem)
        # Pre-populate output file with existing pilot records so they are skipped
        if suffix and not Path(output_path).exists():
            pilot_path = wai_dir / f"{ds_folder}_{stem}_{effective_judge}_wai_judgments.jsonl"
            if pilot_path.exists():
                import shutil
                shutil.copy(pilot_path, output_path)
                print(f"  [pre-populate] Copied {pilot_path.name} → {Path(output_path).name}")
        ok = run_wai(
            interactions_path=interactions_path,
            output_path=output_path,
            config_path=args.config_path,
            n_runs=args.wai_n_runs,
            max_dialogues=args.max_dialogues,
            skip_existing=skip_existing,
            judge_name=effective_judge,
            wai_batch=not args.no_wai_batch,
            max_workers=args.max_workers,
            batch_delay=args.batch_delay,
        )
        eval_results["wai"] = ("[OK]" if ok else "[FAILED]") + f" -> {output_path}"

    print(f"\n{'='*60}")
    print("Results:")
    for k, v in eval_results.items():
        print(f"  {k:12s}  {v}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
