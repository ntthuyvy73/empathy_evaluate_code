"""
Configuration management for Mind-Eval evaluation.

This module handles model configurations, API keys, and environment variables
for translation and evaluation models.

Usage:
    from mindeval.config import get_translation_config, get_judge_config
    
    # Get translation model config
    translation_config = get_translation_config()
    
    # Get judge model config  
    judge_config = get_judge_config()
    
    # Use in scripts
    from mindeval.scripts.convert_simpsydial import main as convert_main
    convert_main(
        model_api_params=translation_config,
        ...
    )
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a model."""
    model: str
    api_key: str
    api_base: Optional[str] = None
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    timeout: int = 60
    max_retries: int = 3


class ConfigManager:
    """Manages model configurations from environment variables and config files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to config file (JSON). If None, uses environment variables.
        """
        self.config_path = config_path
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            return {}
    
    def get_translation_config(self) -> Dict[str, Any]:
        """Get translation model configuration."""
        # Priority: config file > environment variables > defaults
        
        # Check config file
        if 'translation' in self.config_data:
            config = self.config_data['translation']
            return {
                'model': config.get('model', 'gpt-4'),
                'api_key': config.get('api_key', ''),
                'api_base': config.get('api_base', None),
                'temperature': config.get('temperature', 0.3),
                'max_tokens': config.get('max_tokens', None),
                'timeout': config.get('timeout', 60),
                'max_retries': config.get('max_retries', 3)
            }
        
        # Check environment variables
        translation_model = os.environ.get('TRANSLATION_MODEL', 'gpt-4')
        translation_api_key = os.environ.get('TRANSLATION_API_KEY', '')
        translation_api_base = os.environ.get('TRANSLATION_API_BASE', None)
        
        return {
            'model': translation_model,
            'api_key': translation_api_key,
            'api_base': translation_api_base,
            'temperature': 0.3,
            'max_tokens': None,
            'timeout': 60,
            'max_retries': 3
        }
    
    def get_judge_config(self) -> Dict[str, Any]:
        """Get judge model configuration.

        Priority order:
          1. config file 'judges.gpt' section (preferred — named judge)
          2. config file 'judge' section      (legacy fallback)
          3. environment variables
        """
        # 1. Named judge 'gpt' in 'judges' section (new convention)
        named = self.config_data.get("judges", {}).get("gpt")
        if named:
            return {
                "model":       named.get("model", "gpt-5.1"),
                "api_key":     named.get("api_key", ""),
                "api_base":    named.get("api_base", None),
                "temperature": named.get("temperature", 0.3),
                "max_tokens":  named.get("max_tokens", None),
                "timeout":     named.get("timeout", 60),
                "max_retries": named.get("max_retries", 3),
            }

        # 2. Legacy 'judge' section
        if "judge" in self.config_data:
            config = self.config_data["judge"]
            return {
                "model":       config.get("model", "gpt-5.1"),
                "api_key":     config.get("api_key", ""),
                "api_base":    config.get("api_base", None),
                "temperature": config.get("temperature", 0.3),
                "max_tokens":  config.get("max_tokens", None),
                "timeout":     config.get("timeout", 60),
                "max_retries": config.get("max_retries", 3),
            }

        # 3. Environment variables
        return {
            "model":       os.environ.get("JUDGE_MODEL", "gpt-5.1"),
            "api_key":     os.environ.get("JUDGE_API_KEY", ""),
            "api_base":    os.environ.get("JUDGE_API_BASE", None),
            "temperature": 0.3,
            "max_tokens":  None,
            "timeout":     60,
            "max_retries": 3,
        }
    
    def get_profile_extraction_config(self) -> Dict[str, Any]:
        """Get profile extraction model configuration."""
        # Priority: config file > environment variables > defaults (fallback to translation config)
        
        # Check config file
        if 'profile_extraction' in self.config_data:
            config = self.config_data['profile_extraction']
            return {
                'model': config.get('model', 'gpt-4'),
                'api_key': config.get('api_key', ''),
                'api_base': config.get('api_base', None),
                'temperature': config.get('temperature', 0.0),  # Lower temperature for extraction
                'max_tokens': config.get('max_tokens', None),
                'timeout': config.get('timeout', 60),
                'max_retries': config.get('max_retries', 3)
            }
        
        # Fallback to translation config if profile_extraction not specified
        return self.get_translation_config()
    
    def get_google_translate_config(self) -> Dict[str, Any]:
        """Get Google Translate configuration."""
        # Priority: config file > environment variables
        
        # Check config file
        if 'google_translate' in self.config_data:
            config = self.config_data['google_translate']
            return {
                'credentials_path': config.get('credentials_path', ''),
                'project_id': config.get('project_id', ''),
                'location': config.get('location', 'global')
            }
        
        # Check environment variables
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
        
        return {
            'credentials_path': credentials_path,
            'project_id': project_id,
            'location': 'global'
        }
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate that required configuration is present."""
        validation = {}
        
        # Check translation config
        translation_config = self.get_translation_config()
        validation['translation'] = bool(translation_config.get('api_key'))
        
        # Check judge config
        judge_config = self.get_judge_config()
        validation['judge'] = bool(judge_config.get('api_key'))
        
        return validation
    
    def print_config_summary(self):
        """Print configuration summary (without API keys)."""
        translation_config = self.get_translation_config()
        judge_config = self.get_judge_config()
        
        print("\n" + "="*80)
        print("  CONFIGURATION SUMMARY")
        print("="*80)
        
        print("\nTranslation Model:")
        print(f"  Model: {translation_config['model']}")
        print(f"  API Base: {translation_config['api_base'] or 'Default'}")
        print(f"  Temperature: {translation_config['temperature']}")
        print(f"  API Key: {'✓ Set' if translation_config['api_key'] else '✗ Missing'}")
        
        print("\nJudge Model:")
        print(f"  Model: {judge_config['model']}")
        print(f"  API Base: {judge_config['api_base'] or 'Default'}")
        print(f"  Temperature: {judge_config['temperature']}")
        print(f"  API Key: {'✓ Set' if judge_config['api_key'] else '✗ Missing'}")
        
        validation = self.validate_config()
        print("\nValidation:")
        for key, valid in validation.items():
            status = "✓" if valid else "✗"
            print(f"  {status} {key.capitalize()}")
        
        print("\n" + "="*80)


# Global config manager instance
_config_manager = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_translation_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get translation model configuration."""
    manager = get_config_manager(config_path)
    return manager.get_translation_config()


