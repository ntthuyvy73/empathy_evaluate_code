"""
Re-parse judgment scores from unparsed_judgment.

This script is useful when:
1. The parse_judge_scores() function was updated
2. parsed_judgment has incorrect scores
3. You want to re-parse all judgments with the new parsing logic

Usage:
    python reparse_judgment_scores.py data/simpsydial/test/option_b_judgments.jsonl
"""
import json
from pathlib import Path
from mindeval.utils import parse_judge_scores

def reparse_scores(input_path: str, output_path: str = None):
    """
    Re-parse scores from unparsed_judgment.
    
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
    print()
    
    # Re-parse each judgment
    updated_count = 0
    for i, judgment in enumerate(judgments):
        unparsed = judgment.get('unparsed_judgment', '')
        old_parsed = judgment.get('parsed_judgment', {})
        
        # Re-parse scores
        new_parsed = parse_judge_scores(unparsed)[0]
        
        # Check if scores changed
        old_overall = old_parsed.get('Overall score', 0)
        new_overall = new_parsed.get('Overall score', 0)
        
        if abs(old_overall - new_overall) > 0.01:
            print(f"Judgment {i+1}:")
            print(f"  Old overall score: {old_overall:.2f}")
            print(f"  New overall score: {new_overall:.2f}")
            print(f"  Difference: {new_overall - old_overall:+.2f}")
            
            # Show individual score changes
            for criterion in ['Clinical Accuracy & Competence', 
                            'Ethical & Professional Conduct',
                            'Assessment & Response',
                            'Therapeutic Relationship & Alliance',
                            'AI-Specific Communication Quality']:
                old_score = old_parsed.get(criterion, 3.0)
                new_score = new_parsed.get(criterion, 3.0)
                if abs(old_score - new_score) > 0.01:
                    print(f"    {criterion}: {old_score} → {new_score}")
            
            judgment['parsed_judgment'] = new_parsed
            updated_count += 1
            print()
        else:
            print(f"Judgment {i+1}: No change (overall score: {old_overall:.2f})")
    
    # Save updated judgments
    print(f"\nSaving updated judgments to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for judgment in judgments:
            f.write(json.dumps(judgment, ensure_ascii=False) + '\n')
    
    print(f"\n✓ Re-parsing complete!")
    print(f"  Total judgments: {len(judgments)}")
    print(f"  Updated: {updated_count}")
    print(f"  Unchanged: {len(judgments) - updated_count}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reparse_judgment_scores.py <input_path> [output_path]")
        print("\nExample:")
        print("  python reparse_judgment_scores.py data/simpsydial/test/option_b_judgments.jsonl")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    reparse_scores(input_path, output_path)
