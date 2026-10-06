"""
Translate canonical interactions to English for the S1 evaluation setting.

Strategy: BATCH — translate the entire dialogue in ONE LLM call (1 call per record),
vs. the old turn-by-turn approach (N calls per record). For a 30-turn dialogue this
saves ~29 API calls while also giving the model context across all turns.

Input  : data/<dataset>/test/interactions_200_canonical.jsonl
Output : data/<dataset>/test/interactions_200_S1_en.jsonl

Datasets that need translation (ZH → EN):
    simpsydial, psydial, soulchat, cpscycoun

Datasets that need translation (JA → EN):
    kokorochat

Datasets already in English (no-op — S1 file = canonical copy):
    kmi, cactus, psy_insight

Usage
-----
    # Pilot: first 5 records of all ZH datasets
    python mindeval/scripts/translate_to_en.py --limit 5

    # Specific datasets, full run
    python mindeval/scripts/translate_to_en.py --datasets simpsydial psydial soulchat

    # Single dataset pilot
    python mindeval/scripts/translate_to_en.py --datasets simpsydial --limit 5

    # Parallel (5 workers)
    python mindeval/scripts/translate_to_en.py --datasets simpsydial --max_workers 5
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# ---------------------------------------------------------------------------
# Prompt: Chinese → English (system message — fixed, potentially cached)
# ---------------------------------------------------------------------------

_SYSTEM_ZH_EN = """\
You are an expert translator for mental health counseling dialogues (Chinese → English).

TRANSLATION RULES
1. Role-aware tone
   • counselor: warm, empathetic, professional, non-judgmental
   • client: preserve emotional texture — hesitation, distress, ambivalence, uncertainty
   Do not make either speaker sound more polished, more dramatic, or more verbose than the original.

2. Semantic accuracy
   Translate meaning, not isolated words. No omission, no addition, no embellishment.
   Preserve hedges and discourse markers (嗯 / 其实 / 可能 / 就是 / 我觉得 / 说实话) with natural English equivalents when they carry emotional or conversational weight.

3. Natural dialogue style
   Real people talking — not academic, not literary. Simple, conversational English.
   No parenthetical explanations, no pinyin, no glosses inside the speaker's turn.

4. Cultural fidelity
   Preserve culturally important meanings without over-explaining.
   Do not westernize culturally specific concepts.

5. Clinical vs. colloquial
   抑郁 → "depression" (clinical) / "feeling down" (casual)
   焦虑 → "anxiety" (clinical) / "anxious" / "worried" (casual)
   强迫 → "obsessive-compulsive" (clinical) | 创伤 → "trauma"
   认知行为疗法 → "cognitive behavioral therapy (CBT)"

TERMINOLOGY QUICK REFERENCE
彩礼 → betrothal gift | 嫁妆 → dowry | 相亲 → matchmaking date
婆婆 → mother-in-law (if married) / partner's/boyfriend's mother (if not)
孝 / 孝顺 → filial duty | 面子 → face / saving face
内卷 → relentless competition | 躺平 → opting out | 啃老 → living off parents
高考 → the college entrance exam
共情 → empathy | 来访者 → client (role only) | 咨询师 → counselor (role only)
加油 → "You've got this" / "Hang in there" / "I'm rooting for you" (context-dependent)
心情复杂 → mixed feelings | 为难 → torn / caught in the middle
棘手 → tricky / hard to navigate | 力所能及 → whatever I can / as much as I'm able to

COUNSELING EXPRESSIONS
你觉得愿意…吗 / 你觉得可以…吗 → "How would you feel about…?" / "Would you feel comfortable…?"
有需要随时来找我 → "feel free to come back and talk with me anytime"
冲喜 → translate naturally (e.g. "move the wedding forward because of the family situation")

OUTPUT RULES — CRITICAL
• Return ONLY valid JSON, no text before or after.
• No speaker labels, no role tags, no markdown, no explanations.
• Preserve paragraph breaks when the original has them.\
"""

# ---------------------------------------------------------------------------
# Prompt: Korean → English (used if a KO-content dataset is added in future)
# ---------------------------------------------------------------------------

_SYSTEM_KO_EN = """\
You are an expert translator for mental health counseling dialogues (Korean → English).