def get_judge_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get judge model configuration (default judge section)."""
    manager = get_config_manager(config_path)
    return manager.get_judge_config()


def get_named_judge_config(name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get a named judge config from the 'judges' section (e.g. 'gpt', 'claude', 'qwen').
    Falls back to the default 'judge' section if the name is not found.

    Supports an optional 'extra_body' dict for provider-specific parameters, e.g.:
        { "enable_thinking": false }   ← disables Qwen3 thinking mode (saves tokens)
    """
    manager = get_config_manager(config_path)
    judges = manager.config_data.get("judges", {})
    if name in judges:
        cfg = judges[name]
        result: Dict[str, Any] = {
            "model":       cfg.get("model", "gpt-4"),
            "api_key":     cfg.get("api_key", ""),
            "api_base":    cfg.get("api_base", None),
            "temperature": cfg.get("temperature", 0.3),
            "max_tokens":  cfg.get("max_tokens", None),
            "timeout":     cfg.get("timeout", 60),
            "max_retries": cfg.get("max_retries", 3),
        }
        if "extra_body" in cfg:
            result["extra_body"] = cfg["extra_body"]
        if "use_anthropic_batch" in cfg:
            result["use_anthropic_batch"] = cfg["use_anthropic_batch"]
        if "thinking_budget_tokens" in cfg:
            result["thinking_budget_tokens"] = cfg["thinking_budget_tokens"]
        return result
    print(f"[config] Named judge '{name}' not found in 'judges' section; "
          "falling back to default 'judge' section.")
    return manager.get_judge_config()


def get_profile_extraction_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get profile extraction model configuration."""
    manager = get_config_manager(config_path)
    return manager.get_profile_extraction_config()


def get_google_translate_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get Google Translate configuration."""
    manager = get_config_manager(config_path)
    return manager.get_google_translate_config()


def validate_config(config_path: Optional[str] = None) -> Dict[str, bool]:
    """Validate configuration."""
    manager = get_config_manager(config_path)
    return manager.validate_config()


def print_config_summary(config_path: Optional[str] = None):
    """Print configuration summary."""
    manager = get_config_manager(config_path)
    manager.print_config_summary()


# Example config file structure
EXAMPLE_CONFIG = {
    "translation": {
        "model": "gpt-4",
        "api_key": "your-openai-api-key",
        "api_base": "https://api.openai.com/v1",
        "temperature": 0.3,
        "max_tokens": 4000,
        "timeout": 60,
        "max_retries": 3
    },
    "judge": {
        "model": "claude-sonnet-4",
        "api_key": "your-anthropic-api-key",
        "api_base": "https://api.anthropic.com",
        "temperature": 0.3,
        "max_tokens": 4000,
        "timeout": 60,
        "max_retries": 3
    },
    "google_translate": {
        "credentials_path": "/path/to/google-credentials.json",
        "project_id": "your-google-cloud-project",
        "location": "global"
    }
}


def create_example_config(output_path: str = "config.example.json"):
    """Create example configuration file."""
    with open(output_path, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f, indent=2)
    print(f"Example config created: {output_path}")
    print("Rename to config.json and fill in your API keys.")


if __name__ == "__main__":
    # Test the config system
    print_config_summary()
    
    # Create example config if requested
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--create-example":
        create_example_config()
