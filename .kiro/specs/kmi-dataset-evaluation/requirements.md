# Requirements Document: KMI Dataset Evaluation

## Introduction

This document specifies the requirements for adding KMI (Korean Mental health Interview) dataset support to the mind-eval evaluation framework. The KMI dataset contains 1000 Korean-English bilingual therapy dialogues with parallel translations. The system SHALL enable three distinct evaluation options: (A) English utterances with English judgment prompts, (B) Korean utterances with Korean judgment prompts, and (C) Korean utterances with English judgment prompts. This cross-lingual evaluation capability allows researchers to assess how language choice in both dialogue content and evaluation criteria affects therapeutic quality judgments.

## Glossary

- **KMI_Dataset**: Korean Mental health Interview dataset containing 1000 bilingual therapy dialogues
- **Conversion_Script**: The convert_kmi.py script that transforms KMI raw data into Mind-Eval format
- **Option_A**: Evaluation using English utterances with English judgment prompts
- **Option_B**: Evaluation using Korean utterances with Korean judgment prompts
- **Option_C**: Evaluation using Korean utterances with English judgment prompts
- **Mind_Eval_Format**: The standardized format used by the mind-eval framework for interactions
- **Profile_Extraction**: The process of extracting client profile attributes from dialogue content using LLM
- **Judge_Prompts_Module**: Python module containing judgment prompt templates
- **Judgment_Generation_Script**: The existing generate_judgments.py script that creates judgments from interactions
- **JSONL_File**: JSON Lines file format where each line is a valid JSON object
- **Interaction**: A complete therapy dialogue in Mind-Eval format with profile and conversation turns
- **Raw_KMI_Data**: The original kmi.json file containing unprocessed KMI dialogues
- **Utterance**: A single turn of dialogue spoken by either therapist or client
- **Korean_Prompts**: Korean-language translation of judgment evaluation criteria

## Requirements

### Requirement 1: KMI Data Conversion

**User Story:** As a researcher, I want to convert KMI raw data into Mind-Eval format, so that I can evaluate therapy dialogues using the mind-eval framework.

#### Acceptance Criteria

1. WHEN the Conversion_Script is executed with valid Raw_KMI_Data, THE Conversion_Script SHALL load all dialogue records from the kmi.json file
2. WHEN a dialogue is converted, THE Conversion_Script SHALL extract both utterance_ko and utterance_en fields from each turn
3. WHEN a dialogue is converted, THE Conversion_Script SHALL map Therapist role to assistant and Client role to user
4. WHEN the Conversion_Script processes a dialogue, THE Conversion_Script SHALL generate three output variants for Option_A, Option_B, and Option_C
5. WHEN generating Option_A output, THE Conversion_Script SHALL use utterance_en fields for all conversation turns
6. WHEN generating Option_B output, THE Conversion_Script SHALL use utterance_ko fields for all conversation turns
7. WHEN generating Option_C output, THE Conversion_Script SHALL use utterance_ko fields for all conversation turns
8. WHEN conversion completes, THE Conversion_Script SHALL write three separate JSONL_Files named option_a_interactions_en.jsonl, option_b_interactions_ko.jsonl, and option_c_interactions_ko.jsonl

### Requirement 2: Configurable Dialogue Processing

**User Story:** As a researcher, I want to control how many dialogues are processed, so that I can test with small samples or process the full dataset.

#### Acceptance Criteria

1. WHEN the Conversion_Script is executed with a max_dialogues parameter, THE Conversion_Script SHALL process at most that number of dialogues
2. WHEN the Conversion_Script is executed without a max_dialogues parameter, THE Conversion_Script SHALL process all available dialogues in the Raw_KMI_Data
3. WHEN the Conversion_Script is executed with skip_existing enabled, THE Conversion_Script SHALL load existing output files and skip dialogues already converted
4. WHEN the Conversion_Script encounters a dialogue ID that exists in the output files, THE Conversion_Script SHALL exclude that dialogue from processing

### Requirement 3: Profile Extraction from Korean Dialogues

**User Story:** As a researcher, I want to extract client profiles from KMI dialogues, so that judgments can be contextualized with member information.

#### Acceptance Criteria