TRANSLATION RULES
1. Role-aware tone: counselor = warm/empathetic/professional; client = preserve emotional texture.
2. Semantic accuracy: translate meaning, not words. No omission, no addition.
3. Natural style: conversational English, not academic or literary.
4. Cultural fidelity: preserve Korean cultural nuances (nunchi, 눈치; kibun, 기분; jeong, 정; etc.) naturally.
5. Clinical terms: 우울 → depression (clinical)/feeling down (casual); 불안 → anxiety (clinical)/anxious (casual).

OUTPUT RULES — CRITICAL
• Return ONLY valid JSON, no text before or after.
• No speaker labels, no markdown, no explanations.\
"""

_SYSTEM_JA_EN = """\
You are an expert translator for mental health counseling dialogues (Japanese → English).

TRANSLATION RULES
1. Role-aware tone
   • counselor (相談員 / カウンセラー): warm, empathetic, professional, non-judgmental
   • client (相談者 / クライアント): preserve emotional texture — hesitation, distress,
     uncertainty, self-doubt
   Do not make either speaker sound more polished or more verbose than the original.

2. Semantic accuracy
   Translate meaning, not isolated words. No omission, no addition, no embellishment.
   Preserve Japanese discourse markers (あの / えっと / まあ / なんか / でも / そうですね)
   with natural English equivalents when they carry emotional or conversational weight.

3. Natural dialogue style
   Real people talking — conversational English, not academic or literary.
   Keigo (honorific/polite speech) should become warm professional English, not overly formal.
   Casual speech (タメ口) should become natural informal English.

4. Cultural fidelity
   Preserve culturally important meanings without over-explaining.
   Japanese social concepts should be rendered naturally, not glossed in parentheses.

5. Clinical vs. colloquial
   うつ → "depression" (clinical) / "feeling down" (casual)
   不安 → "anxiety" (clinical) / "anxious" / "worried" (casual)
   トラウマ → "trauma" | 認知行動療法 → "cognitive behavioral therapy (CBT)"
   カウンセリング → "counseling" | 自己肯定感 → "self-worth" / "self-esteem"

TERMINOLOGY QUICK REFERENCE
気持ち → feelings / how you feel | つらい → hard / painful / difficult
しんどい → exhausted / worn out / really hard | もやもや → unsettled feeling / something nagging
自分を責める → blaming myself / beating myself up | 人間関係 → relationships / interpersonal issues
職場 → workplace | 家族関係 → family dynamics | 悩み → worry / concern / struggle
相談 → consultation / talking through / sharing a concern
寄り添う → being there for someone / accompanying someone through difficulty
共感 → empathy | 傾聴 → attentive listening | 受容 → acceptance / being accepted

COUNSELING EXPRESSIONS
どんなお気持ちになりますか → "How does that make you feel?" / "What feelings come up for you?"
もう少し詳しく教えていただけますか → "Could you tell me a bit more about that?"
そうなんですね → "I see." / "Is that right." (empathic acknowledgment, not a question)
うんうん → "Mm-hmm." / "I hear you." (back-channel acknowledgment)
それは大変でしたね → "That must have been really hard." / "That sounds really difficult."
一緒に考えていきましょう → "Let's think through this together."
話してくださってありがとうございます → "Thank you for sharing that with me."

