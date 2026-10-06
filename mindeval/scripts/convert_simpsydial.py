"""
Convert SimPsyDial dialogues to Mind-Eval format.

This script converts SimPsyDial Chinese counseling dialogues to the format
required by Mind-Eval evaluation framework.

Usage:
    # Basic conversion (keep Chinese)
    python mindeval/scripts/convert_simpsydial.py \
        --input_dir data/simpsydial/raw \
        --output_path data/simpsydial/converted/interactions_zh.jsonl

    # With translation using GPT-4
    python mindeval/scripts/convert_simpsydial.py \
        --input_dir data/simpsydial/raw \
        --output_path data/simpsydial/converted/interactions_en_gpt4.jsonl \
        --translate \
        --translation_method gpt4 \
        --model_api_params "{'model':'gpt-4','api_key':'YOUR_KEY'}"

    # With translation using Google Translate
    python mindeval/scripts/convert_simpsydial.py \
        --input_dir data/simpsydial/raw \
        --output_path data/simpsydial/converted/interactions_en_google.jsonl \
        --translate \
        --translation_method google \
        --google_credentials_path path/to/credentials.json
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from tqdm import tqdm

from mindeval.utils import save_to_jsonl

# Default profile template for SimPsyDial dialogues
# Since SimPsyDial doesn't provide structured profile information,
# we use default values with "Unknown" for missing fields
DEFAULT_PROFILE = {
    "name": "Anonymous",
    "sex": "Unknown",
    "gender_identity": "Unknown",
    "sexual_orientation": "Unknown",
    "age": 30,  # Default adult age
    "race": "Asian",  # Assume Chinese dataset
    "education": "Unknown",
    "profession": "Unknown",
    "employment_status": "Unknown",
    "siblings": "Unknown",
    "relationship_status": "Unknown",
    "living_situation": "Unknown",
    "exercise": "Unknown",
    "sleep_quality": "Unknown",
    "attitude_towards_mindfulness": "Unknown",
    "region": "urban",  # Default assumption
    "depressive_symptoms": "Unknown",
    "anxious_symptoms": "Unknown"
}

# Role mapping from SimPsyDial to Mind-Eval format.
# Must use "user"/"assistant" so messages_to_convo_str() correctly labels
# member turns as <member> and therapist turns as <therapist> in the judge prompt.
ROLE_MAPPING = {
    "client": "user",
    "counselor": "assistant",
}

def format_client_only_for_profile_extraction(dialogue):
    lines = []
    for i, turn in enumerate(dialogue, start=1):
        if turn["role"] in ("client", "user"):
            lines.append(f"[Client Turn {i}]\n{turn['content']}")
    return "\n\n".join(lines)

def extract_profile_from_english_dialogue(
    dialogue: List[Dict[str, str]],
    model_api_params: dict
) -> Dict[str, Any]:
    """
    Extract member profile attributes from English counseling dialogue using LLM.
    
    Only extracts attributes that can be confidently determined from the dialogue.
    Uncertain attributes are set to "Unknown".
    
    Args:
        dialogue: List of dialogue turns with "role" and "content" (already translated to English)
        model_api_params: API parameters for the extraction model
        
    Returns:
        Dict with extracted profile attributes
    """
    from mindeval.inference import InferenceEngine
    from mindeval.variables import SLEEP_QUALITY, ATTITUDE_TOWARDS_MINDFULNESS
    
    # Format enum values for prompt
    sleep_quality_enum_values = "\n".join([f'  - "{opt}"' for opt in SLEEP_QUALITY])
    mindfulness_enum_values = "\n".join([f'  - "{opt}"' for opt in ATTITUDE_TOWARDS_MINDFULNESS])
    
    # Convert dialogue to text format
    dialogue_text = format_client_only_for_profile_extraction(dialogue)
    # for turn in dialogue:
    #     # Use English role labels from the original file
    #     role_label = "Client" if turn["role"] == "client" else "Counselor"
    #     dialogue_text += f"{role_label}: {turn['content']}\n\n"
    
    prompt = f"""Extract a structured CLIENT profile from an English mental health counseling dialogue for the mind-eval member_profile schema.

The fields name, race, and region are assigned by the system outside this prompt.
Do NOT extract or output name, race, or region.

