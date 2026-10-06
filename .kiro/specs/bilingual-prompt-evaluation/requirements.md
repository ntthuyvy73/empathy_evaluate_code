# Requirements Document: Bilingual Prompt Evaluation

## 1. Functional Requirements

### 1.1 Bilingual Prompt Template Creation
**Priority**: High  
**Description**: The system shall provide bilingual prompt templates that combine English rubrics with Chinese translations.

**Acceptance Criteria**:
- Bilingual templates contain both English and Chinese sections
- Section markers clearly separate EN and ZH content
- All template variables are consistent between EN and ZH sections
- Templates support the same variable substitution as single-language templates

### 1.2 Judge Prompt Bilingual Support
**Priority**: High  
**Description**: The system shall support bilingual prompts for the main judge evaluation (5 criteria assessment).

**Acceptance Criteria**:
- New module `judge_prompts_bilingual.py` is created
- Module exports `JUDGE_PROMPT_TEMPLATE_BILINGUAL` template
- Template includes all 5 evaluation criteria in both languages
- Template maintains same structure as existing single-language prompts
- All member detail variables are supported

### 1.3 WAI Prompt Bilingual Support
**Priority**: High  
**Description**: The system shall support bilingual prompts for WAI (Working Alliance Inventory) evaluation.

**Acceptance Criteria**:
- New module `wai_prompts_bilingual.py` is created
- All 12 WAI questions (Q1-Q12) have bilingual versions
- Detailed guidelines for all questions are available in both languages
- `build_prompt_bilingual(qid, conversation)` function is implemented
- Chain-of-Thought (CoT) structure is preserved in bilingual format

### 1.4 Configuration Extension
**Priority**: High  
**Description**: The system shall allow users to configure prompt language preference including bilingual option.

**Acceptance Criteria**:
- `config.json` supports `prompt_language` field with values: "en", "zh", "bilingual"
- Configuration can be set independently for judge and WAI evaluations
- Default value is "en" for backward compatibility
- Invalid configuration values are rejected with clear error messages

### 1.5 Prompt Selection Logic
**Priority**: High  
**Description**: The system shall automatically select the appropriate prompt template based on configuration.

**Acceptance Criteria**:
- `select_judge_prompt(prompt_language)` function routes to correct template
- `select_wai_prompt_builder(prompt_language)` function routes to correct builder
- Bilingual mode loads bilingual modules
- Single-language modes continue to work unchanged
- Missing modules trigger appropriate fallback behavior

### 1.6 Template Variable Consistency
**Priority**: High  
**Description**: Bilingual templates shall maintain consistency of template variables between English and Chinese sections.

**Acceptance Criteria**:
- Variable extraction function identifies all template variables
- Validation function checks EN/ZH variable consistency
- Mismatched variables trigger ValueError during template construction
- Error messages clearly indicate which variables are inconsistent

### 1.7 Backward Compatibility
**Priority**: Critical  
**Description**: The system shall maintain full backward compatibility with existing single-language evaluation modes.

**Acceptance Criteria**:
- Existing "en" mode produces identical results as before
- Existing "zh" mode produces identical results as before
- Existing configurations without `prompt_language` field default to "en"
- No breaking changes to existing APIs or interfaces
- All existing tests continue to pass

### 1.8 Output Format Consistency
**Priority**: High  
**Description**: Bilingual evaluations shall produce output in the same format as single-language evaluations.

**Acceptance Criteria**:
- Judge evaluation output contains same 5 scores
- WAI evaluation output contains same structure (evidence, analysis, score)
- Score ranges remain unchanged (1-6 for judge, 1-5 for WAI)
- JSON parsing logic works for all prompt types
- Output schema validation passes for bilingual results

## 2. Non-Functional Requirements

### 2.1 Performance
**Priority**: Medium  
**Description**: Bilingual evaluation shall maintain acceptable performance despite increased token usage.

**Acceptance Criteria**:
- Evaluation completes within 2x the time of single-language evaluation
- Token usage is documented and predictable
- Batch processing is supported for multiple evaluations
- Memory usage increase is less than 200KB per evaluation

### 2.2 Usability
**Priority**: Medium  
**Description**: The bilingual feature shall be easy to configure and use.

**Acceptance Criteria**:
- Configuration change requires only updating `prompt_language` field
- Clear documentation explains bilingual mode benefits and costs
- Example configurations are provided
- Error messages are clear and actionable

### 2.3 Maintainability
**Priority**: Medium  
**Description**: Bilingual prompt templates shall be easy to maintain and update.

**Acceptance Criteria**:
- English and Chinese templates are stored in separate, clearly named modules
- Template combination logic is centralized and reusable
- Changes to single-language templates can be easily propagated to bilingual versions
- Code follows existing project conventions and style

