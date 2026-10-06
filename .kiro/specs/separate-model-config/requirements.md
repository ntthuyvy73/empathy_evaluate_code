# Requirements Document

## Introduction

This document specifies requirements for a cleaner, more modular configuration system that separates translation model configuration from judge model configuration. The system introduces dedicated configuration classes for each model type, enables support for multiple named configurations per model type, provides centralized API key management with environment variable fallback, and maintains backward compatibility with existing code.

## Glossary

- **TranslationModelConfig**: Configuration dataclass for translation models with translation-specific defaults (temperature 0.3, max_tokens 4000)
- **JudgeModelConfig**: Configuration dataclass for judge/evaluator models with evaluation-specific defaults
- **ModelConfig**: Base dataclass for all model configurations containing common fields (model, api_key, api_base, temperature, max_tokens, timeout, max_retries)
- **ApiKeyManager**: Singleton class that manages API keys for different model providers with environment variable fallback
- **ModelConfigFactory**: Factory class for creating and retrieving model configurations, supporting named configurations
- **ConfigRegistry**: Global registry for storing named configurations
- **InferenceEngine**: Existing component that consumes model configuration dictionaries

## Requirements

### Requirement 1: Base Model Configuration Class

**User Story:** As a developer, I want a base configuration class for all model types, so that common configuration fields are defined consistently across the system.

#### Acceptance Criteria

1. THE ModelConfig class SHALL define fields for model, api_key, api_base, temperature, max_tokens, timeout, and max_retries
2. THE ModelConfig.to_dict() method SHALL return a dictionary containing all configuration fields
3. WHEN ModelConfig.validate() is called THEN the system SHALL return a list of validation error messages
4. WHEN temperature is less than 0.0 or greater than 2.0 THEN ModelConfig.validate() SHALL return an error message
5. WHEN max_tokens is provided and is less than or equal to 0 THEN ModelConfig.validate() SHALL return an error message
6. WHEN timeout is less than or equal to 0 THEN ModelConfig.validate() SHALL return an error message
7. WHEN max_retries is less than 0 THEN ModelConfig.validate() SHALL return an error message

### Requirement 2: Translation Model Configuration Class

**User Story:** As a developer, I want a dedicated configuration class for translation models, so that translation-specific defaults and validation are encapsulated in one place.

#### Acceptance Criteria

1. THE TranslationModelConfig class SHALL inherit from ModelConfig
2. THE TranslationModelConfig default model SHALL be "gpt-4"
3. THE TranslationModelConfig default temperature SHALL be 0.3
4. THE TranslationModelConfig default max_tokens SHALL be 4000
5. WHEN a TranslationModelConfig is serialized to a dictionary and back THEN the resulting object SHALL equal the original object

### Requirement 3: Judge Model Configuration Class

**User Story:** As a developer, I want a dedicated configuration class for judge models, so that evaluation-specific defaults and validation are encapsulated in one place.

#### Acceptance Criteria

1. THE JudgeModelConfig class SHALL inherit from ModelConfig
2. THE JudgeModelConfig default model SHALL be "claude-sonnet-4"
3. THE JudgeModelConfig default temperature SHALL be 0.3
4. THE JudgeModelConfig default max_tokens SHALL be 4000
5. WHEN a JudgeModelConfig is serialized to a dictionary and back THEN the resulting object SHALL equal the original object

### Requirement 4: API Key Management

**User Story:** As a developer, I want centralized API key management, so that keys are handled securely and consistently across all model types.

#### Acceptance Criteria

1. THE ApiKeyManager SHALL be a singleton class
2. WHEN ApiKeyManager.get_api_key() is called for a model_type THEN the system SHALL return the API key from config file if present
3. WHEN no API key is found in the config file THEN ApiKeyManager.get_api_key() SHALL fall back to the appropriate environment variable (TRANSLATION_API_KEY or JUDGE_API_KEY)
4. WHEN no API key is found in config file or environment THEN ApiKeyManager.get_api_key() SHALL return an empty string
5. THE ApiKeyManager SHALL never log or print API key values

### Requirement 5: Model Configuration Factory

**User Story:** As a developer, I want a factory for creating model configurations, so that configurations are loaded consistently and support named configurations.

#### Acceptance Criteria

1. WHEN ModelConfigFactory.get_translation_config() is called with no name THEN the system SHALL return the default translation configuration
2. WHEN ModelConfigFactory.get_translation_config() is called with a name THEN the system SHALL return the named translation configuration if it exists
3. WHEN ModelConfigFactory.get_judge_config() is called with no name THEN the system SHALL return the default judge configuration
4. WHEN ModelConfigFactory.get_judge_config() is called with a name THEN the system SHALL return the named judge configuration if it exists
5. WHEN a named configuration does not exist THEN the system SHALL fall back to the default configuration and log a warning
6. WHEN ModelConfigFactory.register_translation_config() is called THEN the system SHALL store the configuration with the given name
7. WHEN ModelConfigFactory.register_judge_config() is called THEN the system SHALL store the configuration with the given name