OUTPUT RULES — CRITICAL
• Return ONLY valid JSON, no text before or after.
• No speaker labels, no role tags, no markdown, no explanations.
• Preserve paragraph breaks when the original has them.\
"""

_SYSTEM_BY_LANG = {"zh": _SYSTEM_ZH_EN, "ko": _SYSTEM_KO_EN, "ja": _SYSTEM_JA_EN}

# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------

DATASET_CONFIGS: dict[str, dict] = {
    "simpsydial": {
        "src": pathlib.Path("data/simpsydial/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/simpsydial/test/interactions_200_S1_en.jsonl"),
        "source_lang": "zh",
    },
    "psydial": {
        "src": pathlib.Path("data/PsyDial/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/PsyDial/test/interactions_200_S1_en.jsonl"),
        "source_lang": "zh",
    },
    "soulchat": {
        "src": pathlib.Path("data/SoulChat/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/SoulChat/test/interactions_200_S1_en.jsonl"),
        "source_lang": "zh",
    },
    # EN datasets: canonical is already S1
    "kmi": {
        "src": pathlib.Path("data/KMI/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/KMI/test/interactions_200_S1_en.jsonl"),
        "source_lang": "en",
    },
    "cactus": {
        "src": pathlib.Path("data/cactus/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/cactus/test/interactions_200_S1_en.jsonl"),
        "source_lang": "en",
    },
    "psy_insight": {
        "src": pathlib.Path("data/Psy-Insight/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/Psy-Insight/test/interactions_200_S1_en.jsonl"),
        "source_lang": "en",
    },
    "cpscycoun": {
        "src": pathlib.Path("data/CPsyCoun/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/CPsyCoun/test/interactions_200_S1_en.jsonl"),
        "source_lang": "zh",
    },
    "kokorochat": {
        "src": pathlib.Path("data/KokoroChat/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/KokoroChat/test/interactions_200_S1_en.jsonl"),
        "source_lang": "ja",
    },
    "smile": {
        "src": pathlib.Path("data/smile/test/interactions_200_canonical.jsonl"),
        "dst": pathlib.Path("data/smile/test/interactions_200_S1_en.jsonl"),
        "source_lang": "zh",
    },
    # KMI translation experiment: translate the KO source text via LLM instead of
    # reusing the built-in utterance_en. Output goes to a separate file so both
    # versions can be compared side-by-side for the translation-quality analysis.
    "kmi_ko": {
        "src": pathlib.Path("data/KMI/test/interactions_200_canonical_ko.jsonl"),
        "dst": pathlib.Path("data/KMI/test/interactions_200_S1_ko_translated_en.jsonl"),
        "source_lang": "ko",
    },
}

# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

def _build_user_message(turns: list[dict], source_lang: str) -> str:
    lang_name = {"zh": "Chinese", "ko": "Korean"}.get(source_lang, source_lang)
    n = len(turns)
    dialogue_json = json.dumps(
        [{"index": i, "role": t["role"], "content": t["content"]} for i, t in enumerate(turns)],
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"Translate the following {lang_name} counseling dialogue to English.\n\n"
        f"The dialogue has {n} turns. You MUST return exactly {n} translations.\n\n"
        "Return ONLY valid JSON in this exact format (no text before or after):\n"
        '{"translations": ["<EN turn 0>", "<EN turn 1>", ..., "<EN turn N-1>"]}\n\n'
        f"Dialogue:\n{dialogue_json}"
    )


def _parse_translation_response(response: str, expected_n: int) -> list[str] | None:
    """Parse LLM response into a list of translated strings.

    Returns None if parsing fails or count mismatches.
    """
    text = response.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        obj = json.loads(text)
        translations = obj.get("translations")
        if not isinstance(translations, list):
            return None
        if len(translations) != expected_n:
            return None
        return [str(t) for t in translations]
    except json.JSONDecodeError:
        return None


def translate_dialogue_batch(
    turns: list[dict],
    model_api_params: dict,
    source_lang: str,
    max_retries: int = 2,
) -> list[str] | None:
    """Translate all turns in a single LLM call.

    Returns a list of EN strings (same length as turns), or None on failure.
    """
    from mindeval.inference import InferenceEngine

    system_prompt = _SYSTEM_BY_LANG.get(source_lang, _SYSTEM_ZH_EN)
    user_msg = _build_user_message(turns, source_lang)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    # Strip max_retries from api_params (InferenceEngine pops it internally)
    engine = InferenceEngine(model_api_params)

    for attempt in range(1 + max_retries):
        try:
            raw = engine.generate(messages)
            result = _parse_translation_response(raw, expected_n=len(turns))
            if result is not None:
                return result
            if attempt < max_retries:
                print(f"    [warn] JSON parse failed or wrong count (attempt {attempt+1}), retrying…")
                time.sleep(2)
        except Exception as exc:
            if attempt < max_retries:
                print(f"    [warn] API error (attempt {attempt+1}): {exc}, retrying…")
                time.sleep(5)
            else:
                print(f"    [error] API error after all retries: {exc}")
    return None


def translate_dialogue_chunked(
    turns: list[dict],
    model_api_params: dict,
    source_lang: str,
    chunk_size: int,
    max_retries: int = 2,
) -> list[str] | None:
    """Translate a dialogue in chunks of `chunk_size` turns per LLM call.

    Long dialogues (>chunk_size turns) risk hitting output-token limits or the
    60s request timeout when translated in a single call, which truncates the
    JSON response and fails the exact-length check in _parse_translation_response.
    Splitting into chunks keeps each call's output short enough to complete
    reliably. Each chunk is translated independently (no cross-chunk context
    passed back to the model), so very long-range pronoun/reference resolution
    may be slightly less consistent across chunk boundaries — an acceptable
    trade-off for counseling dialogues where local context dominates.

    Returns the concatenated list of EN strings (same length/order as `turns`),
    or None if any chunk fails after retries.
    """
    if len(turns) <= chunk_size:
        return translate_dialogue_batch(turns, model_api_params, source_lang, max_retries)

    translations: list[str] = []
    for start in range(0, len(turns), chunk_size):
        chunk = turns[start : start + chunk_size]
        result = translate_dialogue_batch(chunk, model_api_params, source_lang, max_retries)
        if result is None:
            return None
        translations.extend(result)
    return translations


# ---------------------------------------------------------------------------
# Record processing
# ---------------------------------------------------------------------------

def _translate_record(
    record: dict,
    model_api_params: dict,
    source_lang: str,
    translation_model: str,
    chunk_size: int = 40,
) -> dict | None:
    """Translate one canonical record → EN record. Returns None on failure."""
    turns = record["interaction"]
    translated_contents = translate_dialogue_chunked(
        turns, model_api_params, source_lang, chunk_size
    )
    if translated_contents is None:
        return None

    en_turns = [
        {"role": t["role"], "content": en}
        for t, en in zip(turns, translated_contents)
    ]

    result = dict(record)
    result["interaction"] = en_turns
    result["metadata"] = dict(record["metadata"])
    result["metadata"]["language"] = "en"
    result["metadata"]["translation_source_language"] = source_lang
    result["metadata"]["translation_model"] = translation_model
    result["metadata"]["translation_variant"] = "llm_translated"
    return result


def _copy_record_as_en(record: dict) -> dict:
    """Copy an already-EN record into the S1 file (no translation needed)."""
    result = dict(record)
    result["metadata"] = dict(record["metadata"])
    result["metadata"]["language"] = "en"
    result["metadata"]["translation_variant"] = "utterance_en"
    return result


# ---------------------------------------------------------------------------
# Per-dataset runner
# ---------------------------------------------------------------------------

def _load_existing_ids(dst: pathlib.Path) -> set[str]:
    if not dst.exists():
        return set()
    ids = set()
    with open(dst, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ids.add(rec["interaction_id"])
            except Exception:
                pass
    return ids


def _append_jsonl(records: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_dataset(
    key: str,
    cfg: dict,
    model_api_params: dict,
    limit: int | None,
    max_workers: int,
    dry_run: bool,
    chunk_size: int = 40,
) -> dict[str, Any]:
    src: pathlib.Path = cfg["src"]
    dst: pathlib.Path = cfg["dst"]
    source_lang: str = cfg["source_lang"]
    translation_model: str = model_api_params.get("model", "unknown")

    print(f"\n[{key}]  lang={source_lang}  src={src}")

    if not src.exists():
        print(f"  SKIP — source not found: {src}")
        return {"key": key, "status": "skipped", "reason": "src missing"}

    # Load source
    with open(src, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    if limit is not None:
        records = records[:limit]

    # Skip already-translated
    existing_ids = _load_existing_ids(dst)
    todo = [r for r in records if r["interaction_id"] not in existing_ids]
    print(f"  total={len(records)}  already_done={len(existing_ids)}  to_process={len(todo)}")

    if not todo:
        print(f"  All records already processed.")
        return {"key": key, "status": "ok", "done": 0, "errors": 0}

    # --- No-op for already-EN datasets ---
    if source_lang == "en":
        print(f"  Already English — copying {len(todo)} records.")
        if not dry_run:
            _append_jsonl([_copy_record_as_en(r) for r in todo], dst)
            print(f"  dst={dst}  [written]")
        else:
            print(f"  dst={dst}  [DRY RUN]")
        return {"key": key, "status": "ok", "done": len(todo), "errors": 0}

    # --- Translation ---
    print(f"  model={translation_model}  workers={max_workers}")
    if dry_run:
        print(f"  [DRY RUN] Would translate {len(todo)} records.")
        return {"key": key, "status": "ok", "done": 0, "errors": 0}

    done_count = 0
    error_count = 0
    errors: list[str] = []

    def _process(record: dict) -> tuple[dict | None, str]:
        result = _translate_record(
            record, model_api_params, source_lang, translation_model, chunk_size
        )
        return result, record["interaction_id"]

    if max_workers == 1:
        for i, record in enumerate(todo, 1):
            print(f"  [{i}/{len(todo)}] {record['interaction_id']} …", end="", flush=True)
            result, iid = _process(record)
            if result is not None:
                _append_jsonl([result], dst)
                done_count += 1
                turns = record["metadata"]["turn_count"]
                print(f" OK ({turns} turns)")
            else:
                error_count += 1
                errors.append(iid)
                print(f" FAILED")
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process, r): r for r in todo}
            batch: list[dict] = []
            for fut in as_completed(futures):
                result, iid = fut.result()
                if result is not None:
                    batch.append(result)
                    done_count += 1
                    if len(batch) >= max_workers:
                        _append_jsonl(batch, dst)
                        batch = []
                        print(f"  progress: {done_count}/{len(todo)} done, {error_count} errors")
                else:
                    error_count += 1
                    errors.append(iid)
            if batch:
                _append_jsonl(batch, dst)

    print(f"  done={done_count}  errors={error_count}")
    if errors:
        print(f"  failed ids: {errors[:5]}")
    print(f"  dst={dst}")
    return {"key": key, "status": "ok", "done": done_count, "errors": error_count}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate canonical interactions to English (S1 setting).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASET_CONFIGS.keys()),
        default=["simpsydial", "psydial", "soulchat"],
        help=(
            "Datasets to process (default: ZH datasets). "
            "Use 'kmi_ko' to translate KMI Korean text via LLM "
            "(compare with built-in utterance_en in kmi/S1)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Translate only the first N records (pilot mode)",
    )
    parser.add_argument(
        "--config_path",
        default="config.json",
        help="Path to config.json (default: config.json)",
    )
    parser.add_argument(
        "--translator",
        default=None,
        help=(
            "Named translator from config.json 'translators' section "
            "(e.g. 'gpt', 'claude', 'qwen'). Falls back to 'translation' section "
            "if not specified or not found."
        ),
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=1,
        help="Parallel workers per dataset (default: 1 = sequential)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print plan without calling the API",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=40,
        help=(
            "Max turns translated per LLM call (default: 40). Dialogues longer "
            "than this are split into chunks to avoid output-token/timeout "
            "truncation on very long dialogues. Each chunk is translated "
            "independently (no cross-chunk context)."
        ),
    )
    args = parser.parse_args()

    # Load model config
    from mindeval.config import get_translation_config, get_config_manager
    # Re-init config manager to pick up the correct path
    import mindeval.config as _cfg_mod
    _cfg_mod._config_manager = None

    if args.translator:
        # Try named translator from 'translators' section; fall back to 'translation'
        import json as _json
        with open(args.config_path, encoding="utf-8") as _f:
            _raw_cfg = _json.load(_f)
        _translators = _raw_cfg.get("translators", {})
        if args.translator in _translators:
            model_api_params = _translators[args.translator]
            print(f"[config] Using named translator '{args.translator}'")
        else:
            print(
                f"[config] Translator '{args.translator}' not found in 'translators' section; "
                "falling back to 'translation' section."
            )
            model_api_params = get_translation_config(args.config_path)
    else:
        model_api_params = get_translation_config(args.config_path)

    print("=" * 60)
    print("translate_to_en — Mind-Eval S1 generation")
    print("=" * 60)
    print(f"model      : {model_api_params.get('model')}")
    print(f"translator : {args.translator or '(default translation section)'}")
    print(f"datasets   : {args.datasets}")
    print(f"limit      : {args.limit or 'all'}")
    print(f"max_workers: {args.max_workers}")
    print(f"chunk_size : {args.chunk_size}")
    print(f"dry_run    : {args.dry_run}")
    print("=" * 60)

    results = []
    for key in args.datasets:
        cfg = DATASET_CONFIGS[key]
        r = run_dataset(
            key=key,
            cfg=cfg,
            model_api_params=model_api_params,
            limit=args.limit,
            max_workers=args.max_workers,
            dry_run=args.dry_run,
            chunk_size=args.chunk_size,
        )
        results.append(r)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for r in results:
        status = r.get("status", "?")
        done = r.get("done", "-")
        errors = r.get("errors", "-")
        print(f"  {r['key']:14s}  {status:8s}  done={done}  errors={errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