INPUT FORMAT
The dialogue contains role-tagged turns:
[Turn <number> | client]
<utterance>

[Turn <number> | counselor]
<utterance>

Use counselor turns only for context.
Extract information ONLY from client turns.
If a fact appears only in a counselor turn and is not stated or confirmed by the client, treat it as "Unknown".

CORE RULES

1. CLIENT ONLY
Extract only information about the client.
Ignore information about boyfriend/girlfriend, spouse, parents, in-laws, friends, coworkers, or counselor.

Example:
"My boyfriend's mother has late-stage lung cancer" is about the boyfriend's mother, not the client.
Do not set the client's physical health, depressive symptoms, or anxious symptoms from this.

2. DEFAULT TO UNKNOWN
Use "Unknown" whenever information is absent, vague, uncertain, about someone else, or requires guessing.
Do not fill fields just because they seem likely.

3. NO SENSITIVE INFERENCE
Do NOT infer sex, gender_identity, or sexual_orientation from partner gender or relationship terms such as boyfriend, girlfriend, husband, wife, fiancé, fiancée, mother-in-law, or father-in-law.
Only set these fields if the client explicitly self-identifies.
Otherwise use "Unknown".

Examples:
- "I have a boyfriend" → relationship_status may be extracted, but sex, gender_identity, and sexual_orientation must remain "Unknown".
- "I am gay" → sexual_orientation may be extracted.
- "As a woman..." → sex/gender may be extracted if clearly self-referential.

4. SITUATIONAL DISTRESS IS NOT CLINICAL SYMPTOMS
Do NOT mark depressive_symptoms or anxious_symptoms from ordinary life stress, worry, pressure, mixed feelings, or family/relationship conflict.

Examples that should remain Unknown:
- "I've been under a lot of pressure lately."
- "My feelings are complicated."
- "I'm worried about how they will react."
- "I'm stressed about the wedding, family, or money."

Only assign depressive/anxious symptoms if the client describes their OWN clinically relevant symptoms, such as persistent low mood, loss of interest, inability to function, panic attacks, uncontrollable worry, diagnosis, hospitalization, suicidal ideation, or symptoms with clear duration and daily impairment.

5. SEVERITY
Use severity only with clear evidence:
- severe: diagnosis with severe impairment, hospitalization, suicidal ideation, inability to function, panic attacks with major impairment.
- moderate: persistent symptoms over time with clear daily impact.
- mild: occasional symptoms with low daily impact.
- minimal to no: only if the client explicitly denies symptoms.
- Unknown: not discussed, vague, situational, or insufficient evidence.

6. SLEEP / MINDFULNESS
Only assign sleep_quality or attitude_towards_mindfulness if the client clearly provides enough detail.
If not enough detail, return "Unknown".

TARGET JSON SCHEMA
Return exactly this JSON structure:

{{
  "sex": "Male" | "Female" | "Unknown",
  "gender_identity": "Male" | "Female" | "Non-binary" | "Unknown",
  "sexual_orientation": "Heterosexual / Straight" | "Homosexual" | "Bisexual" | "Queer" | "Questioning / Unsure" | "Unknown",
  "age": <integer> | "Unknown",
  "education": "high school dropout, later got GED" | "high school graduate" | "trade school or community college graduate" | "bachelor's degree" | "master's degree" | "PhD or doctorate" | "professional degree (JD/MD/etc)" | "Unknown",
  "profession": "<specific job title in English>" | "Unknown",
  "employment_status": "employed full time" | "employed part time" | "working variable hours" | "working as stay-at-home parent" | "unemployed" | "student" | "retired" | "Unknown",
  "siblings": "none" | "<specific description>" | "Unknown",
  "relationship_status": "single" | "dating multiple people" | "in a relationship" | "in a long-term relationship, not married" | "married" | "divorced" | "widowed" | "Unknown",
  "living_situation": "alone" | "alone with a cat" | "with partner" | "with partner and pet" | "with family" | "with their child" | "with adult children who moved back" | "with roommates" | "Unknown",
  "exercise": "very active" | "quite active, exercise is part of routine" | "moderately active, regular but not intense" | "inconsistently active, goes through phases" | "somewhat active" | "hardly ever" | "Unknown",
  "sleep_quality": "<specific description>" | "Unknown",
  "attitude_towards_mindfulness": "<specific description>" | "Unknown",
  "depressive_symptoms": "severe depressive symptoms" | "moderate depressive symptoms" | "mild depressive symptoms" | "minimal to no depressive symptoms" | "Unknown",
  "anxious_symptoms": "severe anxious symptoms" | "moderate anxious symptoms" | "mild anxious symptoms" | "minimal to no anxious symptoms" | "Unknown"
}}