### Requirement 6: Configuration Registry

**User Story:** As a developer, I want a global registry for named configurations, so that configurations can be accessed throughout the application.

#### Acceptance Criteria

1. THE ConfigRegistry SHALL store translation configurations indexed by name
2. THE ConfigRegistry SHALL store judge configurations indexed by name
3. WHEN ConfigRegistry.get_translation() is called with a valid name THEN the system SHALL return the TranslationModelConfig
4. WHEN ConfigRegistry.get_judge() is called with a valid name THEN the system SHALL return the JudgeModelConfig
5. WHEN ConfigRegistry.clear() is called THEN the system SHALL remove all registered configurations

### Requirement 7: Backward Compatible Access Functions

**User Story:** As a developer using existing scripts, I want the get_translation_config() and get_judge_config() functions to work unchanged, so that my existing code continues to function without modification.

#### Acceptance Criteria

1. WHEN get_translation_config() is called with no arguments THEN the system SHALL return a dictionary with keys: model, api_key, api_base, temperature, max_tokens, timeout, max_retries
2. WHEN get_judge_config() is called with no arguments THEN the system SHALL return a dictionary with keys: model, api_key, api_base, temperature, max_tokens, timeout, max_retries
3. WHEN get_translation_config() is called THEN the returned dictionary SHALL be compatible with the InferenceEngine constructor
4. WHEN get_judge_config() is called THEN the returned dictionary SHALL be compatible with the InferenceEngine constructor
5. THE get_translation_config() function signature SHALL accept optional config_path and name parameters with name defaulting to "default"
6. THE get_judge_config() function signature SHALL accept optional config_path and name parameters with name defaulting to "default"

### Requirement 8: Configuration File Format

**User Story:** As a user, I want a clear configuration file format for defining multiple translation and judge models, so that I can easily switch between different model configurations.

#### Acceptance Criteria

1. THE configuration file SHALL support a "translation_models" section containing named translation configurations
2. THE configuration file SHALL support a "judge_models" section containing named judge configurations
3. THE configuration file SHALL support a "google_translate" section for Google Translate configuration
4. WHEN a configuration file is loaded THEN the system SHALL parse JSON and validate the structure
5. WHEN a configuration file contains invalid JSON THEN the system SHALL raise a JSONDecodeError with the file path

### Requirement 9: Configuration Loading Priority

**User Story:** As a user, I want clear priority rules for configuration loading, so that I can override settings in predictable ways.

#### Acceptance Criteria

1. WHEN a config file path is provided and exists THEN the system SHALL load configuration from the file
2. WHEN a config file path is provided but does not exist THEN the system SHALL log a warning and fall back to environment variables
3. WHEN no config file is provided THEN the system SHALL load configuration from environment variables
4. WHEN a named configuration is requested that does not exist THEN the system SHALL use the first available configuration as default

### Requirement 10: Validation and Error Handling

**User Story:** As a developer, I want comprehensive validation with clear error messages, so that configuration problems are easy to diagnose.

#### Acceptance Criteria

1. WHEN validate_config() is called THEN the system SHALL return a dictionary with keys "translation" and "judge"
2. WHEN a configuration is valid THEN validate_config() SHALL return an empty list for that configuration type
3. WHEN a model name is empty or missing THEN validate_config() SHALL return an error message "Model name is required"
4. WHEN an API key is missing THEN validate_config() SHALL return an error message "API key is required"
5. WHEN validate_config() returns no errors for a configuration THEN that configuration SHALL be usable with InferenceEngine

### Requirement 11: API Key Security

**User Story:** As a security-conscious user, I want API keys to be protected from accidental exposure, so that my credentials remain secure.

#### Acceptance Criteria

1. WHEN print_config_summary() is called THEN the system SHALL display "✓ Set" or "✗ Missing" instead of the actual API key value
2. WHEN configuration is logged THEN API key values SHALL NOT appear in log output
3. WHEN an error occurs involving API keys THEN the error message SHALL NOT contain the API key value

### Requirement 12: Default Configuration Availability

**User Story:** As a developer, I want default configurations to always be available, so that the system works out of the box without requiring a configuration file.

#### Acceptance Criteria

1. WHEN get_translation_config() is called without a config file THEN the system SHALL return a configuration with model "gpt-4"
2. WHEN get_judge_config() is called without a config file THEN the system SHALL return a configuration with model "claude-sonnet-4"
3. WHEN no environment variables are set THEN the system SHALL return default configurations with empty API key strings

### Requirement 13: Configuration Caching

**User Story:** As a developer, I want configuration caching, so that repeated configuration access does not incur unnecessary file I/O overhead.

#### Acceptance Criteria

1. WHEN a configuration is loaded for the first time THEN the system SHALL cache the configuration
2. WHEN the same configuration is requested again THEN the system SHALL return the cached configuration
3. WHEN ConfigRegistry.clear() is called THEN the system SHALL clear all cached configurations
