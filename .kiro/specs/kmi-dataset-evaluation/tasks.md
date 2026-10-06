# Implementation Plan: KMI Dataset Evaluation

## Overview

This implementation adds support for the KMI (Korean Mental health Interview) dataset to the mind-eval evaluation framework. The approach follows the proven SimpsyDial architecture exactly, reusing existing infrastructure for judgment generation, profile extraction, and utility functions. Only two new files are created: the KMI conversion script (adapting SimpsyDial patterns) and the Korean judgment prompts module (translating existing English prompts).

**Key Implementation Strategy:**
- **Reuse** mindeval/scripts/generate_judgments.py for all judgment generation
- **Reuse** mindeval/judge_prompts.py structure for Korean prompts
- **Adapt** convert_simpsydial.py patterns for KMI's bilingual structure
- **Reuse** mindeval.utils (JSONL I/O), mindeval.inference (LLM calls), mindeval.variables (enums)

## Tasks

- [x] 1. Create Korean judgment prompts module
  - Create mindeval/judge_prompts_ko.py following judge_prompts.py and judge_prompts_zh.py structure
  - Translate JUDGE_PROMPT_TEMPLATE to Korean as JUDGE_PROMPT_TEMPLATE_KO
  - Preserve all Template variable placeholders (${name}, ${conversation_str}, etc.)
  - Preserve all XML tags (<evaluation_framework>, <criterion_1>, etc.)
  - Maintain semantic equivalence with English version
  - Include Korean translations for all five criteria with rating scales
  - Add module docstring explaining usage
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 2. Set up KMI data directory structure
  - Create data/KMI/test/ directory for output files
  - Verify data/KMI/raw/kmi.json exists and is readable
  - Document expected directory structure in conversion script docstring
  - _Requirements: 8.3, 8.4_

- [ ] 3. Implement KMI conversion script core structure
  - [-] 3.1 Create mindeval/scripts/convert_kmi.py with module docstring
    - Include usage examples for all three options in docstring
    - Import required modules: json, pathlib, typing, tqdm
    - Import mindeval.utils (save_to_jsonl, load_jsonl)
    - Import mindeval.inference (InferenceEngine)
    - Import mindeval.variables (SLEEP_QUALITY, ATTITUDE_TOWARDS_MINDFULNESS)
    - _Requirements: 10.4, 11.1, 11.2_

  - [x] 3.2 Define DEFAULT_KOREAN_PROFILE constant
    - Set race="Asian" and region="urban" as defaults
    - Set all other fields to "Unknown" or reasonable defaults
    - Follow DEFAULT_PROFILE structure from convert_simpsydial.py
    - _Requirements: 3.6, 13.2, 13.3_

  - [x] 3.3 Implement create_interaction() function
    - Accept parameters: dialogue (Dict), profile (Dict), use_korean (bool), option (str)
    - Extract utterance_ko or utterance_en based on use_korean flag
    - Map role: "Therapist" → "assistant", "Client" → "user"
    - Build Mind-Eval format with member_profile, interaction, metadata
    - Set metadata fields: source="KMI", original_id, category, language, option, profile_extracted
    - _Requirements: 1.2, 1.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 4. Implement profile extraction for KMI dialogues
  - [x] 4.1 Implement format_client_only_for_profile_extraction() helper
    - Reuse function from convert_simpsydial.py
    - Format only client turns with turn numbers
    - Use utterance_en fields for extraction input
    - _Requirements: 3.2_

  - [-] 4.2 Implement extract_profile_from_korean_dialogue() function
    - Adapt extract_profile_from_english_dialogue() from convert_simpsydial.py
    - Accept dialogue (List[Dict]) and model_api_params (Dict)
    - Build extraction prompt with Korean cultural context notes
    - Call InferenceEngine with extraction prompt
    - Parse JSON response and merge with DEFAULT_KOREAN_PROFILE
    - Handle JSON parsing errors by returning default profile
    - Log warnings on extraction failure
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 7.5, 13.1, 13.4_

