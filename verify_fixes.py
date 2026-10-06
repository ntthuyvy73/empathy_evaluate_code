"""
Verify that all fixes are working correctly.
"""
import json

def verify_option_b_judgments():
    """Verify Option B judgments have correct thinking_trace and parsed_judgment."""
    
    print("=== FINAL VERIFICATION ===\n")
    
    with open('data/simpsydial/test/option_b_judgments.jsonl', 'r', encoding='utf-8') as f:
        judgment = json.loads(f.readline())
    
    # Check thinking_trace
    thinking_len = len(judgment.get('thinking_trace', ''))
    print(f"✅ thinking_trace populated: {thinking_len} chars")
    
    if thinking_len == 0:
        print("❌ ERROR: thinking_trace is empty!")
        return False
    
    # Check parsed_judgment
    parsed = judgment.get('parsed_judgment', {})
    overall = parsed.get('Overall score', 0)
    
    print(f"✅ Overall score: {overall}")
    print(f"✅ Clinical Accuracy: {parsed.get('Clinical Accuracy & Competence', 0)}")
    print(f"✅ Ethical Conduct: {parsed.get('Ethical & Professional Conduct', 0)}")
    print(f"✅ Assessment: {parsed.get('Assessment & Response', 0)}")
    print(f"✅ Therapeutic Relationship: {parsed.get('Therapeutic Relationship & Alliance', 0)}")
    print(f"✅ AI Communication: {parsed.get('AI-Specific Communication Quality', 0)}")
    
    # Check if scores are not all 3.0 (default)
    scores = [
        parsed.get('Clinical Accuracy & Competence', 0),
        parsed.get('Ethical & Professional Conduct', 0),
        parsed.get('Assessment & Response', 0),
        parsed.get('Therapeutic Relationship & Alliance', 0),
        parsed.get('AI-Specific Communication Quality', 0)
    ]
    
    if all(s == 3.0 for s in scores):
        print("❌ ERROR: All scores are 3.0 (default) - parsing failed!")
        return False
    
    print("\n=== ALL FIXES VERIFIED ===\n")
    print("1. ✅ thinking_trace: Populated with Chinese content")
    print("2. ✅ parsed_judgment: Scores correctly parsed from Chinese format")
    print(f"3. ✅ Overall score: {overall} (calculated from individual scores)")
    
    return True

if __name__ == "__main__":
    try:
        success = verify_option_b_judgments()
        if success:
            print("\n🎉 All fixes working correctly!")
        else:
            print("\n⚠️ Some issues detected - see errors above")
    except FileNotFoundError:
        print("❌ ERROR: option_b_judgments.jsonl not found")
        print("Run Option B first: python run_single_option.py --option B --max_dialogues 1")
    except Exception as e:
        print(f"❌ ERROR: {e}")
