"""
View current configuration (model, API key, etc.)

Usage:
    python view_config.py
    python view_config.py --show-api-key  # Show full API key (be careful!)
"""

import sys
from mindeval.config import get_judge_config, get_translation_config, get_profile_extraction_config


def mask_api_key(api_key: str) -> str:
    """Mask API key for security."""
    if not api_key:
        return "❌ NOT SET"
    if len(api_key) < 10:
        return "***"
    return f"{api_key[:8]}...{api_key[-4:]}"


def main():
    """View configuration."""
    show_full_key = "--show-api-key" in sys.argv
    
    print("\n" + "="*80)
    print("  CURRENT CONFIGURATION")
    print("="*80)
    
    # Judge config (used by Mind-Eval and WAI)
    print("\n📊 JUDGE MODEL (Mind-Eval & WAI)")
    print("-" * 80)
    judge_config = get_judge_config("config.json")
    print(f"  Model:        {judge_config['model']}")
    print(f"  API Base:     {judge_config['api_base'] or 'Default'}")
    print(f"  Temperature:  {judge_config['temperature']}")
    print(f"  Timeout:      {judge_config['timeout']}s")
    print(f"  Max Retries:  {judge_config['max_retries']}")
    
    if show_full_key:
        print(f"  API Key:      {judge_config['api_key']}")
    else:
        print(f"  API Key:      {mask_api_key(judge_config['api_key'])}")
    
    # Translation config
    print("\n🌐 TRANSLATION MODEL (Option A)")
    print("-" * 80)
    translation_config = get_translation_config("config.json")
    print(f"  Model:        {translation_config['model']}")
    print(f"  API Base:     {translation_config['api_base'] or 'Default'}")
    print(f"  Temperature:  {translation_config['temperature']}")
    print(f"  Timeout:      {translation_config['timeout']}s")
    print(f"  Max Retries:  {translation_config['max_retries']}")
    
    if show_full_key:
        print(f"  API Key:      {translation_config['api_key']}")
    else:
        print(f"  API Key:      {mask_api_key(translation_config['api_key'])}")
    
    # Profile extraction config
    print("\n👤 PROFILE EXTRACTION MODEL")
    print("-" * 80)
    profile_config = get_profile_extraction_config("config.json")
    print(f"  Model:        {profile_config['model']}")
    print(f"  API Base:     {profile_config['api_base'] or 'Default'}")
    print(f"  Temperature:  {profile_config['temperature']}")
    print(f"  Timeout:      {profile_config['timeout']}s")
    print(f"  Max Retries:  {profile_config['max_retries']}")
    
    if show_full_key:
        print(f"  API Key:      {profile_config['api_key']}")
    else:
        print(f"  API Key:      {mask_api_key(profile_config['api_key'])}")
    
    print("\n" + "="*80)
    
    # Config source
    print("\n📁 Configuration Source:")
    print("  File: config.json")
    print("  Priority: config.json > environment variables > defaults")
    
    if not show_full_key:
        print("\n💡 Tip: Use --show-api-key to see full API keys (be careful!)")
    
    print()


if __name__ == "__main__":
    main()