FIELD CUES
Use these as cues, not automatic mappings:

- age: only explicit numeric age.
- education: high school, college, undergraduate, bachelor's, master's, PhD, doctorate, professional degree.
- profession: explicit job title only.
- employment_status: full-time, part-time, unemployed, retired, student, stay-at-home parent, variable hours.
- siblings: brother, sister, only child.
- relationship_status:
  single → "single"
  boyfriend/girlfriend/partner/dating → "in a relationship"
  together for over a year / long-term partner and not married → "in a long-term relationship, not married"
  husband/wife/spouse/married → "married"
  divorced → "divorced"
  widowed → "widowed"
- living_situation:
  living alone → "alone"
  living with parents/family → "with family"
  living with partner → "with partner"
  living with roommates → "with roommates"
  living with child/children → "with their child"

Important:
Relationship status must NOT be used to infer sex, gender_identity, or sexual_orientation.

DIALOGUE
{dialogue_text}

OUTPUT
Return STRICT JSON only.
No preamble, no markdown fences, no explanations.
Do not include extra fields.
"""
    
    model = InferenceEngine(model_api_params)
    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = model.generate(messages)
        # Clean response (remove markdown code blocks if present)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON response
        extracted = json.loads(response)
        return extracted
    except (json.JSONDecodeError, Exception) as e:
        print(f"Warning: Profile extraction failed: {e}")
        print(f"Response was: {response[:200] if 'response' in locals() else 'No response'}")
        # Return all Unknown if extraction fails
        return {
            "sex": "Unknown",
            "gender_identity": "Unknown",
            "sexual_orientation": "Unknown",
            "age": "Unknown",
            "education": "Unknown",
            "profession": "Unknown",
            "employment_status": "Unknown",
            "siblings": "Unknown",
            "relationship_status": "Unknown",
            "living_situation": "Unknown",
            "exercise": "Unknown",
            "sleep_quality": "Unknown",
            "attitude_towards_mindfulness": "Unknown",
            "depressive_symptoms": "Unknown",
            "anxious_symptoms": "Unknown"
        }


def translate_chinese_counseling_to_target_language(
    source_text: str,
    speaker_role: str,
    model_api_params: dict,
    target_language: str = "en"
) -> str:
    """
    Translate Chinese counseling dialogue text to target language using LLM.
    
    This function is specifically designed for mental health counseling dialogues,
    preserving therapeutic tone and cultural context.
    
    Args:
        source_text: Chinese text to translate
        speaker_role: Role of the speaker ("client" or "counselor")
        model_api_params: API parameters for the model
        target_language: Target language code (default: "en" for English)
        
    Returns:
        Translated text in target language
    """
    from mindeval.inference import InferenceEngine

    # Normalize internal role names to descriptive labels used in the prompt
    role_display = {"user": "client", "assistant": "counselor"}.get(speaker_role, speaker_role)

    # Language names mapping
    language_names = {
        "vi": "Vietnamese",
        "en": "English",
        "zh": "Chinese",
        "ko": "Korean",
        "ja": "Japanese"
    }
    
    target_lang_name = language_names.get(target_language, target_language)
    
    prompt = f"""You are an expert translator specializing in mental health counseling dialogue and Chinese-to-English translation. You have deep knowledge of clinical psychology language, counseling communication, and Chinese cultural contexts such as family dynamics, filial piety/孝, face/面子, collectivist values, marriage customs, intergenerational expectations, education pressure, and workplace hierarchy.

TASK
Translate the following Chinese text from a mental health counseling conversation into natural, fluent English.

This is a SINGLE turn of conversation content only.

Speaker role: {role_display}

You will receive only the spoken content. Translate the content only. Do NOT translate or output the speaker role.

SOURCE TEXT:
{source_text}

