"""
Translate the few-shot calibration examples embedded in the English judge
prompt (v0_1) into Chinese and Korean, so the S2 judge prompts have the SAME
calibration anchors as the S1/S3 English judge.

Why: evaluate.py uses judge template `v0_1` for S1/S3, which contains 5 few-shot
example conversations (each with reference scores). The manually-translated ZH/KO
judge prompts originally had NO few-shots — a confound for the S3-vs-S2
"judge language" comparison. This script extracts those 5 examples, translates
the dialogue turns to the target language (keeping <therapist>/<member> tags and
the reference scores intact), and writes a ready-to-include text block.

Output:
    mindeval/judge_fewshots_zh.txt
    mindeval/judge_fewshots_ko.txt

These files are loaded by judge_prompts_zh.py / judge_prompts_ko.py and inserted
between the rubric and the "now evaluate" section.

Usage:
    python -m mindeval.scripts.translate_judge_fewshots --langs zh ko
    python -m mindeval.scripts.translate_judge_fewshots --langs zh --dry_run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from mindeval.judge_prompts import JUDGE_PROMPT_TEMPLATE

# English criterion order in the <output> block
_CRITERIA_EN = [
    "Clinical Accuracy & Competence",
    "Ethical & Professional Conduct",
    "Assessment & Response",
    "Therapeutic Relationship & Alliance",
    "AI-Specific Communication Quality",
]

# Localized criterion names — must match the rubric translations in
# judge_prompts_zh.py / judge_prompts_ko.py and the output format the judge is
# asked to produce (English name kept in parens so parse_judge_scores works).
_CRITERIA_LOCAL = {
    "zh": [
        "临床准确性与胜任力",
        "伦理与专业行为",
        "评估与回应",
        "治疗关系与联盟",
        "AI 特定沟通质量",
    ],
    "ko": [
        "임상적 정확성 및 역량",
        "윤리적 및 전문적 행동",
        "평가 및 반응",
        "치료적 관계 및 동맹",
        "AI 특정 의사소통 품질",
    ],
}

_LANG_NAME = {"zh": "Chinese (Simplified)", "ko": "Korean"}

_OUTPUT_DIR = pathlib.Path("mindeval")
_OUTPUT_FILE = {"zh": _OUTPUT_DIR / "judge_fewshots_zh.txt", "ko": _OUTPUT_DIR / "judge_fewshots_ko.txt"}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_fewshot_examples() -> list[dict]:
    """Return list of {turns: [(tag, content)], scores: {criterion: float}}.

    Extracts the few-shot region between </criterion_5> and
    'Now, consider a new instance:' from the English v0_1 template.
    """
    template_str = JUDGE_PROMPT_TEMPLATE.template

    start_marker = "</criterion_5>"
    end_marker = "Now, consider a new instance:"
    start = template_str.index(start_marker) + len(start_marker)
    end = template_str.index(end_marker)
    region = template_str[start:end]

    # Each example: <conversation>...</conversation> followed by <output>...</output>
    pattern = re.compile(
        r"<conversation>(.*?)</conversation>\s*<output>(.*?)</output>",
        re.DOTALL,
    )

    examples = []
    for conv_block, output_block in pattern.findall(region):
        turns = _parse_turns(conv_block)
        scores = _parse_scores(output_block)
        examples.append({"turns": turns, "scores": scores})
    return examples


def _parse_turns(conv_block: str) -> list[tuple[str, str]]:
    """Parse <therapist>/<member> turns. Returns list of (tag, content)."""
    pattern = re.compile(r"<(therapist|member)>(.*?)</\1>", re.DOTALL)
    return [(tag, content.strip()) for tag, content in pattern.findall(conv_block)]


def _parse_scores(output_block: str) -> dict[str, float]:
    scores = {}
    for crit in _CRITERIA_EN:
        m = re.search(rf"{re.escape(crit)}\s*[:：]\s*(\d+\.?\d*)", output_block)
        if m:
            scores[crit] = float(m.group(1))
    return scores


# ---------------------------------------------------------------------------
# Translation (EN -> target)
# ---------------------------------------------------------------------------

_SYSTEM_EN_TO = """\
You are an expert translator for mental health counseling dialogues (English → {lang}).

RULES
1. Role-aware tone: counselor (therapist) = warm, empathetic, professional; client (member) = preserve emotional texture.
2. Semantic accuracy: translate meaning, not words. No omission, no addition.
3. Natural conversational style in {lang} — real people talking, not academic prose.
4. Preserve clinical vs. colloquial distinctions and therapeutic terminology.
5. Keep any markdown formatting (bullet points, **bold**, headings) intact.