- [ ] 5. Implement main conversion logic
  - [ ] 5.1 Implement convert_kmi_dialogue() function
    - Accept dialogue (Dict), extract_profile (bool), profile_extraction_params (Optional[Dict])
    - Validate dialogue has required fields (id, category_en, dialogue list)
    - Check each turn has role, utterance_ko, utterance_en fields
    - Skip dialogue and log warning if fields missing
    - Extract profile if extract_profile=True, else use defaults
    - Call create_interaction() three times for options A, B, C
    - Return tuple of (option_a_dict, option_b_dict, option_c_dict)
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 7.2, 14_

  - [~] 5.2 Implement main() function with command-line interface
    - Accept parameters: input_path, output_dir, max_dialogues, extract_profile, profile_extraction_params, skip_existing
    - Load existing JSONL files if skip_existing=True
    - Extract processed dialogue IDs from existing files
    - Load kmi.json and apply max_dialogues limit
    - Filter out already processed dialogues
    - Process remaining dialogues with tqdm progress bar
    - Combine existing + new results and save to three JSONL files
    - Report counts: already converted, newly processed, skipped
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5, 6, 8.1, 8.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2, 12.3, 12.4_

  - [~] 5.3 Add argparse command-line interface
    - Add --input_path argument (required)
    - Add --output_dir argument (required)
    - Add --max_dialogues argument (optional, type=int)
    - Add --extract_profile flag (default=False)
    - Add --profile_extraction_params argument (optional, JSON string)
    - Add --skip_existing flag (default=True)
    - Parse arguments and call main() function
    - Handle invalid parameters with usage message
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [~] 6. Add error handling and validation
  - Add try-except for file I/O operations
  - Validate kmi.json structure on load
  - Raise ValueError for missing required fields with descriptive messages
  - Implement exponential backoff retry for API rate limits (3 attempts)
  - Save progress and exit with error message if retries exhausted
  - Log warnings for skipped dialogues with dialogue IDs
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [~] 7. Checkpoint - Test conversion script
  - Run conversion on small sample (max_dialogues=5) without profile extraction
  - Verify three output files created with correct naming
  - Verify Mind-Eval format compliance for all three options
  - Verify metadata fields correctly identify language and option
  - Ensure all tests pass, ask the user if questions arise

- [ ] 8. Test profile extraction integration
  - [~] 8.1 Run conversion with profile extraction enabled on 5 dialogues
    - Verify profile extraction uses utterance_en fields
    - Verify extracted profiles merged with defaults
    - Verify race="Asian" and region="urban" in all profiles
    - _Requirements: 3.2, 3.3, 3.6, 10_

  - [ ]* 8.2 Write unit tests for profile extraction
    - Test valid LLM response parsing
    - Test invalid JSON handling with default fallback
    - Test Korean cultural context in extraction prompt
    - Test Unknown fallback for undetermined attributes
    - _Requirements: 3.4, 3.5, 7.5, 13.4, 15, 17_

- [ ] 9. Test judgment generation integration
  - [~] 9.1 Generate judgments for Option A (English dialogue + English prompts)
    - Run generate_judgments.py with option_a_interactions_en.jsonl
    - Use default English judge prompts (judge_prompts.py)
    - Verify judgment output format
    - _Requirements: 6.1, 10.1_

  - [~] 9.2 Generate judgments for Option B (Korean dialogue + Korean prompts)
    - Run generate_judgments.py with option_b_interactions_ko.jsonl
    - Use --judge_template_path pointing to judge_prompts_ko.py
    - Verify Korean prompts loaded correctly
    - Verify judgment output format
    - _Requirements: 6.2, 6.4, 10.2_

  - [~] 9.3 Generate judgments for Option C (Korean dialogue + English prompts)
    - Run generate_judgments.py with option_c_interactions_ko.jsonl
    - Use default English judge prompts
    - Verify judgment output format
    - _Requirements: 6.3, 6.5_

  - [ ]* 9.4 Write integration tests for judgment generation
    - Test all three options produce valid judgment files
    - Test Korean prompts maintain template variable consistency
    - Test judgment scores are within valid ranges
    - _Requirements: 13_

- [~] 10. Test skip_existing functionality
  - Run conversion twice with skip_existing=True
  - Verify second run skips already converted dialogues
  - Verify existing conversions preserved in output files
  - Verify only new dialogues processed
  - _Requirements: 2.3, 2.4, 6, 8.1, 8.2, 16_

- [~] 11. Final checkpoint - Full dataset conversion
  - Run conversion on full dataset (1000 dialogues) with profile extraction
  - Monitor progress with tqdm
  - Verify all three output files contain 1000 interactions
  - Verify no duplicate dialogue IDs in output files
  - Ensure all tests pass, ask the user if questions arise

- [~] 12. Documentation and usage examples
  - Add comprehensive docstrings to all functions
  - Update module docstring with usage examples for all three options
  - Document command-line interface in script header
  - Add example commands for judgment generation workflow
  - Document code reuse strategy and architecture decisions
  - _Requirements: 10_

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of core functionality
- Profile extraction is optional and can be disabled for faster processing
- The implementation reuses proven patterns from SimpsyDial to minimize new code
- Korean prompts should be professionally translated to maintain semantic equivalence
- All three options share the same profile extraction to ensure consistency

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3.1", "3.2"] },
    { "id": 2, "tasks": ["3.3", "4.1"] },
    { "id": 3, "tasks": ["4.2", "5.1"] },
    { "id": 4, "tasks": ["5.2"] },
    { "id": 5, "tasks": ["5.3", "6"] },
    { "id": 6, "tasks": ["7"] },
    { "id": 7, "tasks": ["8.1"] },
    { "id": 8, "tasks": ["8.2", "9.1"] },
    { "id": 9, "tasks": ["9.2", "9.3"] },
    { "id": 10, "tasks": ["9.4", "10"] },
    { "id": 11, "tasks": ["11"] },
    { "id": 12, "tasks": ["12"] }
  ]
}
```