TRANSLATION PRINCIPLES

1. Role-aware therapeutic fidelity
   - If speaker_role is "counselor":
     Preserve a warm, calm, professional, empathetic, non-judgmental counseling tone.
     Preserve reflective listening, validation, open-ended questions, gentle guidance, and therapeutic framing when present.
     Do not make the counselor sound more clinical, more directive, more judgmental, more emotional, or more verbose than the original.

   - If speaker_role is "client":
     Preserve the client’s emotional texture, including hesitation, distress, ambivalence, uncertainty, confusion, relief, frustration, or mixed feelings.
     Do not make the client sound more polished, more rational, more dramatic, more fluent, or more self-aware than the original.
     Preserve informal, fragmented, or emotionally hesitant speech when present, while still making the English natural.

2. Semantic accuracy
   - Translate meaning, not isolated words.
   - Avoid word-for-word translation when it sounds unnatural in English.
   - Do NOT omit, summarize, embellish, explain, or infer details.
   - Every meaningful clause in the source must be reflected in the output.
   - Preserve hedges, fillers, and discourse markers such as 嗯, 其实, 可能, 就是, 好像, 我觉得, 说实话 with natural English equivalents when they carry emotional or conversational meaning.
   - Preserve uncertainty and ambiguity. Do not make vague terms more specific than the source.
   - Do not add information that is not explicitly present in the Chinese source.

3. Natural dialogue style
   - This is a dialogue dataset. The translation must sound like real people talking, not like academic writing, a dictionary entry, or translator notes.
   - Use simple, natural, conversational English.
   - Avoid rare, literary, overly formal, overly idiomatic, or overly polished English.
   - Avoid explanatory parentheses, footnote-like glosses, or definitions inside the speaker’s turn.
   - If a culturally specific concept appears, choose a concise natural English equivalent that preserves the meaning without adding an explanation.
   - Do not westernize culturally specific concepts.

4. Cultural preservation without over-explanation
   - Preserve culturally important meanings, but do not over-explain them.
   - Do not insert pinyin terms unless the source itself uses pinyin or the term is being discussed as a term.
   - For kinship terms, preserve the specific relationship when it matters.
   - For general terms, avoid adding specificity not present in the source.
   - For idioms, proverbs, and 成语, translate the intended meaning naturally. Preserve the image only if it remains natural and relevant in English.

5. Mental health terminology
   - Use standard English for clinical terms when the source is clinical.
   - Distinguish colloquial emotional language from diagnostic language.
   - Do not turn ordinary sadness, worry, pressure, or stress into a clinical diagnosis unless the Chinese source clearly does so.

Examples:
   - 抑郁 → “depression” when clinical; “feeling down” when colloquial.
   - 焦虑 → “anxiety” when clinical; “anxious” / “worried” when colloquial.
   - 强迫 → “obsessive-compulsive” when clinical.
   - 创伤 → “trauma”.
   - 认知行为疗法 → “cognitive behavioral therapy (CBT)”.

6. Output discipline
   - Output ONLY the translated content.
   - Do NOT output explanations, notes, alternatives, markdown, quotation marks, or JSON.
   - Do NOT add speaker labels such as “Client:”, “Counselor:”, “User:”, or “Assistant:”.
   - Do NOT add prefixes or labels of any kind.
   - Keep paragraph breaks and punctuation rhythm close to the source while making the English natural.
   - Do not add parenthetical explanations unless the parentheses are present in the original source.

TERMINOLOGY AND STYLE GUIDE

Marriage & family customs:
   - 彩礼 → “betrothal gift” / “betrothal gift money” / “traditional marriage gift money”
     Avoid “bride price” unless the context clearly requires a literal anthropological term.
     Do not add pinyin or parenthetical explanations.

   - 嫁妆 → “dowry”

   - 提前结婚 → “get married earlier”
     Use “move the wedding up” only if the context clearly refers to an already scheduled wedding date.

   - 冲喜 → translate naturally according to context, such as “bring the wedding forward because of the family situation”.
     Do not add a long cultural explanation.

   - 相亲 → “arranged date” / “matchmaking date” / “matchmaking meeting”, depending on context.

   - 婆婆 → “mother-in-law” when the marriage relationship is established; otherwise “his mother”, “my boyfriend’s mother”, or “my partner’s mother”, depending on context.

   - 公公 → “father-in-law” when the marriage relationship is established; otherwise “his father”, “my boyfriend’s father”, or “my partner’s father”, depending on context.

   - 月子 → “postpartum confinement” / “the month of rest after giving birth”, depending on context.