1. WHEN Profile_Extraction is enabled, THE Conversion_Script SHALL extract client profile attributes from dialogue content using an LLM
2. WHEN extracting profiles, THE Conversion_Script SHALL use utterance_en fields as input to the extraction prompt
3. WHEN Profile_Extraction succeeds, THE Conversion_Script SHALL merge extracted attributes with default profile values
4. WHEN Profile_Extraction fails, THE Conversion_Script SHALL use default Korean profile values and log a warning
5. WHEN Profile_Extraction is disabled, THE Conversion_Script SHALL use default Korean profile values for all dialogues
6. WHEN a profile is created, THE Conversion_Script SHALL set the race field to Asian for all KMI dialogues

### Requirement 4: Mind-Eval Format Compliance

**User Story:** As a developer, I want converted interactions to follow Mind-Eval format, so that they work with existing evaluation infrastructure.

#### Acceptance Criteria

1. WHEN an Interaction is created, THE Conversion_Script SHALL include member_profile, interaction, and metadata fields
2. WHEN an Interaction is created, THE member_profile field SHALL contain all required Mind-Eval profile attributes
3. WHEN an Interaction is created, THE interaction field SHALL contain a list of turns with role and content fields
4. WHEN an Interaction is created, THE metadata field SHALL include source, original_id, category, language, option, and profile_extracted fields
5. WHEN creating Option_A metadata, THE Conversion_Script SHALL set language to en and option to a
6. WHEN creating Option_B metadata, THE Conversion_Script SHALL set language to ko and option to b
7. WHEN creating Option_C metadata, THE Conversion_Script SHALL set language to ko and option to c

### Requirement 5: Korean Judgment Prompts

**User Story:** As a researcher, I want Korean-language judgment prompts, so that I can evaluate Korean dialogues using native-language criteria.

#### Acceptance Criteria

1. THE Judge_Prompts_Module for Korean SHALL provide a JUDGE_PROMPT_TEMPLATE_KO template
2. THE JUDGE_PROMPT_TEMPLATE_KO SHALL contain evaluation framework descriptions in Korean
3. THE JUDGE_PROMPT_TEMPLATE_KO SHALL contain all five criteria descriptions in Korean
4. THE JUDGE_PROMPT_TEMPLATE_KO SHALL contain rating scale explanations in Korean
5. THE JUDGE_PROMPT_TEMPLATE_KO SHALL maintain semantic equivalence with the English JUDGE_PROMPT_TEMPLATE
6. THE JUDGE_PROMPT_TEMPLATE_KO SHALL use the same Template variable placeholders as the English version

### Requirement 6: Judgment Generation Integration

**User Story:** As a researcher, I want to generate judgments for all three options, so that I can compare cross-lingual evaluation results.

#### Acceptance Criteria

1. WHEN generating judgments for Option_A, THE Judgment_Generation_Script SHALL use English interactions and English judge prompts
2. WHEN generating judgments for Option_B, THE Judgment_Generation_Script SHALL use Korean interactions and Korean judge prompts
3. WHEN generating judgments for Option_C, THE Judgment_Generation_Script SHALL use Korean interactions and English judge prompts
4. WHEN the Judgment_Generation_Script is executed with a judge_template_path parameter, THE Judgment_Generation_Script SHALL load the specified Korean_Prompts module
5. WHEN the Judgment_Generation_Script is executed without a judge_template_path parameter, THE Judgment_Generation_Script SHALL use the default English judge prompts

### Requirement 7: Data Validation and Error Handling

**User Story:** As a developer, I want robust error handling, so that conversion failures are handled gracefully.

#### Acceptance Criteria

1. WHEN the Raw_KMI_Data file is missing required fields, THE Conversion_Script SHALL raise a ValueError with a descriptive message
2. WHEN a dialogue is missing utterance_ko or utterance_en fields, THE Conversion_Script SHALL skip that dialogue and log a warning
3. WHEN Profile_Extraction encounters an API rate limit error, THE Conversion_Script SHALL implement exponential backoff retry logic with three attempts
4. WHEN Profile_Extraction retries are exhausted, THE Conversion_Script SHALL save progress and exit with an error message
5. WHEN the LLM returns invalid JSON during Profile_Extraction, THE Conversion_Script SHALL use default profile values and continue processing