### 2.4 Testability
**Priority**: High  
**Description**: The bilingual feature shall be thoroughly testable.

**Acceptance Criteria**:
- Unit tests cover all new functions and modules
- Integration tests verify end-to-end bilingual evaluation
- Property-based tests validate correctness properties
- Test coverage is at least 90% for new code
- Mock LLM responses are used for deterministic testing

### 2.5 Documentation
**Priority**: Medium  
**Description**: The bilingual feature shall be well-documented.

**Acceptance Criteria**:
- README includes bilingual mode usage instructions
- Configuration examples are provided
- API documentation covers all new functions
- Design rationale is documented
- Cost implications (token usage) are clearly explained

### 2.6 Error Handling
**Priority**: High  
**Description**: The system shall handle errors gracefully and provide clear feedback.

**Acceptance Criteria**:
- Missing template variables raise KeyError with variable names
- Template variable mismatches raise ValueError with details
- Invalid configuration raises ValueError with valid options
- Missing modules trigger ImportError with fallback behavior
- All errors are logged with appropriate severity levels

### 2.7 Security
**Priority**: High  
**Description**: The bilingual feature shall not introduce new security vulnerabilities.

**Acceptance Criteria**:
- Template variables are validated before substitution
- No prompt injection vulnerabilities are introduced
- API keys are not exposed in logs or error messages
- Same security practices as existing modes are maintained
- Input sanitization is applied to conversation text

## 3. Technical Requirements

### 3.1 Module Structure
**Priority**: High  
**Description**: New modules shall follow the existing project structure and conventions.

**Acceptance Criteria**:
- `judge_prompts_bilingual.py` is created in `mindeval/` directory
- `wai_prompts_bilingual.py` is created in `mindeval/wai/` directory
- Modules follow Python naming conventions
- Imports are organized and minimal
- Type hints are used for all function signatures

### 3.2 Template Format
**Priority**: High  
**Description**: Bilingual templates shall use consistent formatting and structure.

**Acceptance Criteria**:
- Section headers use clear, bilingual labels
- Section separator is configurable (default: `\n\n---\n\n`)
- English section appears before Chinese section
- Template variables use `${variable}` syntax
- XML tags are preserved from original templates

### 3.3 Configuration Schema
**Priority**: High  
**Description**: Configuration schema shall be extended to support prompt language selection.

**Acceptance Criteria**:
- `prompt_language` field is optional (defaults to "en")
- Valid values are: "en", "zh", "bilingual"
- Field can be set in "judge" and "translation" sections
- Schema validation rejects invalid values
- Example configuration file is updated

### 3.4 Dependency Management
**Priority**: Medium  
**Description**: The feature shall not introduce new external dependencies.

**Acceptance Criteria**:
- Only standard library modules are used
- No new packages added to requirements
- Existing dependencies (litellm, etc.) are reused
- Import statements are conditional where appropriate

### 3.5 Code Quality
**Priority**: Medium  
**Description**: New code shall meet project quality standards.

**Acceptance Criteria**:
- Code passes linting checks
- Docstrings follow project conventions
- Type hints are complete and accurate
- No code duplication beyond necessary template content
- Functions are focused and single-purpose

## 4. Integration Requirements

### 4.1 InferenceEngine Integration
**Priority**: High  
**Description**: Bilingual prompts shall integrate seamlessly with the existing InferenceEngine.

**Acceptance Criteria**:
- InferenceEngine.generate() accepts bilingual prompts
- InferenceEngine.batch_generate() supports bilingual mode
- Token counting works correctly for bilingual prompts
- Response parsing handles bilingual prompt outputs

### 4.2 WAI Evaluator Integration
**Priority**: High  
**Description**: WAI evaluator shall support bilingual prompt mode.

**Acceptance Criteria**:
- `wai_evaluator.py` can use bilingual prompt builder
- `build_prompt()` function accepts language parameter
- All 12 questions work in bilingual mode
- Dimension score calculations are unchanged
- Output format matches existing WAI results

### 4.3 Script Integration
**Priority**: Medium  
**Description**: Existing evaluation scripts shall support bilingual mode.

**Acceptance Criteria**:
- `generate_judgments.py` supports bilingual configuration
- `generate_wai_judgments.py` supports bilingual configuration
- Command-line arguments allow prompt language selection
- Scripts maintain backward compatibility

### 4.4 Configuration Loading
**Priority**: High  
**Description**: Configuration loading shall support the new prompt_language field.

**Acceptance Criteria**:
- `config.py` parses prompt_language field
- Default values are applied when field is missing
- Validation occurs at configuration load time
- Clear error messages for invalid configurations

## 5. Data Requirements

### 5.1 Template Data
**Priority**: High  
**Description**: All prompt templates shall be available in bilingual format.

