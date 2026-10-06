"""
Dimension C — Emotional Trajectory Profiling Pipeline (Multi-dataset)
UED Framework + NRC-VAD Lexicon v2.1 (EN) + v1 (Korean, Japanese, Chinese)

Chạy Dim-C cho bất kỳ dataset nào có canonical JSONL.

Input file strategy:
  - EN datasets (cactus, AnnoMI, Psy-Insight):
      → data/<dataset>/test/interactions_*_canonical.jsonl  (text gốc đã là EN)
      → Lexicon: NRC-VAD v2.1 EN unigrams
  - Non-EN với bản dịch S1 (simpsydial, PsyDial, SoulChat):
      → data/<dataset>/test/interactions_*_S1_en.jsonl      (đã dịch sang EN)
      → Lexicon: NRC-VAD v2.1 EN (Approach B)
  - KMI Korean (native):
      → data/KMI/test/interactions_200_canonical_ko.jsonl   (text KO gốc)
      → Lexicon: NRC-VAD v1 Korean (Approach A) — cần tải thêm, xem §SETUP bên dưới
  - KMI English (utterance_en):
      → data/KMI/test/interactions_200_S1_en.jsonl
      → Lexicon: NRC-VAD v2.1 EN (Approach B)
  - Non-EN chưa có S1 (CPsyCoun ZH, KokoroChat JA):
      → data/<dataset>/test/interactions_*_canonical.jsonl  (text gốc — coverage ~0% với EN lexicon)
      → Ghi chú: cần dịch trước hoặc tải lexicon bản ngữ

=== NGÔN NGỮ ĐƯỢC HỖ TRỢ ===

  Datasets gồm 3 ngôn ngữ chính: Tiếng Anh (EN), Tiếng Trung (ZH), Tiếng Nhật (JA)

  EN datasets — dùng NRC-VAD v2.1 EN trực tiếp (Approach A):
    cactus, annomi, psy_insight

  ZH datasets — 2 lựa chọn:
    Approach A (bản ngữ): simpsydial_zh, psydial_zh, soulchat_zh, cpsycoun_zh
      → Cần tải: NRC-VAD-Lexicon-v1-multilang/Chinese-Simplified-NRC-VAD-Lexicon.txt
      → Tokenizer: jieba (pip install jieba) hoặc character-level fallback
    Approach B (dịch sang EN): simpsydial, psydial, soulchat (dùng S1_en đã có)

  JA datasets — 2 lựa chọn:
    Approach A (bản ngữ): kokorochat_ja
      → Cần tải: NRC-VAD-Lexicon-v1-multilang/Japanese-NRC-VAD-Lexicon.txt
      → Tokenizer: fugashi (pip install fugashi[unidic-lite]) hoặc character-level fallback
    Approach B (dịch sang EN): kokorochat (cần dịch trước)

=== SETUP: Tải NRC-VAD v1 Multilingual ===
  1. Truy cập http://saifmohammad.com/WebPages/nrc-vad.html
  2. Tải "NRC-VAD-Lexicon-v1.zip"
  3. Giải nén → OneFilePerLanguage/
  4. Copy vào NRC-VAD-Lexicon-v1-multilang/:
     - Chinese-Simplified-NRC-VAD-Lexicon.txt  (ZH)
     - Japanese-NRC-VAD-Lexicon.txt            (JA)
  
  Format: word<TAB>valence<TAB>arousal<TAB>dominance  (scale 0–1)
  → Script normalize tự động sang [-1, +1]: new = (old - 0.5) × 2

Usage:
    # EN datasets
    python dimC_pipeline.py --dataset cactus annomi psy_insight --n 20

    # ZH Approach A (native text + ZH lexicon)
    python dimC_pipeline.py --dataset simpsydial_zh psydial_zh soulchat_zh cpsycoun_zh --n 20

    # ZH Approach B (EN translation)
    python dimC_pipeline.py --dataset simpsydial psydial soulchat --n 20

    # JA Approach A (native text + JA lexicon)
    python dimC_pipeline.py --dataset kokorochat_ja --n 20

    # ── Chạy toàn bộ 2 phương án (theo DimC_Pipeline_Guide.md §3.4) ──

    # Approach B — Dịch sang EN (S1): EN datasets + ZH/KO đã có bản dịch
    python dimC_pipeline.py --dataset cactus annomi psy_insight simpsydial psydial soulchat kmi --n 20

    # Approach A — Bản ngữ (S3): text gốc + lexicon bản ngữ
    python dimC_pipeline.py --dataset simpsydial_zh psydial_zh soulchat_zh cpsycoun_zh kokorochat_ja kmi_ko --n 20

    # Chạy tất cả (bao gồm cả A và B)
    python dimC_pipeline.py --all --n 20
"""