Cultural concepts:
   - 孝 / 孝顺 → “filial duty” / “being filial” / “doing right by my parents”, depending on tone.
     Do not flatten it into “being a good child” if the cultural meaning matters.

   - 面子 → “face” / “saving face” / “losing face”

   - 内卷 → “relentless competition” / “rat race”

   - 躺平 → “opting out” / “checking out of the rat race”

   - 啃老 → “living off my parents”

   - 高考 → “the college entrance exam”

Counseling-specific expressions:
   - 共情 → “empathy”
     Do not translate it as “sympathy” unless the context clearly means sympathy.

   - 来访者 / 求助者 → “client” only when referring to the role, not as an inserted speaker label.

   - 咨询师 → “counselor” only when referring to the role, not as an inserted speaker label.

   - 你觉得愿意…吗 / 你觉得可以…吗:
     Prefer natural open-ended counseling questions such as:
     “How would you feel about…?”
     “What do you think about…?”
     “Would you feel comfortable…?”
     Choose based on context.

   - 有需要随时来找我 / 再来找我聊聊:
     “feel free to come back and talk with me anytime”
     “you can come back and talk with me anytime”

   - 加油:
     “You’ve got this”
     “Hang in there”
     “I’m rooting for you”
     Choose based on emotional tone.
     Avoid “Keep it up” unless the context is about continuing an ongoing effort.

Common emotional and conversational expressions:
   - 棘手 → “hard to navigate” / “complicated” / “tricky”, depending on context.
     Avoid “thorny” unless it sounds natural in the surrounding English.

   - 为难 → “torn” / “caught in the middle” / “in a tough spot”

   - 心情复杂 → “my feelings are complicated” / “I have mixed feelings”

   - 力所能及 → “whatever I can” / “as much as I’m able to”

   - 到点就回家 → “head straight home when it’s time” / “go home as soon as we can” / “head straight home”, depending on context.

   - 节省一段时间 → “save money for a while” / “cut back on expenses for a while”

   - 自主 → “more independent” / “more in control”, depending on context.

   - 房子 → “home” / “house”
     Do not translate it as “apartment” unless the source clearly says 公寓, 楼房, or otherwise specifies an apartment.

   - 装修 → “renovation” / “renovate” / “fix up the home”, depending on context.

   - 压力很大 → “under a lot of pressure” / “the pressure is really heavy”

   - 折中 / 折中的办法 → “compromise” / “middle-ground solution” / “workable compromise”

FINAL CHECK BEFORE OUTPUT
Before returning the translation, silently check:
   - Did I preserve the role-specific tone?
   - Did I add any information not in the source?
   - Did I omit any meaningful clause?
   - Did I make a vague term more specific than the original?
   - Did I over-explain a cultural term?
   - Did I insert a speaker label?
   - Is the English natural for a counseling dialogue?
   - Did I preserve the emotional tone?

