"""
WAI (Working Alliance Inventory) Evaluation Module

Based on Li et al. (2024), "Understanding the Therapeutic Relationship between 
Counselors and Clients in Online Text-based Counseling using LLMs"
(Findings of EMNLP 2024, arXiv:2402.11958)
"""

from .wai_evaluator import (
    QUESTIONS,
    DIMENSIONS,
    DETAILED_GUIDELINES,
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_BATCH,
    evaluate_dialogue,
    evaluate_dialogue_batch,
    evaluate_question,
    build_prompt,
    build_prompt_batch,
)

__all__ = [
    "QUESTIONS",
    "DIMENSIONS",
    "DETAILED_GUIDELINES",
    "PROMPT_TEMPLATE",
    "PROMPT_TEMPLATE_BATCH",
    "evaluate_dialogue",
    "evaluate_dialogue_batch",
    "evaluate_question",
    "build_prompt",
    "build_prompt_batch",
]