import argparse
import json
import re
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPT_DIR.parent      # mind-eval/

LEXICON_EN_PATH = (
    SCRIPT_DIR
    / "NRC-VAD-Lexicon-v2.1"
    / "Unigrams"
    / "unigrams-NRC-VAD-Lexicon-v2.1.txt"
)

# NRC-VAD v1 multilingual lexicons (cần tải thêm — xem §SETUP trong docstring)
LEXICON_V1_DIR = SCRIPT_DIR / "NRC-VAD-Lexicon-v1-multilang"
LEXICON_KO_PATH = LEXICON_V1_DIR / "Korean-NRC-VAD-Lexicon.txt"
LEXICON_ZH_PATH = LEXICON_V1_DIR / "Chinese-Simplified-NRC-VAD-Lexicon.txt"
LEXICON_JA_PATH = LEXICON_V1_DIR / "Japanese-NRC-VAD-Lexicon.txt"

# ─────────────────────────────────────────────
# DATASET REGISTRY
# ─────────────────────────────────────────────
# Mỗi entry:
#   input_file  : relative path từ REPO_ROOT
#   language    : ngôn ngữ hội thoại gốc
#   en_ready    : True = file đã là EN (dùng trực tiếp với lexicon EN)
#   note        : cảnh báo nếu cần xử lý thêm