OUTPUT RULES — CRITICAL
• Return ONLY valid JSON, no text before or after.
• No speaker labels, no markdown fences, no explanations.\
"""


def _build_user_message(turns: list[tuple[str, str]], lang_name: str) -> str:
    n = len(turns)
    payload = json.dumps(
        [{"index": i, "content": c} for i, (_, c) in enumerate(turns)],
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"Translate the following English counseling dialogue turns to {lang_name}.\n\n"
        f"There are {n} turns. You MUST return exactly {n} translations in order.\n\n"
        "Return ONLY valid JSON in this exact format (no text before or after):\n"
        '{"translations": ["<turn 0>", "<turn 1>", ..., "<turn N-1>"]}\n\n'
        f"Turns:\n{payload}"
    )


def _parse_translation_response(response: str, expected_n: int) -> list[str] | None:
    text = response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        obj = json.loads(text)
        translations = obj.get("translations")
        if not isinstance(translations, list) or len(translations) != expected_n:
            return None
        return [str(t) for t in translations]
    except json.JSONDecodeError:
        return None


def translate_turns(turns: list[tuple[str, str]], lang: str, model_api_params: dict,
                    max_retries: int = 2) -> list[str] | None:
    from mindeval.inference import InferenceEngine

    lang_name = _LANG_NAME[lang]
    messages = [
        {"role": "system", "content": _SYSTEM_EN_TO.format(lang=lang_name)},
        {"role": "user", "content": _build_user_message(turns, lang_name)},
    ]
    engine = InferenceEngine(model_api_params)
    for attempt in range(1 + max_retries):
        try:
            raw = engine.generate(messages)
            parsed = _parse_translation_response(raw, expected_n=len(turns))
            if parsed is not None:
                return parsed
            if attempt < max_retries:
                print(f"    [warn] parse failed (attempt {attempt+1}), retrying…")
                time.sleep(2)
        except Exception as exc:
            if attempt < max_retries:
                print(f"    [warn] API error (attempt {attempt+1}): {exc}, retrying…")
                time.sleep(5)
            else:
                print(f"    [error] API error after retries: {exc}")
    return None


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _format_output_block(scores: dict[str, float], lang: str) -> str:
    """Build the localized ratings block matching the judge output format."""
    local_names = _CRITERIA_LOCAL[lang]
    lines = []
    for crit_en, crit_local in zip(_CRITERIA_EN, local_names):
        score = scores.get(crit_en, 3.0)
        # Drop trailing .0 cleanly but keep decimals like 3.75
        score_str = f"{score:g}"
        lines.append(f"{crit_local} ({crit_en}): {score_str}")
    return "\n".join(lines)


def build_fewshot_text(examples: list[dict], translated: list[list[str]], lang: str) -> str:
    """Assemble the full few-shot block in the target language."""
    blocks = []
    for ex, trans in zip(examples, translated):
        turns = ex["turns"]
        conv_lines = ["<conversation>"]
        for (tag, _), tr in zip(turns, trans):
            conv_lines.append(f"<{tag}>")
            conv_lines.append(tr)
            conv_lines.append(f"</{tag}>")
        conv_lines.append("</conversation>")
        conv_str = "\n".join(conv_lines)

        output_str = "<output>\n" + _format_output_block(ex["scores"], lang) + "\n</output>"
        blocks.append(conv_str + "\n\n" + output_str)

    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Translate judge few-shot examples to ZH/KO.")
    parser.add_argument("--langs", nargs="+", choices=["zh", "ko"], default=["zh", "ko"])
    parser.add_argument("--config_path", default="config.json")
    parser.add_argument("--dry_run", action="store_true",
                        help="Extract + report only, no API calls, no file writes")
    args = parser.parse_args()

    import mindeval.config as _cfg_mod
    _cfg_mod._config_manager = None
    from mindeval.config import get_translation_config
    model_api_params = get_translation_config(args.config_path)

    print("=" * 60)
    print("translate_judge_fewshots")
    print("=" * 60)
    print(f"model: {model_api_params.get('model')}")
    print(f"langs: {args.langs}")
    print(f"dry_run: {args.dry_run}")

    examples = extract_fewshot_examples()
    total_turns = sum(len(e["turns"]) for e in examples)
    print(f"\nExtracted {len(examples)} few-shot examples ({total_turns} turns total)")
    for i, ex in enumerate(examples):
        print(f"  [{i}] turns={len(ex['turns']):3d}  scores={ex['scores']}")

    if len(examples) == 0:
        print("ERROR: no few-shot examples extracted — aborting.")
        return

    if args.dry_run:
        print("\n[DRY RUN] stopping before translation.")
        return

    for lang in args.langs:
        print(f"\n--- Translating to {_LANG_NAME[lang]} ---")
        translated_all = []
        ok = True
        for i, ex in enumerate(examples):
            print(f"  example {i} ({len(ex['turns'])} turns) …", end="", flush=True)
            tr = translate_turns(ex["turns"], lang, model_api_params)
            if tr is None:
                print(" FAILED")
                ok = False
                break
            translated_all.append(tr)
            print(" OK")

        if not ok:
            print(f"  [error] translation failed for {lang} — skipping write.")
            continue

        text = build_fewshot_text(examples, translated_all, lang)
        # Escape '$' so string.Template treats few-shots as literal text
        text = text.replace("$", "$$")

        out_path = _OUTPUT_FILE[lang]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"  wrote {out_path}  ({len(text)} chars)")

    print("\nDone.")


if __name__ == "__main__":
    main()
