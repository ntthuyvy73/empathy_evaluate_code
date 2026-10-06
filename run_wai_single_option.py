"""
Helper script to run a single WAI evaluation option for testing.

This script allows you to test each WAI option (A, B, or C) individually
with a small number of dialogues before running the full evaluation.

WAI Options (similar to Mind-Eval):
- Option A: English dialogue + English WAI prompt
- Option B: Chinese dialogue + Chinese WAI prompt
- Option C: Chinese dialogue + English WAI prompt

Usage:
    # Test Option A with 2 dialogues
    python run_wai_single_option.py --option A --max_dialogues 2
    
    # Test Option B with 5 dialogues
    python run_wai_single_option.py --option B --max_dialogues 5
    
    # Test Option C with 3 dialogues
    python run_wai_single_option.py --option C --max_dialogues 3
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mindeval.scripts.generate_wai_judgments import main as wai_main


def run_wai_single_option(
    option: str,
    input_dir: str = "data/simpsydial/test",
    config_path: str = "config.json",
    max_dialogues: int = 2,
    n_runs: int = 1
):
    """
    Run a single WAI evaluation option for testing.
    
    Args:
        option: Which option to run ("A", "B", or "C")
        input_dir: Directory containing interactions files
        config_path: Path to config file
        max_dialogues: Maximum number of dialogues to process
        n_runs: Number of runs per question (default 3, per paper)
    """
    # Validate option
    option = option.upper()
    if option not in ["A", "B", "C"]:
        raise ValueError(f"Invalid option: {option}. Must be A, B, or C")
    
    print("\n" + "="*80)
    print(f"  TESTING WAI OPTION {option}")
    print("="*80)
    print(f"\nThis will process {max_dialogues} dialogue(s) to test the WAI pipeline.")
    print(f"Config file: {config_path}")
    print(f"N runs per question: {n_runs}")
    print(f"Total LLM calls per dialogue: {12 * n_runs}")
    print("\n" + "="*80 + "\n")
    
    # Determine interactions path and language based on option
    input_dir_path = Path(input_dir)
    
    if option == "A":
        # Option A: English dialogue + English prompt
        interactions_path = input_dir_path / "option_a_interactions_en.jsonl"
        output_path = input_dir_path / "option_a_wai_judgments.jsonl"
        language = "en"
        print("Option A: English dialogue + English WAI prompt")
        
    elif option == "B":
        # Option B: Chinese dialogue + Chinese prompt
        interactions_path = input_dir_path / "option_b_interactions_zh.jsonl"
        output_path = input_dir_path / "option_b_wai_judgments.jsonl"
        language = "zh"
        print("Option B: Chinese dialogue + Chinese WAI prompt")
        
    else:  # option == "C"
        # Option C: Chinese dialogue + English prompt
        interactions_path = input_dir_path / "option_c_interactions_zh.jsonl"
        output_path = input_dir_path / "option_c_wai_judgments.jsonl"
        language = "en"
        print("Option C: Chinese dialogue + English WAI prompt")
    
    # Check if interactions file exists
    if not interactions_path.exists():
        raise FileNotFoundError(
            f"Interactions file not found: {interactions_path}\n"
            f"Please run the corresponding mind-eval option first to generate interactions."
        )
    
    print(f"Input: {interactions_path}")
    print(f"Output: {output_path}")
    print(f"Language: {'Chinese' if language == 'zh' else 'English'}")
    print()
    
    # Run WAI evaluation
    wai_main(
        interactions_path=str(interactions_path),
        output_path=str(output_path),
        config_path=config_path,
        n_runs=n_runs,
        max_workers=1,
        language=language,
        skip_existing=True,
        max_dialogues=max_dialogues
    )
    
    print("\n" + "="*80)
    print(f"  WAI OPTION {option} TEST COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_path}")
    # print("\nNext steps:")
    # print(f"1. Review the output in {output_path}")
    # print(f"2. Check the WAI scores and dimensions")
    # print(f"3. If everything looks good, run with more dialogues:")
    # print(f"   python run_wai_single_option.py --option {option} --max_dialogues 50")
    # print(f"4. Or compare all three options:")
    # print(f"   python run_wai_single_option.py --option A --max_dialogues 10")
    # print(f"   python run_wai_single_option.py --option B --max_dialogues 10")
    # print(f"   python run_wai_single_option.py --option C --max_dialogues 10")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([run_wai_single_option], as_positional=False)
