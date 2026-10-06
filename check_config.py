"""
Quick config checker and fixer.

This script checks your config.json for common issues and offers to fix them.
"""

import json
from pathlib import Path


def check_config(config_path: str = "config.json"):
    """Check config file for common issues."""
    
    print("\n" + "="*80)
    print("  CONFIG CHECKER")
    print("="*80 + "\n")
    
    # Check if file exists
    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        print(f"\nCreate it by copying config.example.json:")
        print(f"  copy config.example.json {config_path}")
        return
    
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    issues = []
    fixes = {}
    
    # Check translation model
    if 'translation' in config:
        trans_model = config['translation'].get('model', '')
        trans_key = config['translation'].get('api_key', '')
        
        # Check for invalid model names
        if trans_model == 'gpt-5.1':
            issues.append("⚠️  Translation model 'gpt-5.1' does not exist")
            fixes['translation_model'] = 'gpt-4'
        elif trans_model == 'gpt-5':
            issues.append("⚠️  Translation model 'gpt-5' does not exist")
            fixes['translation_model'] = 'gpt-4'
        
        # Check API key
        if not trans_key or trans_key == 'your-openai-api-key':
            issues.append("❌ Translation API key not set")
        elif len(trans_key) < 20:
            issues.append("⚠️  Translation API key looks too short")
        else:
            print(f"✅ Translation model: {trans_model}")
            print(f"✅ Translation API key: Set ({len(trans_key)} chars)")
    else:
        issues.append("❌ Translation config missing")
    
    # Check judge model
    if 'judge' in config:
        judge_model = config['judge'].get('model', '')
        judge_key = config['judge'].get('api_key', '')
        
        # Check for invalid model names
        if judge_model == 'gpt-5.1':
            issues.append("⚠️  Judge model 'gpt-5.1' does not exist")
            fixes['judge_model'] = 'gpt-4'
        elif judge_model == 'gpt-5':
            issues.append("⚠️  Judge model 'gpt-5' does not exist")
            fixes['judge_model'] = 'gpt-4'
        
        # Check API key
        if not judge_key or judge_key == 'your-anthropic-api-key':
            issues.append("❌ Judge API key not set")
        elif len(judge_key) < 20:
            issues.append("⚠️  Judge API key looks too short")
        else:
            print(f"✅ Judge model: {judge_model}")
            print(f"✅ Judge API key: Set ({len(judge_key)} chars)")
    else:
        issues.append("❌ Judge config missing")
    
    # Print issues
    if issues:
        print("\n" + "="*80)
        print("  ISSUES FOUND")
        print("="*80)
        for issue in issues:
            print(issue)
    
    # Offer to fix
    if fixes:
        print("\n" + "="*80)
        print("  SUGGESTED FIXES")
        print("="*80)
        
        if 'translation_model' in fixes:
            print(f"Change translation model to: {fixes['translation_model']}")
        if 'judge_model' in fixes:
            print(f"Change judge model to: {fixes['judge_model']}")
        
        response = input("\nApply fixes? (y/n): ")
        if response.lower() == 'y':
            # Apply fixes
            if 'translation_model' in fixes:
                config['translation']['model'] = fixes['translation_model']
            if 'judge_model' in fixes:
                config['judge']['model'] = fixes['judge_model']
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Config updated: {config_path}")
            print("\nRun this script again to verify:")
            print(f"  python check_config.py")
        else:
            print("\nNo changes made.")
            print("\nTo fix manually, edit config.json:")
            if 'translation_model' in fixes:
                print(f'  "translation": {{"model": "{fixes["translation_model"]}"}}')
            if 'judge_model' in fixes:
                print(f'  "judge": {{"model": "{fixes["judge_model"]}"}}')
    
    if not issues:
        print("\n" + "="*80)
        print("  ✅ CONFIG LOOKS GOOD!")
        print("="*80)
        print("\nNext step: Test with a small sample")
        print("  python run_single_option.py --option A --max_dialogues 2")


def list_valid_models():
    """List valid model names."""
    print("\n" + "="*80)
    print("  VALID MODEL NAMES")
    print("="*80)
    
    print("\n📝 OpenAI Models (for translation):")
    print("  - gpt-4")
    print("  - gpt-4-turbo")
    print("  - gpt-4o")
    print("  - gpt-3.5-turbo (faster, cheaper)")
    
    print("\n📝 Anthropic Models (for judge):")
    print("  - claude-3-opus-20240229")
    print("  - claude-3-sonnet-20240229")
    print("  - claude-3-haiku-20240307")
    print("  - claude-sonnet-4 (if available)")
    
    print("\n📝 Other Models (via LiteLLM):")
    print("  - gemini/gemini-pro")
    print("  - gemini/gemini-1.5-pro")
    print("  - See: https://docs.litellm.ai/docs/providers")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list-models":
        list_valid_models()
    else:
        config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
        check_config(config_path)
