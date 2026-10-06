"""
Convert SoulChat corpus to Mind-Eval format.

SoulChat source format:
    [
      {
        "topic": "情感问题",
        "messages": [
          {"role": "用户", "content": "我最近很难过..."},
          {"role": "心理咨询师", "content": "听起来你..."},
          ...
        ]
      },
      ...
    ]

Role mapping:
    用户 (user)        → "client"
    心理咨询师 (counselor) → "counselor"

Usage:
    # Keep Chinese (Option B / C)
    python mindeval/scripts/convert_soulchat.py \
        --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
        --output_path data/SoulChat/test/option_b_interactions_zh.jsonl \
        --max_dialogues 50

    # Translate to English (Option A)
    python mindeval/scripts/convert_soulchat.py \
        --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
        --output_path data/SoulChat/test/option_a_interactions_en.jsonl \
        --translate \
        --translation_method llm \
        --config_path config.json \
        --max_dialogues 50

    # Translate + extract profile
    python mindeval/scripts/convert_soulchat.py \
        --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
        --output_path data/SoulChat/test/option_a_interactions_en.jsonl \
        --translate \
        --extract_profile \
        --config_path config.json \
        --max_dialogues 50
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any

from tqdm import tqdm

from mindeval.utils import save_to_jsonl

# Role mapping from SoulChat to Mind-Eval format.
# Must use "user"/"assistant" so messages_to_convo_str() correctly labels
# member turns as <member> and therapist turns as <therapist> in the judge prompt.
ROLE_MAPPING = {
    "用户": "user",
    "心理咨询师": "assistant",
}

# Default profile for SoulChat dialogues.
# SoulChat does not provide structured demographic information,
# so all fields default to "Unknown" / safe defaults.
DEFAULT_PROFILE = {
    "name": "Anonymous",
    "sex": "Unknown",
    "gender_identity": "Unknown",
    "sexual_orientation": "Unknown",
    "age": 30,
    "race": "Asian",
    "education": "Unknown",
    "profession": "Unknown",
    "employment_status": "Unknown",
    "siblings": "Unknown",
    "relationship_status": "Unknown",
    "living_situation": "Unknown",
    "exercise": "Unknown",
    "sleep_quality": "Unknown",
    "attitude_towards_mindfulness": "Unknown",
    "region": "urban",
    "depressive_symptoms": "Unknown",
    "anxious_symptoms": "Unknown",
}


def convert_dialogue(
    dialogue: Dict,
    dialogue_index: int,
    translate: bool = False,
    translation_method: str = "llm",
    model_api_params: Optional[dict] = None,
    google_credentials_path: Optional[str] = None,
    target_language: str = "en",
    extract_profile: bool = False,
    profile_extraction_params: Optional[dict] = None,
) -> Dict:
    """
    Convert a single SoulChat dialogue entry to Mind-Eval format.

    Args:
        dialogue: One entry from SoulChatCorpus-sft-multi-Turn.json
        dialogue_index: Zero-based index of this dialogue in the source file
        translate: Whether to translate content to target_language
        translation_method: "llm" or "google"
        model_api_params: API params for LLM translation / profile extraction
        google_credentials_path: Path to Google Cloud credentials
        target_language: Target language code (default "en")
        extract_profile: Whether to extract profile from translated dialogue
        profile_extraction_params: API params for profile extraction model

    Returns:
        Dict in Mind-Eval interactions format
    """
    topic = dialogue.get("topic", "Unknown")
    messages = dialogue.get("messages", [])

    # Build interaction turns
    interaction = []
    for turn in messages:
        raw_role = turn.get("role", "")
        content = turn.get("content", "")

        # Map Chinese role labels to "user"/"assistant" for Mind-Eval format
        role = ROLE_MAPPING.get(raw_role, raw_role)

        if translate:
            if translation_method == "llm":
                if not model_api_params:
                    raise ValueError("model_api_params required for LLM translation")
                from mindeval.scripts.convert_simpsydial import (
                    translate_chinese_counseling_to_target_language,
                )
                content = translate_chinese_counseling_to_target_language(
                    source_text=content,
                    speaker_role=role,
                    model_api_params=model_api_params,
                    target_language=target_language,
                )
            elif translation_method == "google":
                from mindeval.scripts.convert_simpsydial import translate_with_google
                content = translate_with_google(content, google_credentials_path)
            else:
                raise ValueError(f"Unknown translation method: {translation_method}")

        interaction.append({"role": role, "content": content})

    # Optionally extract profile from translated dialogue
    if extract_profile and extract_profile and (translate or target_language == "en"):
        from mindeval.scripts.convert_simpsydial import (
            extract_profile_from_english_dialogue,
        )
        params = profile_extraction_params or model_api_params
        if params:
            extracted = extract_profile_from_english_dialogue(interaction, params)
            member_profile = DEFAULT_PROFILE.copy()
            member_profile.update(extracted)
        else:
            member_profile = DEFAULT_PROFILE.copy()
    else:
        member_profile = DEFAULT_PROFILE.copy()

    return {
        "member_profile": member_profile,
        "interaction": interaction,
        "metadata": {
            "source": "SoulChat",
            "dialogue_index": dialogue_index,
            "topic": topic,
            "language": target_language if translate else "zh",
            "translated": translate,
            "translation_method": translation_method if translate else None,
            "profile_extracted": extract_profile and translate,
        },
    }


def main(
    input_path: str,
    output_path: str,
    translate: bool = False,
    translation_method: str = "llm",
    model_api_params: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    google_credentials_path: Optional[str] = None,
    max_dialogues: Optional[int] = None,
    target_language: str = "en",
    extract_profile: bool = False,
    profile_extraction_params: Optional[Dict[str, Any]] = None,
    skip_existing: bool = True,
    random_sample: bool = False,
    random_seed: int = 42,
):
    """
    Convert SoulChat corpus entries to Mind-Eval format.

    Args:
        input_path: Path to SoulChatCorpus-sft-multi-Turn.json
        output_path: Output path for converted JSONL file
        translate: Whether to translate dialogues to target_language
        translation_method: "llm" or "google"
        model_api_params: API params for LLM (overridden by config_path if provided)
        config_path: Path to config.json (uses judge config for translation)
        google_credentials_path: Path to Google Cloud credentials
        max_dialogues: Maximum number of dialogues to include in output
        target_language: Target language code (default "en")
        extract_profile: Whether to extract profile from translated dialogue
        profile_extraction_params: API params for profile extraction (defaults to model_api_params)
        skip_existing: Skip dialogues already present in the output file (default True)
        random_sample: If True, randomly sample from the dataset instead of taking the first N
        random_seed: Random seed for reproducible sampling
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    # Load model config if config_path provided
    if config_path and not model_api_params:
        from mindeval.config import get_translation_config
        model_api_params = get_translation_config(config_path)

    # Load existing converted dialogues for caching
    existing_converted = []
    existing_indices: set = set()

    if skip_existing and output_file.exists():
        print(f"Loading existing conversions from {output_path}...")
        try:
            from mindeval.utils import load_jsonl
            existing_converted = load_jsonl(output_path)
            for item in existing_converted:
                if "metadata" in item and "dialogue_index" in item["metadata"]:
                    existing_indices.add(item["metadata"]["dialogue_index"])
            print(f"Found {len(existing_indices)} already converted dialogues")
        except Exception as e:
            print(f"Warning: Could not load existing file: {e}")
            existing_converted = []
            existing_indices = set()

    # Load source data
    print(f"Loading SoulChat data from {input_path}...")
    with open(input_file, "r", encoding="utf-8") as f:
        all_dialogues = json.load(f)

    print(f"Total dialogues in source: {len(all_dialogues)}")

    # Build index list to process
    all_indices = list(range(len(all_dialogues)))

    if random_sample:
        random.seed(random_seed)
        random.shuffle(all_indices)

    # Apply max_dialogues limit to total output size
    if max_dialogues:
        all_indices = all_indices[:max_dialogues]

    # Filter out already converted indices
    if skip_existing and existing_indices:
        original_count = len(all_indices)
        all_indices = [i for i in all_indices if i not in existing_indices]
        skipped = original_count - len(all_indices)
        if skipped > 0:
            print(f"Skipping {skipped} already converted dialogues")

    print(f"Dialogues to convert: {len(all_indices)}")

    if not all_indices:
        print("No new dialogues to convert. All already processed.")
        return

    if translate:
        print(f"Translation enabled: {translation_method} → {target_language}")
        if model_api_params:
            print(f"  Model: {model_api_params.get('model', 'unknown')}")

    converted = []
    errors = []

    for idx in tqdm(all_indices, desc="Converting SoulChat dialogues"):
        try:
            result = convert_dialogue(
                dialogue=all_dialogues[idx],
                dialogue_index=idx,
                translate=translate,
                translation_method=translation_method,
                model_api_params=model_api_params,
                google_credentials_path=google_credentials_path,
                target_language=target_language,
                extract_profile=extract_profile,
                profile_extraction_params=profile_extraction_params or model_api_params,
            )
            converted.append(result)
        except Exception as e:
            error_msg = f"Error converting dialogue {idx}: {str(e)}"
            print(f"\n{error_msg}")
            errors.append({"dialogue_index": idx, "error": str(e)})

    # Merge with existing and save
    all_converted = existing_converted + converted
    output_file.parent.mkdir(parents=True, exist_ok=True)
    save_to_jsonl(all_converted, output_path)

    print(f"\n✓ Successfully converted {len(converted)} new dialogues")
    if existing_converted:
        print(f"✓ Total in output: {len(all_converted)} ({len(existing_converted)} existing + {len(converted)} new)")
    print(f"✓ Saved to: {output_path}")

    if errors:
        error_path = str(output_file).replace(".jsonl", "_errors.json")
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
        print(f"⚠ {len(errors)} errors occurred. See: {error_path}")

    print("\n=== Conversion Summary ===")
    print(f"Source dialogues: {len(all_dialogues)}")
    print(f"Requested (max_dialogues): {max_dialogues or 'all'}")
    if skip_existing and existing_indices:
        print(f"Already converted (skipped): {len(existing_indices)}")
    print(f"Newly converted: {len(converted)}")
    print(f"Failed: {len(errors)}")
    print(f"Total in output: {len(all_converted)}")
    print(f"Translation: {'Yes (' + translation_method + ' → ' + target_language + ')' if translate else 'No'}")
    print(f"Profile extraction: {'Yes' if extract_profile and translate else 'No'}")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([main], as_positional=False)
