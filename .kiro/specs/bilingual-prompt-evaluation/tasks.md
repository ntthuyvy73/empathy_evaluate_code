# Implementation Tasks: Bilingual Prompt Evaluation

## Phase 1: Core Infrastructure

### 1.1 Create Bilingual Judge Prompt Module
**Priority**: High  
**Estimated Effort**: 4 hours  
**Dependencies**: None

**Tasks**:
- [ ] Create `mindeval/judge_prompts_bilingual.py` file
- [ ] Import English template from `judge_prompts.py`
- [ ] Import Chinese template from `judge_prompts_zh.py`
- [ ] Implement `build_bilingual_prompt()` function to combine templates
- [ ] Create `JUDGE_PROMPT_TEMPLATE_BILINGUAL` constant
- [ ] Add section markers ("## English Rubric", "## 中文翻译")
- [ ] Add docstrings and type hints
- [ ] Verify all template variables are consistent between EN/ZH

**Acceptance Criteria**:
- Module imports successfully
- Template contains both EN and ZH sections
- All template variables from original templates are preserved
- Section separators are properly inserted

### 1.2 Create Bilingual WAI Prompt Module
**Priority**: High  
**Estimated Effort**: 6 hours  
**Dependencies**: None

**Tasks**:
- [ ] Create `mindeval/wai/wai_prompts_bilingual.py` file
- [ ] Import questions from `wai_evaluator.py` and `wai_prompts_zh.py`
- [ ] Create `QUESTIONS_BILINGUAL` dict with EN/ZH for Q1-Q12
- [ ] Create `DETAILED_GUIDELINES_BILINGUAL` dict with EN/ZH for Q1-Q12
- [ ] Implement `build_prompt_bilingual(qid, conversation)` function
- [ ] Create `PROMPT_TEMPLATE_BILINGUAL` string
- [ ] Add section markers for bilingual content
- [ ] Add docstrings and type hints
- [ ] Verify all 12 questions have complete bilingual versions

**Acceptance Criteria**:
- Module imports successfully
- All 12 WAI questions have bilingual versions
- `build_prompt_bilingual()` generates valid prompts
- CoT structure is preserved
- JSON output format instructions are bilingual

### 1.3 Extend Configuration Module
**Priority**: High  
**Estimated Effort**: 3 hours  
**Dependencies**: None