OUTPUT ONLY THE TRANSLATED CONTENT."""
    
    model = InferenceEngine(model_api_params)
    messages = [{"role": "user", "content": prompt}]
    translation = model.generate(messages)
    
    return translation.strip()


def translate_with_google(text: str, credentials_path: Optional[str] = None) -> str:
    """
    Translate text using Google Translate API.
    
    Args:
        text: Chinese text to translate
        credentials_path: Path to Google Cloud credentials JSON
        
    Returns:
        Translated English text
    """
    try:
        from google.cloud import translate_v2 as translate
        
        # Set credentials if provided
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        translate_client = translate.Client()
        
        # Translate
        result = translate_client.translate(
            text,
            target_language='en',
            source_language='zh-CN'
        )
        
        return result['translatedText']
    
    except ImportError:
        raise ImportError(
            "Google Cloud Translate library not installed. "
            "Install with: pip install google-cloud-translate"
        )
    except Exception as e:
        raise RuntimeError(f"Google Translate API error: {str(e)}")


def convert_dialogue(
    dialogue_path: str,
    translate: bool = False,
    translation_method: str = "llm",
    model_api_params: Optional[dict] = None,
    google_credentials_path: Optional[str] = None,
    target_language: str = "en",
    extract_profile: bool = False,
    profile_extraction_params: Optional[dict] = None
) -> Dict:
    """
    Convert a single SimPsyDial dialogue to Mind-Eval format.
    
    Workflow:
    1. Load Chinese dialogue
    2. Translate dialogue to target language (if requested)
    3. Extract profile from translated dialogue (if requested)
    4. Return Mind-Eval format
    
    Args:
        dialogue_path: Path to dialogue JSON file
        translate: Whether to translate
        translation_method: "llm" (use LLM from config), "gpt4" (legacy), or "google"
        model_api_params: API parameters for LLM translation
        google_credentials_path: Path to Google credentials
        target_language: Target language code (default: "en" for English)
        extract_profile: Whether to extract profile from dialogue
        profile_extraction_params: API parameters for profile extraction model
        
    Returns:
        Dict in Mind-Eval format
    """
    # Load dialogue
    with open(dialogue_path, 'r', encoding='utf-8') as f:
        dialogue = json.load(f)
    
    # Step 1: Translate interaction (if requested)
    interaction = []
    for turn in dialogue:
        # Keep original role if ROLE_MAPPING is None, otherwise map it
        if ROLE_MAPPING is None:
            role = turn["role"]  # Keep original: "client" or "counselor"
        else:
            role = ROLE_MAPPING.get(turn["role"], turn["role"])
        
        content = turn["content"]
        
        # Translate if needed (only translate content, not role)
        if translate:
            if translation_method in ["llm", "gpt4"]:  # Support both "llm" and legacy "gpt4"
                if not model_api_params:
                    raise ValueError("model_api_params required for LLM translation")
                content = translate_chinese_counseling_to_target_language(
                    source_text=content,
                    speaker_role=role,
                    model_api_params=model_api_params,
                    target_language=target_language
                )
            elif translation_method == "google":
                content = translate_with_google(content, google_credentials_path)
            else:
                raise ValueError(f"Unknown translation method: {translation_method}")
        
        interaction.append({
            "role": role,
            "content": content
        })
    
    # Step 2: Extract profile from translated dialogue (if requested)
    if extract_profile and profile_extraction_params:
        print(f"  Extracting profile from {os.path.basename(dialogue_path)}...")
        # Pass the translated interaction (not original dialogue)
        extracted_attrs = extract_profile_from_english_dialogue(interaction, profile_extraction_params)
        
        # Merge with default profile (fixed attributes + extracted attributes)
        member_profile = DEFAULT_PROFILE.copy()
        member_profile.update(extracted_attrs)
    else:
        member_profile = DEFAULT_PROFILE.copy()
    
    # Build Mind-Eval format
    return {
        "member_profile": member_profile,
        "interaction": interaction,
        "metadata": {
            "source": "SimPsyDial",
            "original_file": os.path.basename(dialogue_path),
            "language": "zh" if not translate else target_language,
            "translated": translate,
            "translation_method": translation_method if translate else None,
            "profile_extracted": extract_profile
        }
    }


def main(
    input_dir: str,
    output_path: str,
    translate: bool = False,
    translation_method: str = "llm",
    model_api_params: Optional[Dict[str, Any]] = None,
    google_credentials_path: Optional[str] = None,
    max_files: Optional[int] = None,
    target_language: str = "en",
    extract_profile: bool = False,
    profile_extraction_params: Optional[Dict[str, Any]] = None,
    skip_existing: bool = True
):
    """
    Convert all dialogues in input directory to Mind-Eval format.
    
    Args:
        input_dir: Directory containing SimPsyDial dialogue JSON files
        output_path: Output path for converted JSONL file
        translate: Whether to translate dialogues
        translation_method: "llm" (use LLM from config), "gpt4" (legacy), or "google"
        model_api_params: API parameters for LLM translation
        google_credentials_path: Path to Google Cloud credentials
        max_files: Maximum number of files to process (for testing)
        target_language: Target language code (default: "en" for English)
        extract_profile: Whether to extract profile from dialogue
        profile_extraction_params: API parameters for profile extraction model
        skip_existing: Whether to skip files that are already in the output (default: True)
    """
    input_path = Path(input_dir)
    output_file = Path(output_path)
    
    # Load existing converted dialogues if output file exists
    existing_converted = []
    existing_files = set()
    
    if skip_existing and output_file.exists():
        print(f"Loading existing conversions from {output_path}...")
        try:
            from mindeval.utils import load_jsonl
            existing_converted = load_jsonl(output_path)
            # Track which files have already been converted
            for item in existing_converted:
                if "metadata" in item and "original_file" in item["metadata"]:
                    existing_files.add(item["metadata"]["original_file"])
            print(f"Found {len(existing_files)} already converted files")
        except Exception as e:
            print(f"Warning: Could not load existing file: {e}")
            existing_converted = []
            existing_files = set()
    
    # Get all JSON files
    dialogue_files = sorted(input_path.glob("*.json"))
    
    # Apply max_files limit FIRST (to total files we want in output)
    if max_files:
        dialogue_files = dialogue_files[:max_files]
    
    # Filter out already converted files
    if skip_existing and existing_files:
        original_count = len(dialogue_files)
        dialogue_files = [f for f in dialogue_files if f.name not in existing_files]
        skipped_count = original_count - len(dialogue_files)
        if skipped_count > 0:
            print(f"Skipping {skipped_count} already converted files")
    
    print(f"Found {len(dialogue_files)} dialogue files to convert")
    
    if len(dialogue_files) == 0:
        print("No new files to convert. All files already processed.")
        return
    
    if translate:
        print(f"Translation enabled using method: {translation_method}")
        print(f"Target language: {target_language}")
        if translation_method in ["llm", "gpt4"]:
            print(f"Using model: {model_api_params.get('model', 'unknown')}")
    
    if extract_profile:
        print(f"Profile extraction enabled")
        if profile_extraction_params:
            print(f"Using model: {profile_extraction_params.get('model', 'unknown')}")
    
    converted = []
    errors = []
    
    for dialogue_file in tqdm(dialogue_files, desc="Converting dialogues"):
        try:
            converted_dialogue = convert_dialogue(
                str(dialogue_file),
                translate=translate,
                translation_method=translation_method,
                model_api_params=model_api_params,
                google_credentials_path=google_credentials_path,
                target_language=target_language,
                extract_profile=extract_profile,
                profile_extraction_params=profile_extraction_params
            )
            converted.append(converted_dialogue)
        except Exception as e:
            error_msg = f"Error converting {dialogue_file.name}: {str(e)}"
            print(f"\n{error_msg}")
            errors.append({
                "file": dialogue_file.name,
                "error": str(e)
            })
    
    # Merge with existing converted dialogues
    all_converted = existing_converted + converted
    
    # Save all converted dialogues (existing + new)
    save_to_jsonl(all_converted, output_path)
    print(f"\n✓ Successfully converted {len(converted)} new dialogues")
    if len(existing_converted) > 0:
        print(f"✓ Total dialogues in output: {len(all_converted)} ({len(existing_converted)} existing + {len(converted)} new)")
    print(f"✓ Saved to: {output_path}")
    
    # Save error log if any
    if errors:
        error_path = output_path.replace('.jsonl', '_errors.json')
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
        print(f"⚠ {len(errors)} errors occurred. See: {error_path}")
    
    # Print summary
    print("\n=== Conversion Summary ===")
    print(f"Total files in input: {len(sorted(input_path.glob('*.json')))}")
    if skip_existing and len(existing_files) > 0:
        print(f"Already converted: {len(existing_files)}")
    print(f"Newly converted: {len(converted)}")
    print(f"Failed: {len(errors)}")
    print(f"Total in output: {len(all_converted)}")
    print(f"Translation: {'Yes' if translate else 'No'}")
    if translate:
        print(f"Method: {translation_method}")
        print(f"Target language: {target_language}")
        if translation_method in ["llm", "gpt4"]:
            print(f"Model: {model_api_params.get('model', 'unknown')}")
    print(f"Profile extraction: {'Yes' if extract_profile else 'No'}")
    if extract_profile and profile_extraction_params:
        print(f"Extraction model: {profile_extraction_params.get('model', 'unknown')}")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([main], as_positional=False)