**Acceptance Criteria**:
- Judge prompt template combines EN and ZH versions
- All 12 WAI questions have bilingual versions
- All 12 WAI detailed guidelines have bilingual versions
- Prompt scaffolding (instructions, format) is bilingual
- Output format instructions are bilingual

### 5.2 Translation Quality
**Priority**: High  
**Description**: Chinese translations shall accurately convey the meaning of English rubrics.

**Acceptance Criteria**:
- Translations are reviewed for accuracy
- Technical terms are consistently translated
- Evaluation criteria maintain same meaning across languages
- Cultural context is appropriately adapted
- No ambiguity introduced by translation

### 5.3 Data Consistency
**Priority**: High  
**Description**: Bilingual data shall remain consistent with single-language versions.

**Acceptance Criteria**:
- Updates to English templates are reflected in bilingual versions
- Updates to Chinese templates are reflected in bilingual versions
- Version control tracks template changes
- Inconsistencies are detected and reported

## 6. Validation Requirements

### 6.1 Template Validation
**Priority**: High  
**Description**: Template construction shall be validated at build time.

**Acceptance Criteria**:
- Variable consistency check runs during template creation
- Section markers are verified to be present
- Template syntax is validated
- Validation errors prevent template creation

### 6.2 Configuration Validation
**Priority**: High  
**Description**: Configuration values shall be validated at load time.

**Acceptance Criteria**:
- prompt_language value is checked against allowed values
- Missing required fields trigger errors
- Type checking is performed on all fields
- Validation errors include helpful messages

### 6.3 Output Validation
**Priority**: Medium  
**Description**: Evaluation outputs shall be validated for correctness.

**Acceptance Criteria**:
- Score ranges are validated (1-6 for judge, 1-5 for WAI)
- Required fields are present in output
- JSON structure is valid
- Output schema matches expected format

## 7. Deployment Requirements

### 7.1 Installation
**Priority**: Medium  
**Description**: The feature shall be easy to install and enable.

**Acceptance Criteria**:
- No additional installation steps required
- Feature is available after code update
- Configuration change enables bilingual mode
- No database migrations or data updates needed

### 7.2 Migration
**Priority**: Medium  
**Description**: Existing users shall be able to adopt bilingual mode without disruption.

**Acceptance Criteria**:
- Existing configurations continue to work
- Migration guide is provided
- Example configurations demonstrate bilingual setup
- No data loss or corruption during migration

### 7.3 Rollback
**Priority**: Low  
**Description**: Users shall be able to revert to single-language mode easily.

**Acceptance Criteria**:
- Configuration change disables bilingual mode
- No permanent changes to data or state
- Single-language modes remain fully functional
- Rollback is documented

## 8. Constraints

### 8.1 Technical Constraints
- Must use Python 3.8+
- Must work with existing litellm integration
- Must not break existing API contracts
- Must maintain same output schema

### 8.2 Resource Constraints
- Token usage approximately doubles for bilingual mode
- Memory usage increase should be minimal (<200KB)
- No significant CPU overhead beyond LLM API calls

### 8.3 Time Constraints
- Feature should be implementable in existing codebase
- No major refactoring of existing code required
- Testing should be completable within reasonable timeframe

### 8.4 Compatibility Constraints
- Must work with all LLM providers supported by litellm
- Must maintain compatibility with existing evaluation scripts
- Must not require changes to existing data files

## 9. Assumptions

### 9.1 Technical Assumptions
- LLM models can effectively process bilingual prompts
- Token limits are sufficient for bilingual prompts (typically 4000-6000 tokens)
- LLM response quality improves with bilingual prompts for Chinese dialogues
- JSON output format is consistently parseable across prompt types

### 9.2 User Assumptions
- Users have access to configuration files
- Users understand the cost implications of increased token usage
- Users can choose appropriate prompt language for their use case
- Users have Chinese language support in their environment if using bilingual mode

### 9.3 Data Assumptions
- Existing English and Chinese translations are accurate
- Translation quality is sufficient for evaluation purposes
- Conversations are primarily in Chinese when using bilingual mode
- Member details can be represented in both languages

## 10. Success Criteria

### 10.1 Functional Success
- All 8 functional requirements are fully implemented
- All acceptance criteria are met
- Feature works end-to-end for both judge and WAI evaluations
- No regressions in existing functionality

### 10.2 Quality Success
- Test coverage exceeds 90% for new code
- All tests pass consistently
- No critical or high-severity bugs
- Code review approval from maintainers

### 10.3 Performance Success
- Bilingual evaluation completes within acceptable time (< 2x single-language)
- Token usage is predictable and documented
- No memory leaks or resource exhaustion
- Batch processing works efficiently

### 10.4 User Success
- Users can successfully configure and use bilingual mode
- Documentation is clear and complete
- Error messages are helpful and actionable
- Feature provides measurable value (improved evaluation quality)