**Tasks**:
- [ ] Add `PromptLanguage` enum to `mindeval/config.py` (or create if doesn't exist)
- [ ] Define enum values: EN = "en", ZH = "zh", BILINGUAL = "bilingual"
- [ ] Implement `get_prompt_language(config)` function
- [ ] Add default value handling (default to "en")
- [ ] Add validation for prompt_language field
- [ ] Add type hints and docstrings
- [ ] Update `config.example.json` with prompt_language field

**Acceptance Criteria**:
- Enum is properly defined
- Function parses configuration correctly
- Invalid values raise ValueError
- Default value is "en"
- Example configuration is updated

### 1.4 Implement Prompt Selection Logic
**Priority**: High  
**Estimated Effort**: 4 hours  
**Dependencies**: 1.1, 1.2, 1.3

**Tasks**:
- [ ] Add `select_judge_prompt(prompt_language)` function to `mindeval/inference.py`
- [ ] Add `select_wai_prompt_builder(prompt_language)` function
- [ ] Implement conditional imports for bilingual modules
- [ ] Add error handling for missing modules
- [ ] Implement fallback to single-language mode
- [ ] Add logging for prompt selection
- [ ] Add type hints and docstrings

**Acceptance Criteria**:
- Function routes to correct template based on language
- Bilingual mode loads bilingual modules
- Single-language modes work unchanged
- Missing modules trigger appropriate fallback
- Clear error messages for failures

## Phase 2: Integration

### 2.1 Integrate with InferenceEngine
**Priority**: High  
**Estimated Effort**: 2 hours  
**Dependencies**: 1.1, 1.4

**Tasks**:
- [ ] Update `InferenceEngine` to accept prompt_language parameter (if needed)
- [ ] Verify `generate()` works with bilingual prompts
- [ ] Verify `batch_generate()` works with bilingual prompts
- [ ] Test token counting with bilingual prompts
- [ ] Verify response parsing handles bilingual outputs

**Acceptance Criteria**:
- InferenceEngine processes bilingual prompts correctly
- Token usage is tracked accurately
- Response parsing works for all prompt types
- No breaking changes to existing API

### 2.2 Integrate with WAI Evaluator
**Priority**: High  
**Estimated Effort**: 3 hours  
**Dependencies**: 1.2, 1.4

**Tasks**:
- [ ] Update `wai_evaluator.py` to support language parameter
- [ ] Modify `build_prompt()` to accept and use language parameter
- [ ] Update prompt builder selection logic
- [ ] Verify all 12 questions work in bilingual mode
- [ ] Test dimension score calculations with bilingual prompts
- [ ] Verify output format matches existing WAI results

**Acceptance Criteria**:
- WAI evaluator supports bilingual mode
- All 12 questions process correctly
- Dimension scores are calculated correctly
- Output format is consistent
- Backward compatibility maintained

### 2.3 Update Evaluation Scripts
**Priority**: Medium  
**Estimated Effort**: 3 hours  
**Dependencies**: 2.1, 2.2

**Tasks**:
- [ ] Update `generate_judgments.py` to support prompt_language config
- [ ] Update `generate_wai_judgments.py` to support prompt_language config
- [ ] Add command-line argument for prompt language (optional)
- [ ] Update script documentation
- [ ] Test scripts with all three language modes

**Acceptance Criteria**:
- Scripts read prompt_language from config
- Scripts work with all language modes
- Command-line override works (if implemented)
- Backward compatibility maintained
- Documentation is updated

## Phase 3: Validation & Testing

### 3.1 Unit Tests for Bilingual Judge Prompts
**Priority**: High  
**Estimated Effort**: 4 hours  
**Dependencies**: 1.1

**Tasks**:
- [ ] Create `tests/test_judge_prompts_bilingual.py`
- [ ] Test template construction with valid EN/ZH templates
- [ ] Test variable extraction and consistency checking
- [ ] Test section separator insertion
- [ ] Test label formatting
- [ ] Test error handling for missing variables
- [ ] Test error handling for variable mismatches
- [ ] Verify 90%+ code coverage

**Acceptance Criteria**:
- All tests pass
- Code coverage exceeds 90%
- Edge cases are covered
- Error conditions are tested

### 3.2 Unit Tests for Bilingual WAI Prompts
**Priority**: High  
**Estimated Effort**: 5 hours  
**Dependencies**: 1.2

**Tasks**:
- [ ] Create `tests/test_wai_prompts_bilingual.py`
- [ ] Test `build_prompt_bilingual()` for all Q1-Q12
- [ ] Test question and guideline formatting
- [ ] Test JSON output format instructions
- [ ] Test conversation embedding
- [ ] Test error handling for invalid qid
- [ ] Test Unicode and special character handling
- [ ] Verify 90%+ code coverage

**Acceptance Criteria**:
- All tests pass
- All 12 questions are tested
- Code coverage exceeds 90%
- Edge cases are covered

### 3.3 Unit Tests for Configuration
**Priority**: High  
**Estimated Effort**: 2 hours  
**Dependencies**: 1.3

**Tasks**:
- [ ] Create `tests/test_config_bilingual.py`
- [ ] Test `get_prompt_language()` with various configs
- [ ] Test default value handling
- [ ] Test invalid configuration handling
- [ ] Test enum validation
- [ ] Test missing field handling

**Acceptance Criteria**:
- All tests pass
- All enum values are tested
- Error conditions are tested
- Default behavior is verified

### 3.4 Unit Tests for Prompt Selection
**Priority**: High  
**Estimated Effort**: 3 hours  
**Dependencies**: 1.4

**Tasks**:
- [ ] Create `tests/test_prompt_selection.py`
- [ ] Test `select_judge_prompt()` for all language options
- [ ] Test `select_wai_prompt_builder()` routing
- [ ] Test module import handling
- [ ] Test fallback behavior
- [ ] Test error messages
- [ ] Test backward compatibility

**Acceptance Criteria**:
- All tests pass
- All language modes are tested
- Fallback behavior is verified
- Error handling is tested

### 3.5 Integration Tests
**Priority**: High  
**Estimated Effort**: 6 hours  
**Dependencies**: 2.1, 2.2, 2.3

**Tasks**:
- [ ] Create `tests/test_bilingual_integration.py`
- [ ] Test end-to-end bilingual judge evaluation
- [ ] Test end-to-end bilingual WAI evaluation
- [ ] Test configuration loading and prompt selection
- [ ] Test with mock LLM responses
- [ ] Test batch processing
- [ ] Test error propagation
- [ ] Test switching between language modes

**Acceptance Criteria**:
- All integration tests pass
- End-to-end workflows work correctly
- Mock LLM integration works
- All language modes are tested

### 3.6 Property-Based Tests
**Priority**: Medium  
**Estimated Effort**: 4 hours  
**Dependencies**: 1.1, 1.2

**Tasks**:
- [ ] Install hypothesis library (if not already present)
- [ ] Create `tests/test_bilingual_properties.py`
- [ ] Implement template variable consistency property test
- [ ] Implement content preservation property test
- [ ] Implement substitution completeness property test
- [ ] Implement section separation property test
- [ ] Run property tests with multiple random inputs

**Acceptance Criteria**:
- Property tests pass with 100+ random examples
- All correctness properties are verified
- No counterexamples found

## Phase 4: Documentation & Polish

### 4.1 Code Documentation
**Priority**: Medium  
**Estimated Effort**: 3 hours  
**Dependencies**: 1.1, 1.2, 1.3, 1.4

**Tasks**:
- [ ] Add comprehensive docstrings to all new functions
- [ ] Add module-level docstrings
- [ ] Add inline comments for complex logic
- [ ] Add type hints to all function signatures
- [ ] Generate API documentation (if applicable)

**Acceptance Criteria**:
- All public functions have docstrings
- Docstrings follow project conventions
- Type hints are complete and accurate
- Code is well-commented

### 4.2 User Documentation
**Priority**: Medium  
**Estimated Effort**: 4 hours  
**Dependencies**: All previous tasks

**Tasks**:
- [ ] Update README.md with bilingual mode section
- [ ] Create usage examples for bilingual mode
- [ ] Document configuration options
- [ ] Document cost implications (token usage)
- [ ] Create migration guide for existing users
- [ ] Add troubleshooting section
- [ ] Update CHANGES-SUMMARY.md or similar

**Acceptance Criteria**:
- README includes bilingual mode documentation
- Usage examples are clear and complete
- Configuration is well-documented
- Cost implications are explained
- Migration guide is provided

### 4.3 Configuration Examples
**Priority**: Low  
**Estimated Effort**: 1 hour  
**Dependencies**: 1.3

**Tasks**:
- [ ] Update `config.example.json` with bilingual examples
- [ ] Create separate example config for bilingual mode
- [ ] Add comments explaining each option
- [ ] Provide examples for judge and WAI configurations

**Acceptance Criteria**:
- Example configurations are valid
- All options are documented
- Comments are clear and helpful

### 4.4 Code Quality & Linting
**Priority**: Medium  
**Estimated Effort**: 2 hours  
**Dependencies**: All code tasks

**Tasks**:
- [ ] Run linter on all new code
- [ ] Fix any linting errors or warnings
- [ ] Ensure consistent code style
- [ ] Remove any code duplication
- [ ] Optimize imports
- [ ] Run type checker (mypy or similar)

**Acceptance Criteria**:
- No linting errors
- Code style is consistent
- Type checking passes
- No unnecessary code duplication

## Phase 5: Validation & Deployment

### 5.1 Manual Testing
**Priority**: High  
**Estimated Effort**: 4 hours  
**Dependencies**: All previous tasks

**Tasks**:
- [ ] Test bilingual judge evaluation with real conversation
- [ ] Test bilingual WAI evaluation with real conversation
- [ ] Test configuration switching between modes
- [ ] Test error scenarios manually
- [ ] Verify output format and scores
- [ ] Test with different LLM models (if available)
- [ ] Compare results with single-language modes

**Acceptance Criteria**:
- Manual tests complete successfully
- Output format is correct
- Scores are reasonable
- No unexpected errors
- Results are comparable to single-language modes

### 5.2 Performance Testing
**Priority**: Medium  
**Estimated Effort**: 3 hours  
**Dependencies**: 5.1

**Tasks**:
- [ ] Measure token usage for bilingual prompts
- [ ] Measure response time for bilingual evaluations
- [ ] Compare with single-language performance
- [ ] Test batch processing performance
- [ ] Measure memory usage
- [ ] Document performance characteristics

**Acceptance Criteria**:
- Token usage is documented
- Response time is acceptable (< 2x single-language)
- Memory usage is reasonable (< 200KB increase)
- Performance metrics are documented

### 5.3 Backward Compatibility Testing
**Priority**: Critical  
**Estimated Effort**: 3 hours  
**Dependencies**: All previous tasks

**Tasks**:
- [ ] Run all existing tests with new code
- [ ] Verify existing configurations still work
- [ ] Test existing scripts without modification
- [ ] Verify output format hasn't changed for existing modes
- [ ] Test with configurations missing prompt_language field
- [ ] Verify no breaking API changes

**Acceptance Criteria**:
- All existing tests pass
- Existing configurations work unchanged
- No breaking changes detected
- Default behavior is preserved

### 5.4 Final Review & Cleanup
**Priority**: Medium  
**Estimated Effort**: 2 hours  
**Dependencies**: All previous tasks

**Tasks**:
- [ ] Review all code changes
- [ ] Remove any debug code or comments
- [ ] Verify all TODOs are addressed
- [ ] Check for any hardcoded values
- [ ] Verify error messages are helpful
- [ ] Final code review with team (if applicable)

**Acceptance Criteria**:
- Code is clean and production-ready
- No debug code remains
- All TODOs are resolved
- Code review is approved

### 5.5 Deployment Preparation
**Priority**: Low  
**Estimated Effort**: 2 hours  
**Dependencies**: 5.4

**Tasks**:
- [ ] Create deployment checklist
- [ ] Update version number (if applicable)
- [ ] Create release notes
- [ ] Tag release in version control
- [ ] Prepare rollback plan
- [ ] Notify users of new feature (if applicable)

**Acceptance Criteria**:
- Deployment checklist is complete
- Release notes are clear
- Version is tagged
- Rollback plan is documented

## Summary

**Total Estimated Effort**: ~70 hours

**Phase Breakdown**:
- Phase 1 (Core Infrastructure): ~17 hours
- Phase 2 (Integration): ~8 hours
- Phase 3 (Validation & Testing): ~24 hours
- Phase 4 (Documentation & Polish): ~10 hours
- Phase 5 (Validation & Deployment): ~14 hours

**Critical Path**:
1. Create bilingual prompt modules (1.1, 1.2)
2. Extend configuration (1.3)
3. Implement prompt selection (1.4)
4. Integrate with InferenceEngine and WAI (2.1, 2.2)
5. Complete testing (3.1-3.5)
6. Validate backward compatibility (5.3)

**Risk Areas**:
- Template variable consistency between EN/ZH versions
- Token limit issues with bilingual prompts
- LLM response quality with bilingual prompts
- Backward compatibility with existing configurations

**Success Metrics**:
- All tests pass (unit, integration, property-based)
- Code coverage > 90%
- No regressions in existing functionality
- Documentation is complete and clear
- Feature provides measurable value (improved evaluation quality for Chinese dialogues)
