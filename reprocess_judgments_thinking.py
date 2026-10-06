"""
Reprocess judgments to extract thinking_trace from unparsed_judgment.

This script is useful when:
1. Judgments were generated before thinking extraction was updated
2. thinking_trace is empty but unparsed_judgment contains thinking
3. You updated the extraction function and want to re-extract

Usage:
    python reprocess_judgments_thinking.py \
        --input_path data/simpsydial/test/option_b_judgments.jsonl \
        --output_path data/simpsydial/test/option_b_judgments_fixed.jsonl
"""
import json
from pathlib import Path
from mindeval.utils import separate_thinking_from_response, parse_judge_scores

def reprocess_judgments(input_path: str, output_path: str = None):
    """
    Reprocess judgments to extract thinking_trace.
    
    Args:
        input_path: Path to input judgments JSONL
        output_path: Path to output judgments JSONL (default: overwrite input)
    """
    if output_path is None:
        output_path = input_path
    
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Load judgments
    print(f"Loading judgments from: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        judgments = [json.loads(line) for line in f]
    
    print(f"Found {len(judgments)} judgments")
    
    # Reprocess each judgment
    updated_count = 0
    for i, judgment in enumerate(judgments):
        unparsed = judgment.get('unparsed_judgment', '')
        old_thinking = judgment.get('thinking_trace', '')
        
        # Extract thinking from unparsed_judgment
        parts = separate_thinking_from_response(unparsed)
        new_thinking = parts['thinking']
        new_response = parts['response']
        
        # Update if thinking was extracted
        if new_thinking and not old_thinking:
            judgment['thinking_trace'] = new_thinking
            judgment['unparsed_judgment'] = new_response
            # Re-parse judgment (in case format changed)
            judgment['parsed_judgment'] = parse_judge_scores(new_response)[0]
            updated_count += 1
            print(f"  ✓ Judgment {i+1}: Extracted {len(new_thinking)} chars of thinking")
        elif old_thinking:
            print(f"  - Judgment {i+1}: Already has thinking ({len(old_thinking)} chars)")
        else:
            print(f"  ⚠ Judgment {i+1}: No thinking found in unparsed_judgment")
    
    # Save updated judgments
    print(f"\nSaving updated judgments to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for judgment in judgments:
            f.write(json.dumps(judgment, ensure_ascii=False) + '\n')
    
    print(f"\n✓ Reprocessing complete!")
    print(f"  Total judgments: {len(judgments)}")
    print(f"  Updated: {updated_count}")
    print(f"  Already had thinking: {len(judgments) - updated_count - (len(judgments) - updated_count)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reprocess_judgments_thinking.py <input_path> [output_path]")
        print("\nExample:")
        print("  python reprocess_judgments_thinking.py data/simpsydial/test/option_b_judgments.jsonl")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    reprocess_judgments(input_path, output_path)
