"""
Helper script to run a single evaluation option for testing.

This script allows you to test each option (A, B, or C) individually
with a small number of dialogues before running the full evaluation.

Usage:
    # Test Option A with 2 dialogues
    python run_single_option.py --option A --max_dialogues 2
    
    # Test Option B with 5 dialogues
    python run_single_option.py --option B --max_dialogues 5
    
    # Test Option C with 3 dialogues
    python run_single_option.py --option C --max_dialogues 3
    
    # Test with custom paths
    python run_single_option.py \
        --option A \
        --max_dialogues 2 \
        --input_dialogues_path data/simpsydial/raw \
        --source_language zh \
        --output_dir data/simpsydial/test \
        --config_path config.json
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mindeval.scripts.run_three_way_evaluation import main


def run_single_option(
    option: str,
    input_dialogues_path: str = "data/simpsydial/raw",
    source_language: str = "zh",
    output_dir: str = "data/simpsydial/test",
    config_path: str = "config.json",
    max_dialogues: int = 2
):
    """
    Run a single evaluation option for testing.
    
    Args:
        option: Which option to run ("A", "B", or "C")
        input_dialogues_path: Path to input dialogues directory
        source_language: Source language code (zh, ko, ja, etc.)
        output_dir: Output directory for results
        config_path: Path to config file
        max_dialogues: Maximum number of dialogues to process
    """
    # Validate option
    option = option.upper()
    if option not in ["A", "B", "C"]:
        raise ValueError(f"Invalid option: {option}. Must be A, B, or C")
    
    print("\n" + "="*80)
    print(f"  TESTING OPTION {option}")
    print("="*80)
    print(f"\nThis will process {max_dialogues} dialogue(s) to test the pipeline.")
    print(f"Output directory: {output_dir}")
    print(f"Config file: {config_path}")
    print("\n" + "="*80 + "\n")
    
    # Run the evaluation
    main(
        input_dialogues_path=input_dialogues_path,
        source_language=source_language,
        output_dir=output_dir,
        config_path=config_path,
        max_dialogues=max_dialogues,
        run_options=option
    )
    
    # print("\n" + "="*80)
    # print(f"  OPTION {option} TEST COMPLETE")
    # print("="*80)
    # print(f"\nResults saved to: {output_dir}")
    # print("\nNext steps:")
    # print(f"1. Review the output in {output_dir}")
    # print(f"2. Check the model outputs and judgments")
    # print(f"3. If everything looks good, run with more dialogues:")
    # print(f"   python run_single_option.py --option {option} --max_dialogues 50")
    # print(f"4. Or run all options:")
    # print(f"   python mindeval/scripts/run_three_way_evaluation.py \\")
    # print(f"       --input_dialogues_path {input_dialogues_path} \\")
    # print(f"       --source_language {source_language} \\")
    # print(f"       --output_dir data/simpsydial/full_evaluation \\")
    # print(f"       --config_path {config_path} \\")
    # print(f"       --max_dialogues 1000")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([run_single_option], as_positional=False)