### Requirement 8: Output File Management

**User Story:** As a researcher, I want incremental output file updates, so that I can resume interrupted conversion runs.

#### Acceptance Criteria

1. WHEN the Conversion_Script completes processing new dialogues, THE Conversion_Script SHALL append results to existing JSONL_Files
2. WHEN the Conversion_Script writes output files, THE Conversion_Script SHALL combine existing conversions with new conversions
3. WHEN output files do not exist, THE Conversion_Script SHALL create new JSONL_Files in the specified output directory
4. WHEN the output directory does not exist, THE Conversion_Script SHALL create the directory before writing files

### Requirement 9: Metadata Tracking

**User Story:** As a researcher, I want detailed metadata for each interaction, so that I can trace results back to source data.

#### Acceptance Criteria

1. WHEN an Interaction is created, THE metadata field SHALL include the original KMI dialogue ID
2. WHEN an Interaction is created, THE metadata field SHALL include the category from the KMI dataset
3. WHEN an Interaction is created, THE metadata field SHALL indicate whether Profile_Extraction was performed
4. WHEN an Interaction is created, THE metadata field SHALL identify the source as KMI
5. WHEN an Interaction is created, THE metadata field SHALL specify which option variant it represents

### Requirement 10: Code Reuse and Architecture

**User Story:** As a developer, I want to reuse existing infrastructure, so that the implementation is maintainable and consistent.

#### Acceptance Criteria

1. THE Conversion_Script SHALL reuse the existing generate_judgments.py script for judgment generation
2. THE Conversion_Script SHALL reuse the existing judge_prompts.py module for English prompts
3. THE Conversion_Script SHALL reuse profile extraction patterns from convert_simpsydial.py
4. THE Conversion_Script SHALL reuse utility functions from mindeval.utils for JSONL I/O
5. THE Conversion_Script SHALL reuse the InferenceEngine class from mindeval.inference for LLM calls
6. THE Korean_Prompts module SHALL follow the same structure as judge_prompts.py and judge_prompts_zh.py

### Requirement 11: Command-Line Interface

**User Story:** As a researcher, I want a command-line interface for conversion, so that I can easily configure and run the conversion process.

#### Acceptance Criteria

1. THE Conversion_Script SHALL accept an input_path parameter specifying the path to kmi.json
2. THE Conversion_Script SHALL accept an output_dir parameter specifying the directory for output files
3. THE Conversion_Script SHALL accept an optional max_dialogues parameter to limit processing
4. THE Conversion_Script SHALL accept an extract_profile boolean parameter to enable Profile_Extraction
5. THE Conversion_Script SHALL accept an optional profile_extraction_params parameter with API configuration
6. THE Conversion_Script SHALL accept a skip_existing boolean parameter to enable incremental processing
7. WHEN command-line parameters are invalid, THE Conversion_Script SHALL display usage information and exit with an error code

### Requirement 12: Progress Tracking

**User Story:** As a researcher, I want to monitor conversion progress, so that I can estimate completion time for large batches.

#### Acceptance Criteria

1. WHEN the Conversion_Script processes multiple dialogues, THE Conversion_Script SHALL display a progress bar using tqdm
2. WHEN the Conversion_Script loads existing conversions, THE Conversion_Script SHALL report the count of already converted files
3. WHEN the Conversion_Script completes, THE Conversion_Script SHALL report the total number of dialogues processed
4. WHEN the Conversion_Script skips dialogues, THE Conversion_Script SHALL report the count of skipped dialogues

### Requirement 13: Korean Cultural Context

**User Story:** As a researcher, I want profile extraction to consider Korean cultural context, so that extracted profiles are culturally appropriate.

#### Acceptance Criteria

1. WHEN extracting profiles from KMI dialogues, THE Profile_Extraction prompt SHALL consider Korean cultural concepts such as family dynamics and social pressure
2. WHEN extracting profiles from KMI dialogues, THE default profile SHALL set region to urban as a reasonable default for Korean context
3. WHEN extracting profiles from KMI dialogues, THE default profile SHALL set race to Asian
4. WHEN Profile_Extraction cannot determine an attribute, THE Conversion_Script SHALL use Unknown rather than making cultural assumptions