DATASET_REGISTRY = {
    "cactus": {
        "input_file": "data/cactus/test/interactions_200_canonical.jsonl",
        "language": "en",
        "en_ready": True,
        "note": "",
    },
    "annomi": {
        "input_file": "data/AnnoMI/test/interactions_112_canonical.jsonl",
        "language": "en",
        "en_ready": True,
        "note": "",
    },
    "psy_insight": {
        "input_file": "data/Psy-Insight/test/interactions_200_canonical.jsonl",
        "language": "en",
        "en_ready": True,
        "note": "",
    },
    "simpsydial": {
        "input_file": "data/simpsydial/test/interactions_200_S1_en.jsonl",
        "language": "zh",
        "en_ready": True,  # S1 file đã dịch sang EN
        "note": "Using S1_en translation (GPT-translated). Approach B via translation.",
    },
    "psydial": {
        "input_file": "data/PsyDial/test/interactions_200_S1_en.jsonl",
        "language": "zh",
        "en_ready": True,
        "note": "Using S1_en translation (GPT-translated). Approach B via translation.",
    },
    "soulchat": {
        "input_file": "data/SoulChat/test/interactions_200_S1_en.jsonl",
        "language": "zh",
        "en_ready": True,
        "note": "Using S1_en translation (GPT-translated). Approach B via translation.",
    },
    "kmi": {
        "input_file": "data/KMI/test/interactions_200_S1_en.jsonl",
        "language": "ko",
        "en_ready": True,
        "lexicon_path": None,
        "note": "Using S1_en (utterance_en). Approach B — EN lexicon on EN text.",
    },
    # ──────────────────────────────────────────────────────────────────────────
    # APPROACH A — Text gốc bản ngữ + Lexicon bản ngữ (NRC-VAD v1 multilang)
    # Tương đương S3: dùng chính dataset ngôn ngữ gốc
    # ──────────────────────────────────────────────────────────────────────────
    "simpsydial_zh": {
        "input_file": "data/simpsydial/test/interactions_200_canonical.jsonl",
        "language": "zh", "approach": "A",
        "lexicon_path": str(LEXICON_ZH_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "zh",
        "note": "Approach A — ZH native text + NRC-VAD v1 Chinese-Simplified (native col)",
    },
    "psydial_zh": {
        "input_file": "data/PsyDial/test/interactions_200_canonical.jsonl",
        "language": "zh", "approach": "A",
        "lexicon_path": str(LEXICON_ZH_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "zh",
        "note": "Approach A — ZH native text + NRC-VAD v1 Chinese-Simplified (native col)",
    },
    "soulchat_zh": {
        "input_file": "data/SoulChat/test/interactions_200_canonical.jsonl",
        "language": "zh", "approach": "A",
        "lexicon_path": str(LEXICON_ZH_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "zh",
        "note": "Approach A — ZH native text + NRC-VAD v1 Chinese-Simplified (native col)",
    },
    "cpsycoun_zh": {
        "input_file": "data/CPsyCoun/test/interactions_200_canonical.jsonl",
        "language": "zh", "approach": "A",
        "lexicon_path": str(LEXICON_ZH_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "zh",
        "note": "Approach A — ZH native text + NRC-VAD v1 Chinese-Simplified (native col)",
    },
    "kokorochat_ja": {
        "input_file": "data/KokoroChat/test/interactions_200_canonical.jsonl",
        "language": "ja", "approach": "A",
        "lexicon_path": str(LEXICON_JA_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "ja",
        "note": "Approach A — JA native text + NRC-VAD v1 Japanese (native col)",
    },
    "kmi_ko": {
        "input_file": "data/KMI/test/interactions_200_canonical_ko.jsonl",
        "language": "ko", "approach": "A",
        "lexicon_path": str(LEXICON_KO_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "ko",
        "note": "Approach A — KO native text + NRC-VAD v1 Korean (native col)",
    },
    # ── SMILE (ZH, synthetic, single/multi-turn) ──────────────────────────
    "smile_zh": {
        "input_file": "data/smile/test/interactions_200_canonical.jsonl",
        "language": "zh", "approach": "A",
        "lexicon_path": str(LEXICON_ZH_PATH),
        "lexicon_scale": "0_1", "use_native_col": True,
        "tokenizer": "zh",
        "note": "Approach A — ZH native text + NRC-VAD v1 Chinese-Simplified (native col)",
    },
    # ──────────────────────────────────────────────────────────────────────────
    # APPROACH B — Dịch sang EN + Lexicon EN (NRC-VAD v2.1)
    # Tương đương S1: dùng bản dịch EN để đánh giá
    # ──────────────────────────────────────────────────────────────────────────
    "cpsycoun": {
        "input_file": "data/CPsyCoun/test/interactions_200_S1_en.jsonl",
        "language": "zh", "approach": "B",
        "en_ready": True,
        "note": "Approach B — ZH->EN translation (S1_en). EN lexicon v2.1.",
    },
    "kokorochat": {
        "input_file": "data/KokoroChat/test/interactions_200_S1_en.jsonl",
        "language": "ja", "approach": "B",
        "en_ready": True,
        "note": "Approach B — JA->EN translation (S1_en). EN lexicon v2.1.",
    },
    # ── ESConv (EN, crowdsourced emotional support) ───────────────────────
    "esconv": {
        "input_file": "data/ESConv/test/interactions_200_canonical.jsonl",
        "language": "en",
        "en_ready": True,
        "note": "EN native. Approach B — EN lexicon v2.1.",
    },
    # ── SMILE Approach B (ZH->EN translation, S1_en) ─────────────────────
    "smile": {
        "input_file": "data/smile/test/interactions_200_S1_en.jsonl",
        "language": "zh", "approach": "B",
        "en_ready": True,
        "note": "Approach B — ZH->EN translation (S1_en). EN lexicon v2.1.",
    },
}

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CONFIG = {
    "window_size": 10,
    "step": 1,
    "min_tokens": 30,
    "default_n": 20,
}


# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

def load_vad_lexicon(filepath: Path, scale: str = "neg1_1", use_native_col: bool = False) -> dict:
    """
    Load NRC-VAD lexicon.

    scale:
      "neg1_1" → NRC-VAD v2.1 EN: giá trị trong [-1, +1], giữ nguyên.
      "0_1"    → NRC-VAD v1 multilang: giá trị trong [0, 1],
                 normalize → [-1, +1] bằng: new = (old - 0.5) × 2

    use_native_col:
      False → dùng cột 0 (English word) làm key.
              Format v2.1: word | valence | arousal | dominance  (4 cột)
      True  → dùng cột 4 (Native word) làm key.
              Format v1 multilang: EN word | valence | arousal | dominance | Native word  (5 cột)

    Header bị bỏ qua tự động (dòng không parse được sang float).
    """
    lexicon = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            # Multilingual v1: cần ít nhất 5 cột; v2.1 EN: cần ít nhất 4 cột
            min_cols = 5 if use_native_col else 4
            if len(parts) < min_cols:
                continue
            try:
                v, a, d = float(parts[1]), float(parts[2]), float(parts[3])
            except ValueError:
                continue  # bỏ qua dòng header

            # Chọn cột key
            word = parts[4] if use_native_col else parts[0]
            word = word.strip()
            if not word:
                continue

            if scale == "0_1":
                v = (v - 0.5) * 2
                a = (a - 0.5) * 2
                d = (d - 0.5) * 2
            lexicon[word] = (v, a, d)
    return lexicon


def load_canonical_jsonl(path: Path, n: int = None) -> list[dict]:
    """Load canonical JSONL, adapting role/key variants to unified format."""
    dialogues = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)

            # Resolve interaction key (canonical uses "interaction")
            interaction = rec.get("interaction") or rec.get("dialog") or rec.get("dialogue") or []

            # Normalize turns: {role, content} OR {role, text} → {role, text}
            turns = []
            for t in interaction:
                role = t.get("role", "")
                text = t.get("content") or t.get("text") or t.get("utterance") or ""
                turns.append({"role": role, "text": text})

            meta = rec.get("metadata", {})
            dialogues.append({
                "dialogue_id": rec.get("interaction_id") or rec.get("id") or f"unk_{len(dialogues)}",
                "dataset": meta.get("source", "unknown"),
                "language": meta.get("language", "unknown"),
                "turns": turns,
            })

    if n is not None:
        dialogues = dialogues[:n]
    return dialogues


def extract_speaker_texts(dialogue: dict, role: str = "client") -> tuple[list[str], str]:
    texts = [t["text"] for t in dialogue["turns"] if t["role"] == role]
    return texts, " ".join(texts)


def tokenize_en(text: str) -> list[str]:
    """EN tokenizer: lowercase, strip non-alpha."""
    text = text.lower()
    text = re.sub(r"[^a-z\s']", " ", text)
    return text.split()


# ── Korean: particle suffix list (longest first) — used as fallback ───────
_KO_SUFFIXES = [
    "으로부터", "에게서도", "에서부터", "한테서도",
    "에서도", "에서는", "에서의", "에게서", "한테서", "로부터",
    "이에서", "이에게", "이라는", "들에게", "들에서",
    "으로서", "이라는",
    "에서", "에게", "한테", "으로", "이라", "들이", "들을", "들은",
    "들도", "들과", "들의", "이고", "이나", "이랑", "이며", "이면",
    "이요", "이야", "이에", "과도", "와도", "에도", "는데",
    "은데", "인데", "이다", "이든",
    "로도", "로는", "로만", "에도", "에는", "에만",
    "이고", "이나", "이랑", "이며",
    "과도", "과는", "과를", "와도", "와는", "와를",
    "아요", "어요", "세요", "어서", "아서", "지만", "지도", "라도",
    "고도", "면서", "거나", "더니",
    "의", "도", "만", "이", "가", "을", "를", "은", "는",
    "에", "로", "과", "와", "서",
]

# Kiwipiepy POS tags to KEEP for emotion analysis
_KO_CONTENT_TAGS = {
    "NNG",  # 일반명사
    "NNP",  # 고유명사
    "NNB",  # 의존명사
    "VV",   # 동사
    "VA",   # 형용사
    "VX",   # 보조용언
    "MAG",  # 일반부사
    "MAJ",  # 접속부사
    "IC",   # 감탄사
    "SL",   # 외래어
}


def _strip_ko_particle(eojeol: str) -> str:
    """Strip Korean grammatical particles/endings to get root form."""
    if len(eojeol) <= 1:
        return eojeol
    for suffix in _KO_SUFFIXES:
        if eojeol.endswith(suffix) and len(eojeol) > len(suffix):
            return eojeol[:-len(suffix)]
    return eojeol


def tokenize_ko(text: str, use_kiwi: bool = True) -> list[str]:
    """
    Korean tokenizer — 3-level strategy:
      1. Kiwipiepy (no Java required): morpheme analysis, filter to content POS tags
         (NNG, NNP, VV, VA, MAG, IC...). Gets base form of each morpheme.
         Loại bỏ J* (particles) và E* (endings) không có trong emotion lexicon.
      2. Eojeol + particle stripping: fallback khi kiwipiepy không có.
         Tách theo khoảng trắng + strip điều kiện tiếp và phụ tố cuối.
      3. Raw eojeol: fallback cuối cùng.
    """
    text = re.sub(r"[^\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\w\s]", " ", text)
    text = text.strip()
    if not text:
        return []

    if use_kiwi:
        try:
            from kiwipiepy import Kiwi
            kiwi = Kiwi()
            result = kiwi.analyze(text)
            tokens = [
                tok.form for tok in result[0][0]
                if tok.tag in _KO_CONTENT_TAGS and tok.form.strip()
            ]
            if tokens:
                return tokens
        except Exception:
            pass

    # Eojeol + particle stripping fallback
    eojeols = [tok for tok in text.split() if tok.strip()]
    stripped = [_strip_ko_particle(e) for e in eojeols]
    return stripped if stripped else eojeols


def tokenize_zh(text: str, use_jieba: bool = True) -> list[str]:
    """
    Chinese tokenizer — 2-level strategy:
      1. Jieba word segmentation: tách từ đa ký tự, khớp tốt với lexicon avg 2.4 chars.
      2. Character-level fallback: mỗi ký tự Hán = 1 token.
         Chỉ khớp được 5.6% lexicon (1111 single-char entries).
    """
    text = re.sub(r"[^\u4E00-\u9FFF\u3400-\u4DBF\s]", " ", text)
    text = text.strip()
    if not text:
        return []

    if use_jieba:
        try:
            import jieba
            jieba.setLogLevel(60)
            tokens = list(jieba.cut(text))
            return [t.strip() for t in tokens if t.strip()]
        except ImportError:
            pass

    return [ch for ch in text if ch.strip()]


def _mfm_tokenize(text: str, lexicon: dict, max_len: int = 6) -> list[str]:
    """
    Maximum Forward Matching tokenizer — dùng lexicon như dictionary.
    Tại mỗi vị trí, thử match dài nhất → khớp → advance.
    Fallback về single-char nếu không khớp.
    Dùng cho JA khi fugashi chưa cài.
    """
    tokens = []
    i = 0
    while i < len(text):
        if not text[i].strip():
            i += 1
            continue
        found = False
        for length in range(min(max_len, len(text) - i), 0, -1):
            substr = text[i : i + length]
            if substr in lexicon:
                tokens.append(substr)
                i += length
                found = True
                break
        if not found:
            tokens.append(text[i])
            i += 1
    return tokens


# POS categories to EXCLUDE for Japanese emotion analysis
# 助動詞 (auxiliary verbs: ます、た、ない、れる...) and 助詞 (particles: が、を、は、に...)
# carry no emotional content → filtering them out improves both coverage and arc quality.
_JA_SKIP_POS = {"助動詞", "助詞"}


def tokenize_ja(text: str, use_fugashi: bool = True,
                _lexicon: dict | None = None) -> list[str]:
    """
    Japanese tokenizer — 3-level strategy:
      1. Fugashi + lexicon-aware selection + function-word filtering:
         - Bỏ qua 助動詞 (auxiliaries) và 助詞 (particles) — không mang cảm xúc.
         - Với mỗi content morpheme, chọn form khớp lexicon (surface → lemma → surface).
         - One token per morpheme → không inflate token count.
         → Coverage ~40% thay vì 10% của character-level.
      2. MFM (Maximum Forward Matching) với lexicon — fugashi chưa cài.
      3. Character-level fallback cuối cùng.
    """
    text = re.sub(
        r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\s]", " ", text
    )
    text = text.strip()
    if not text:
        return []

    if use_fugashi:
        try:
            import fugashi
            tagger = fugashi.Tagger()
            tokens = []
            for word in tagger(text):
                surface = word.surface.strip()
                if not surface:
                    continue
                # Skip pure function words (particles + auxiliaries)
                try:
                    pos1 = word.feature.pos1
                    if pos1 in _JA_SKIP_POS:
                        continue
                except AttributeError:
                    pass
                # Get lemma (dictionary form)
                try:
                    lemma = word.feature.lemma
                    lemma = lemma.strip() if lemma and lemma not in ("*", "") else None
                except AttributeError:
                    lemma = None

                if _lexicon is not None:
                    # Lexicon-aware: prefer the form that matches
                    if surface in _lexicon:
                        tokens.append(surface)
                    elif lemma and lemma in _lexicon:
                        tokens.append(lemma)
                    else:
                        tokens.append(surface)
                else:
                    tokens.append(surface)
                    if lemma and lemma != surface:
                        tokens.append(lemma)
            return [t for t in tokens if t.strip()]
        except (ImportError, Exception):
            pass

    # MFM fallback
    if _lexicon:
        return _mfm_tokenize(text, _lexicon, max_len=6)

    return [ch for ch in text if ch.strip()]


def tokenize(text: str, lang: str = "en",
             _lexicon: dict | None = None) -> list[str]:
    """Dispatch tokenizer theo ngôn ngữ."""
    if lang == "ko":
        return tokenize_ko(text)
    elif lang == "zh":
        return tokenize_zh(text)
    elif lang == "ja":
        return tokenize_ja(text, _lexicon=_lexicon)
    else:
        return tokenize_en(text)


def _expand_zh_coverage(tokens: list[str], lexicon: dict) -> list[str]:
    """
    Post-tokenization ZH coverage boost:
    Với mỗi jieba token KHÔNG có trong lexicon và dài > 1 ký tự,
    THAY THẾ bằng từng ký tự riêng lẻ (không thêm cả hai).
    → phủ thêm single-char lexicon entries mà không inflate denominator.
    Token 1 ký tự hoặc đã có trong lexicon → giữ nguyên.
    """
    expanded = []
    for tok in tokens:
        if tok in lexicon or len(tok) == 1:
            expanded.append(tok)
        else:
            # Replace with constituent chars (some may be in lexicon)
            chars = [ch for ch in tok if ch.strip()]
            expanded.extend(chars if chars else [tok])
    return expanded


def lexicon_coverage(tokens: list[str], lexicon: dict) -> float:
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in lexicon) / len(tokens)


def compute_emotion_arc(
    tokens: list[str],
    lexicon: dict,
    window_size: int = 10,
    step: int = 1,
) -> tuple:
    arc = []
    valid_indices = []
    for i in range(0, len(tokens) - window_size + 1, step):
        window = tokens[i : i + window_size]
        scores = [lexicon[w] for w in window if w in lexicon]
        if not scores:
            continue
        arc.append(np.array(scores, dtype=float).mean(axis=0))
        valid_indices.append(i)
    if not arc:
        return None, []
    return np.array(arc), valid_indices


def compute_ued_metrics(arc_1d: np.ndarray, window_size: int = 10) -> dict | None:
    """
    Compute UED displacement metrics.

    Unit convention — WORDS (not arc positions):
      Arc position i covers words[i : i+W] where W = window_size, step = 1.
      Converting arc positions → word counts:
        - displacement_length (words) = (n_arc_positions - 1) + W
        - rise_words                  = peak_idx_in_disp + W
        - recovery_words              = (n_arc_positions - peak_idx - 1) + W

    This matches FtD (Feel the Difference) which measures in words.
    Using arc positions directly (old code) would over-estimate rates by ~W/peak_idx ≈ 3×.
    """
    if arc_1d is None or len(arc_1d) < 10:
        return None
    mean = float(np.mean(arc_1d))
    std  = float(np.std(arc_1d))
    home_low, home_high = mean - std, mean + std

    displacements = []
    current = None
    for t, val in enumerate(arc_1d):
        outside = val < home_low or val > home_high
        if outside:
            if current is None:
                current = {"start": t, "values": [val],
                           "direction": "low" if val < home_low else "high"}
            else:
                current["values"].append(val)
        else:
            if current is not None:
                current["end"] = t - 1
                displacements.append(current)
                current = None
    if current is not None:
        current["end"] = len(arc_1d) - 1
        displacements.append(current)

    all_pd, all_dl, all_rr, all_rec = [], [], [], []
    low_pd, low_dl, low_rr, low_rec = [], [], [], []
    high_pd, high_dl, high_rr, high_rec = [], [], [], []

    for d in displacements:
        vals = np.array(d["values"])
        n_pos = len(vals)   # number of arc positions in displacement
        if d["direction"] == "low":
            peak_val = float(np.min(vals)); peak_idx = int(np.argmin(vals))
        else:
            peak_val = float(np.max(vals)); peak_idx = int(np.argmax(vals))
        peak_dist = abs(peak_val - mean)

        # Convert arc positions → word counts (FtD unit)
        # Each arc position i covers words[i : i+W]; step=1
        disp_words = (n_pos - 1) + window_size        # total word span of displacement
        rise_words = peak_idx + window_size            # word span from start → peak
        rec_words  = (n_pos - peak_idx - 1) + window_size  # word span from peak → end

        rise_rate = peak_dist / rise_words
        rec_rate  = peak_dist / rec_words

        all_pd.append(peak_dist); all_dl.append(disp_words)
        all_rr.append(rise_rate); all_rec.append(rec_rate)
        if d["direction"] == "low":
            low_pd.append(peak_dist); low_dl.append(disp_words)
            low_rr.append(rise_rate); low_rec.append(rec_rate)
        else:
            high_pd.append(peak_dist); high_dl.append(disp_words)
            high_rr.append(rise_rate); high_rec.append(rec_rate)

    sm = lambda lst: float(np.mean(lst)) if lst else None
    return {
        "emo_mean": mean, "emo_std": std,
        "emo_avg_peak_dist": sm(all_pd), "emo_avg_disp_length": sm(all_dl),
        "emo_rise_rate": sm(all_rr), "emo_recovery_rate": sm(all_rec),
        "emo_low_peak_dist": sm(low_pd), "emo_low_disp_length": sm(low_dl),
        "emo_low_rise_rate": sm(low_rr), "emo_low_recovery_rate": sm(low_rec),
        "emo_high_peak_dist": sm(high_pd), "emo_high_disp_length": sm(high_dl),
        "emo_high_rise_rate": sm(high_rr), "emo_high_recovery_rate": sm(high_rec),
        "n_displacements": len(displacements),
        "n_low_displacements": len(low_pd),
        "n_high_displacements": len(high_pd),
    }


def compute_full_ued(arc_3d: np.ndarray, window_size: int = 10) -> dict:
    result = {}
    for i, dim in enumerate(["valence", "arousal", "dominance"]):
        m = compute_ued_metrics(arc_3d[:, i], window_size=window_size)
        if m:
            result.update({f"{dim}_{k}": v for k, v in m.items()})
    return result


def compute_descriptive_stats(arc_3d: np.ndarray, ratio: float = 0.2) -> dict:
    n = len(arc_3d)
    k = max(1, int(n * ratio))
    stats = {}
    for i, dim in enumerate(["valence", "arousal", "dominance"]):
        arc = arc_3d[:, i]
        first_k, last_k = float(arc[:k].mean()), float(arc[-k:].mean())
        nec = last_k - first_k
        stats[f"{dim}_nec"]          = nec
        stats[f"{dim}_first_mean"]   = first_k
        stats[f"{dim}_last_mean"]    = last_k
        stats[f"{dim}_happy_ending"] = bool(nec > 0)
    return stats


def process_dialogue(dlg: dict, lexicon: dict, tok_lang: str = "en") -> dict:
    """
    tok_lang: ngôn ngữ tokenizer — "en", "zh", "ja", "ko".

    Coverage strategy per language:
      EN  → lowercase tokenize → direct lookup
      ZH  → jieba segment → _expand_zh_coverage (sub-char boost)
      JA  → fugashi (surface + lemma) OR MFM fallback with lexicon
      KO  → KoNLPy POS-filtered morphemes OR eojeol + particle stripping
    """
    row = {"dialogue_id": dlg["dialogue_id"],
           "dataset": dlg["dataset"], "language": dlg["language"]}

    for speaker in ["client", "counselor"]:
        _, words = extract_speaker_texts(dlg, speaker)

        # Language-specific tokenization with lexicon-aware strategies
        if tok_lang == "ja":
            # Pass lexicon for MFM fallback when fugashi unavailable
            tokens = tokenize(words, tok_lang, _lexicon=lexicon)
        else:
            tokens = tokenize(words, tok_lang)

        # Post-tokenization coverage boost
        if tok_lang == "zh":
            tokens = _expand_zh_coverage(tokens, lexicon)

        coverage = lexicon_coverage(tokens, lexicon)
        row[f"{speaker}_n_tokens"]     = len(tokens)
        row[f"{speaker}_lex_coverage"] = round(coverage, 4)

        arc = None
        if len(tokens) >= CONFIG["min_tokens"]:
            arc, _ = compute_emotion_arc(tokens, lexicon,
                                         CONFIG["window_size"], CONFIG["step"])
        row[f"{speaker}_arc_length"] = len(arc) if arc is not None else 0

        if arc is not None and len(arc) >= 10:
            for k, v in compute_full_ued(arc, window_size=CONFIG["window_size"]).items():
                row[f"{speaker}_{k}"] = v
            for k, v in compute_descriptive_stats(arc).items():
                row[f"{speaker}_{k}"] = v

    # Variability ratio
    for dim in ["valence", "arousal", "dominance"]:
        c_std = row.get(f"client_{dim}_emo_std")
        t_std = row.get(f"counselor_{dim}_emo_std")
        if c_std and t_std and t_std > 0:
            row[f"{dim}_variability_ratio"] = round(c_std / t_std, 4)

    return row


# ─────────────────────────────────────────────
# PIPELINE PER DATASET
# ─────────────────────────────────────────────

def run_dataset(
    dataset_name: str,
    n: int,
    default_lexicon: dict,
    output_base: Path,
) -> pd.DataFrame | None:
    """Run Dim-C pipeline for one dataset. Returns DataFrame of results."""
    if dataset_name not in DATASET_REGISTRY:
        print(f"  [ERROR] Unknown dataset: {dataset_name}. Available: {list(DATASET_REGISTRY)}")
        return None

    info = DATASET_REGISTRY[dataset_name]
    input_path = REPO_ROOT / info["input_file"]

    if not input_path.exists():
        print(f"  [SKIP] Input file not found: {input_path}")
        return None

    # ── Chọn lexicon ──
    custom_lexicon_path = info.get("lexicon_path")
    if custom_lexicon_path:
        lex_path = Path(custom_lexicon_path)
        if not lex_path.exists():
            print(f"\n  [ERROR] {dataset_name}: Lexicon file missing.")
            print(f"          Expected: {lex_path}")
            print(f"          Tip: {info['note']}")
            return None
        scale          = info.get("lexicon_scale", "neg1_1")
        use_native_col = info.get("use_native_col", False)
        lexicon        = load_vad_lexicon(lex_path, scale=scale,
                                          use_native_col=use_native_col)
        col_label      = "native col" if use_native_col else "EN col"
        lexicon_label  = f"{lex_path.name} [{col_label}, scale={scale}]"
    else:
        lexicon        = default_lexicon
        lexicon_label  = "NRC-VAD v2.1 EN unigrams"

    # ── Chọn tokenizer ──
    tok_lang = info.get("tokenizer", "en")  # default EN

    approach_label = info.get("approach", "B" if info.get("en_ready", True) else "A")

    print(f"\n{'='*62}")
    print(f"  Dataset   : {dataset_name}")
    print(f"  Approach  : {'A — Native text + Native lexicon' if approach_label == 'A' else 'B — EN translation + EN lexicon'}")
    print(f"  Language  : {info['language']}")
    print(f"  Tokenizer : {tok_lang}")
    print(f"  Lexicon   : {lexicon_label}  ({len(lexicon):,} entries)")
    print(f"  Input     : {info['input_file']}")
    print(f"  Records   : {n}")
    if info.get("note"):
        print(f"  Note      : {info['note'][:90]}")
    print(f"{'='*62}")

    dialogues = load_canonical_jsonl(input_path, n=n)
    print(f"  Loaded {len(dialogues)} dialogues")

    results = []
    skipped = 0
    for dlg in dialogues:
        row = process_dialogue(dlg, lexicon, tok_lang=tok_lang)
        row["input_file"]   = info["input_file"]
        row["approach"]     = approach_label
        row["lexicon_used"] = lexicon_label
        row["tokenizer"]    = tok_lang
        results.append(row)
        if row["client_arc_length"] == 0:
            skipped += 1

    df = pd.DataFrame(results)

    # Save
    out_dir = output_base / dataset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"{dataset_name}_dimC_pilot.csv"
    df.to_csv(out_csv, index=False)

    # Quick summary
    valid_n = len(df) - skipped
    avg_cov = df["client_lex_coverage"].mean()
    he_col  = "client_valence_happy_ending"
    he_rate = df[he_col].dropna().mean() if he_col in df.columns else float("nan")

    mean_col = "client_valence_emo_mean"
    v_mean = df[mean_col].dropna().mean() if mean_col in df.columns else float("nan")

    print(f"  Processed: {valid_n}/{len(df)} (skipped {skipped} — too short)")
    print(f"  Lexicon coverage (client): {avg_cov:.1%}")
    print(f"  Valence emo_mean: {v_mean:+.4f}" if not np.isnan(v_mean) else "  Valence emo_mean: N/A")
    print(f"  Happy-ending (valence): {he_rate:.1%}" if not np.isnan(he_rate) else "  Happy-ending: N/A")
    print(f"  Saved: {out_csv}")

    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Dimension C — UED pipeline (multi-dataset)"
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dataset", nargs="+",
                     help="Dataset name(s): " + " ".join(DATASET_REGISTRY.keys()))
    grp.add_argument("--all", action="store_true",
                     help="Run all registered datasets")
    parser.add_argument("--n", type=int, default=CONFIG["default_n"],
                        help=f"Max records per dataset (default: {CONFIG['default_n']})")
    parser.add_argument("--output_dir", type=str,
                        default="data/_analysis/dim_c",
                        help="Output base directory (relative to repo root)")
    args = parser.parse_args()

    datasets_to_run = list(DATASET_REGISTRY.keys()) if args.all else args.dataset
    output_base     = REPO_ROOT / args.output_dir

    print(f"\nDim-C Pipeline — NRC-VAD v2.1 (EN lexicon)")
    print(f"Records per dataset: {args.n}")
    print(f"Output: {output_base}")
    print(f"Datasets: {datasets_to_run}")

    # Load lexicon once
    lexicon = load_vad_lexicon(LEXICON_EN_PATH)
    print(f"Lexicon loaded: {len(lexicon):,} entries")

    all_dfs = []
    for ds in datasets_to_run:
        df = run_dataset(ds, args.n, default_lexicon=lexicon, output_base=output_base)
        if df is not None:
            df["dataset_key"] = ds
            all_dfs.append(df)

    if not all_dfs:
        print("\nNo results.")
        return

    # Combined summary table
    combined = pd.concat(all_dfs, ignore_index=True)
    combined_path = output_base / f"all_dimC_pilot_n{args.n}.csv"
    combined.to_csv(combined_path, index=False)
    print(f"\nCombined CSV: {combined_path}")

    # Cross-dataset summary
    print("\n" + "="*70)
    print("  CROSS-DATASET SUMMARY (client valence, mean over valid dialogues)")
    print("="*70)
    key_cols = ["client_lex_coverage", "client_valence_emo_mean",
                "client_valence_emo_std", "client_valence_nec"]

    rows = []
    for ds in datasets_to_run:
        sub = combined[combined["dataset_key"] == ds]
        if sub.empty:
            continue
        row_d = {"dataset": ds,
                 "language": DATASET_REGISTRY[ds]["language"],
                 "approach": DATASET_REGISTRY[ds].get("approach", "B"),
                 "n_valid": int((sub["client_arc_length"] > 0).sum())}
        for col in key_cols:
            if col in sub.columns:
                row_d[col] = round(sub[col].dropna().mean(), 4)
        rows.append(row_d)

    summary_df = pd.DataFrame(rows)
    summary_path = output_base / f"summary_dimC_pilot_n{args.n}.csv"
    summary_df.to_csv(summary_path, index=False)
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {summary_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
