"""
Run three-way evaluation comparison: Option A, B, and C.

This script runs all three evaluation approaches on the same dataset:
- Option A: Translate dialogues to English, evaluate with English judge
- Option B: Keep original language, evaluate with translated judge prompt
- Option C: Bilingual evaluation (original dialogue + English judge prompt)

Usage with config file:
    python mindeval/scripts/run_three_way_evaluation.py \
        --input_dialogues_path data/simpsydial/raw \
        --source_language zh \
        --output_dir data/simpsydial/three_way_comparison \
        --config_path config.json \
        --max_dialogues 50

Usage with environment variables:
    # Set environment variables
    export TRANSLATION_MODEL="gpt-4"
    export TRANSLATION_API_KEY="your-key"
    export JUDGE_MODEL="claude-sonnet-4"
    export JUDGE_API_KEY="your-key"
    
    # Run script
    python mindeval/scripts/run_three_way_evaluation.py \
        --input_dialogues_path data/simpsydial/raw \
        --source_language zh \
        --output_dir data/simpsydial/three_way_comparison \
        --max_dialogues 50
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from tqdm import tqdm

from mindeval.utils import save_to_jsonl, load_jsonl
from mindeval.config import get_translation_config, get_judge_config, print_config_summary


def run_option_a(
    dialogues_path: str,
    source_language: str,
    config_path: Optional[str],
    output_dir: Path,
    max_dialogues: Optional[int] = None
) -> str:
    """
    Option A: Translate dialogues to English, evaluate with English judge.
    
    Returns:
        Path to judgments file
    """
    print("\n" + "="*80)
    print("  OPTION A: TRANSLATE DIALOGUES TO ENGLISH")
    print("="*80 + "\n")
    
    # Get translation config
    translation_config = get_translation_config(config_path)
    
    # Get profile extraction config
    from mindeval.config import get_profile_extraction_config
    profile_extraction_config = get_profile_extraction_config(config_path)
    
    # Print model info
    print(f"Translation Model: {translation_config['model']}")
    print(f"Profile Extraction Model: {profile_extraction_config['model']}")
    print(f"Max dialogues: {max_dialogues or 'All'}")
    print()
    
    # Step 1: Convert, extract profile, and translate
    print("Step 1: Converting, extracting profiles, and translating dialogues...")
    interactions_path = output_dir / "option_a_interactions_en.jsonl"
    
    from mindeval.scripts.convert_simpsydial import main as convert_main
    convert_main(
        input_dir=dialogues_path,
        output_path=str(interactions_path),
        translate=True,
        translation_method="llm",  # Use LLM from config instead of hardcoded "gpt4"
        model_api_params=translation_config,
        max_files=max_dialogues,
        target_language="en",  # Translate to English (default for Option A)
        extract_profile=True,  # Enable profile extraction
        profile_extraction_params=profile_extraction_config,
        skip_existing=True  # Skip already translated files to save tokens
    )
    
    # Step 2: Evaluate with English judge
    print("\nStep 2: Evaluating with English judge...")
    judgments_path = output_dir / "option_a_judgments.jsonl"
    
    # Get judge config
    judge_config = get_judge_config(config_path)
    
    # Print judge model info
    print(f"Judge Model: {judge_config['model']}")
    print()
    
    from mindeval.scripts.generate_judgments import main as judge_main
    judge_main(
        interactions_path=str(interactions_path),
        judge_template_version="v0_1",
        judge_model_api_params=judge_config,
        max_workers=5,
        output_path=str(judgments_path),
        skip_existing=True  # Skip already judged interactions to save tokens
    )
    
    print(f"\n✓ Option A complete: {judgments_path}")
    return str(judgments_path)


def run_option_b(
    dialogues_path: str,
    source_language: str,
    config_path: Optional[str],
    output_dir: Path,
    max_dialogues: Optional[int] = None
) -> str:
    """
    Option B: Keep original language, evaluate with Chinese judge prompt.
    
    Returns:
        Path to judgments file
    """
    print("\n" + "="*80)
    print(f"  OPTION B: EVALUATE IN ORIGINAL LANGUAGE ({source_language.upper()})")
    print("="*80 + "\n")
    
    # Step 1: Use Chinese judge prompt (no translation needed)
    print("Step 1: Using Chinese judge prompt...")
    judge_prompt_path = Path("mindeval/judge_prompts_zh.py")
    
    if not judge_prompt_path.exists():
        print(f"⚠ Chinese judge prompt not found: {judge_prompt_path}")
        print("Please ensure mindeval/judge_prompts_zh.py exists with your Chinese prompt.")
        raise FileNotFoundError(f"Chinese judge prompt file not found: {judge_prompt_path}")
    
    print(f"✓ Using Chinese judge prompt: {judge_prompt_path}")
    
    # Step 2: Convert dialogues (no translation)
    print(f"\nStep 2: Converting dialogues (keeping original language)...")
    print(f"Max dialogues: {max_dialogues or 'All'}")
    interactions_path = output_dir / f"option_b_interactions_{source_language}.jsonl"
    
    from mindeval.scripts.convert_simpsydial import main as convert_main
    convert_main(
        input_dir=dialogues_path,
        output_path=str(interactions_path),
        translate=False,
        max_files=max_dialogues,
        skip_existing=True  # Skip already converted files
    )
    
    # Step 3: Evaluate with Chinese judge
    print(f"\nStep 3: Evaluating with {source_language.upper()} judge...")
    judgments_path = output_dir / "option_b_judgments.jsonl"
    
    # Get judge config
    judge_config = get_judge_config(config_path)
    
    # Print judge model info
    print(f"Judge Model: {judge_config['model']}")
    print()
    
    from mindeval.scripts.generate_judgments import main as judge_main
    judge_main(
        interactions_path=str(interactions_path),
        judge_template_path=str(judge_prompt_path),  # Use Chinese prompt file
        judge_model_api_params=judge_config,
        max_workers=5,
        output_path=str(judgments_path),
        skip_existing=True  # Skip already judged interactions to save tokens
    )
    
    print(f"\n✓ Option B complete: {judgments_path}")
    return str(judgments_path)


def run_option_c(
    dialogues_path: str,
    source_language: str,
    config_path: Optional[str],
    output_dir: Path,
    max_dialogues: Optional[int] = None
) -> str:
    """
    Option C: Keep original language dialogue, evaluate with English judge prompt.
    
    This tests whether the judge can evaluate non-English dialogues directly
    without translation or bilingual prompts.
    
    Returns:
        Path to judgments file
    """
    print("\n" + "="*80)
    print(f"  OPTION C: ORIGINAL LANGUAGE ({source_language.upper()}) + ENGLISH JUDGE")
    print("="*80 + "\n")
    
    # Step 1: Convert dialogues (no translation)
    print("Step 1: Converting dialogues (keeping original language)...")
    print(f"Max dialogues: {max_dialogues or 'All'}")
    interactions_path = output_dir / f"option_c_interactions_{source_language}.jsonl"
    
    from mindeval.scripts.convert_simpsydial import main as convert_main
    convert_main(
        input_dir=dialogues_path,
        output_path=str(interactions_path),
        translate=False,
        max_files=max_dialogues,
        skip_existing=True  # Skip already converted files
    )
    
    # Step 2: Evaluate with English judge prompt (same as Option A)
    print(f"\nStep 2: Evaluating {source_language.upper()} dialogues with English judge prompt...")
    print("Note: This tests if the judge can evaluate non-English dialogues directly")
    judgments_path = output_dir / "option_c_judgments.jsonl"
    
    # Get judge config
    judge_config = get_judge_config(config_path)
    
    # Print judge model info
    print(f"Judge Model: {judge_config['model']}")
    print()
    
    from mindeval.scripts.generate_judgments import main as judge_main
    judge_main(
        interactions_path=str(interactions_path),
        judge_template_version="v0_1",  # Use standard English prompt (same as Option A)
        judge_model_api_params=judge_config,
        max_workers=5,
        output_path=str(judgments_path),
        skip_existing=True  # Skip already judged interactions to save tokens
    )
    
    print(f"\n✓ Option C complete: {judgments_path}")
    return str(judgments_path)


def main(
    input_dialogues_path: str,
    source_language: str,
    output_dir: str,
    config_path: Optional[str] = None,
    max_dialogues: Optional[int] = None,
    run_options: str = "ABC"
):
    """
    Run three-way evaluation comparison.
    
    Args:
        input_dialogues_path: Path to input dialogues directory
        source_language: Source language code (zh, ko, ja, etc.)
        output_dir: Output directory for all results
        config_path: Path to config file (JSON). If None, uses environment variables.
        max_dialogues: Maximum number of dialogues to process
        run_options: Which options to run (e.g., "ABC", "AB", "A")
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("  THREE-WAY EVALUATION COMPARISON")
    print("="*80)
    print(f"\nSource language: {source_language}")
    print(f"Max dialogues: {max_dialogues or 'All'}")
    print(f"Options to run: {run_options}")
    print(f"Output directory: {output_dir}")
    print(f"Config path: {config_path or 'Environment variables'}")
    
    # Print config summary
    print_config_summary(config_path)
    
    results = {}
    
    # Run Option A
    if "A" in run_options.upper():
        try:
            results["option_a"] = run_option_a(
                dialogues_path=input_dialogues_path,
                source_language=source_language,
                config_path=config_path,
                output_dir=output_path,
                max_dialogues=max_dialogues
            )
        except Exception as e:
            print(f"\n❌ Option A failed: {e}")
            results["option_a"] = None
    
    # Run Option B
    if "B" in run_options.upper():
        try:
            results["option_b"] = run_option_b(
                dialogues_path=input_dialogues_path,
                source_language=source_language,
                config_path=config_path,
                output_dir=output_path,
                max_dialogues=max_dialogues
            )
        except Exception as e:
            print(f"\n❌ Option B failed: {e}")
            results["option_b"] = None
    
    # Run Option C
    if "C" in run_options.upper():
        try:
            results["option_c"] = run_option_c(
                dialogues_path=input_dialogues_path,
                source_language=source_language,
                config_path=config_path,
                output_dir=output_path,
                max_dialogues=max_dialogues
            )
        except Exception as e:
            print(f"\n❌ Option C failed: {e}")
            results["option_c"] = None
    
    # Save summary
    summary = {
        "source_language": source_language,
        "max_dialogues": max_dialogues,
        "options_run": run_options,
        "results": results
    }
    
    summary_path = output_path / "evaluation_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final summary
    print("\n" + "="*80)
    print("  EVALUATION COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_dir}")
    print("\nNext step: Run comparison analysis")
    print(f"python mindeval/scripts/compare_evaluation_methods.py \\")
    print(f"    --option_a_path {results.get('option_a', 'N/A')} \\")
    print(f"    --option_b_path {results.get('option_b', 'N/A')} \\")
    print(f"    --option_c_path {results.get('option_c', 'N/A')} \\")
    print(f"    --output_dir {output_dir}/comparison")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([main], as_positional=False)
