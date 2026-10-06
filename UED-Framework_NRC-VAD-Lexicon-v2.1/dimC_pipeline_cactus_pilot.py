"""
Dimension C — Emotional Trajectory Profiling Pipeline
UED Framework + NRC-VAD Lexicon v2.1

Pilot run: CACTUS dataset, first 20 records (EN, Approach A only for EN).

Usage:
    python dimC_pipeline_cactus_pilot.py

Output:
    results/dim_c/cactus_pilot_ued.csv
    results/dim_c/cactus_pilot_summary.txt
    results/dim_c/sanity_check_cactus.txt
"""

import json
import os
import re
import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS  (relative to this script's directory)
# ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPT_DIR.parent          # mind-eval/

LEXICON_EN_PATH = SCRIPT_DIR / "NRC-VAD-Lexicon-v2.1" / "Unigrams" / "unigrams-NRC-VAD-Lexicon-v2.1.txt"

CACTUS_DATA = REPO_ROOT / "data" / "cactus" / "test" / "interactions_200_canonical.jsonl"

OUTPUT_DIR  = REPO_ROOT / "data" / "cactus" / "results" / "dim_c"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CONFIG = {
    "window_size": 10,
    "step": 1,
    "min_tokens": 30,
    "pilot_n": 20,          # number of records for pilot run
}

# Reference values from Wang et al. (2025) "Feel the Difference" — CACTUS Synthetic
REFERENCE_CACTUS = {
    "valence_emo_mean":          0.2761,
    "valence_emo_std":           0.1480,
    "valence_emo_avg_peak_dist": 0.0779,
    "valence_emo_avg_disp_length": 4.2282,
    "valence_emo_rise_rate":     0.0332,
    "valence_emo_recovery_rate": 0.0325,
    # Client-specific rows from Table 8
    "valence_client_emo_mean":         0.2339,
    "valence_client_emo_std":          0.1518,
    "valence_client_emo_rise_rate":    0.0349,
    "valence_client_emo_recovery_rate": 0.0369,
}

# ─────────────────────────────────────────────
# STEP 1 — Load lexicon
# ─────────────────────────────────────────────

def load_vad_lexicon(filepath: Path) -> dict:
    """
    Load NRC-VAD-v2.1 unigrams lexicon.
    Format: term \\t valence \\t arousal \\t dominance  (header on line 1)
    Values are in [-1, 1].
    Returns: dict[str → (valence, arousal, dominance)]
    """
    lexicon = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # skip header
            parts = line.strip().split("\t")
            if len(parts) == 4:
                word = parts[0].lower()
                v, a, d = float(parts[1]), float(parts[2]), float(parts[3])
                lexicon[word] = (v, a, d)
    print(f"Loaded lexicon: {len(lexicon):,} entries from {filepath.name}")
    return lexicon


# ─────────────────────────────────────────────
# STEP 2 — Load & adapt cactus data
# ─────────────────────────────────────────────

def load_cactus(path: Path, n: int = None) -> list[dict]:
    """
    Load cactus canonical jsonl.
    Adapts to pipeline format:
      interaction_id → dialogue_id
      interaction (list of {role, content}) → turns (list of {role, text})
    """
    dialogues = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            turns = [
                {"role": t["role"], "text": t["content"]}
                for t in rec["interaction"]
            ]
            dialogues.append({
                "dialogue_id": rec["interaction_id"],
                "dataset": "cactus",
                "language": rec["metadata"].get("language", "en"),
                "turns": turns,
                # keep metadata for filtering / reporting
                "_attitude":  rec.get("extra", {}).get("attitude", "unknown"),
                "_technique": rec.get("extra", {}).get("cbt_technique", "unknown"),
            })
    if n is not None:
        dialogues = dialogues[:n]
    print(f"Loaded {len(dialogues)} cactus dialogues")
    return dialogues


# ─────────────────────────────────────────────
# STEP 3 — Extract speaker utterances
# ─────────────────────────────────────────────

def extract_speaker_texts(dialogue: dict, role: str = "client") -> tuple[list[str], str]:
    """Return (list_of_utterances, concatenated_word_sequence) for given role."""
    texts = [t["text"] for t in dialogue["turns"] if t["role"] == role]
    word_sequence = " ".join(texts)
    return texts, word_sequence


# ─────────────────────────────────────────────
# STEP 4 — Tokenisation (EN)
# ─────────────────────────────────────────────

def tokenize_en(text: str) -> list[str]:
    """
    Simple EN tokenizer: lowercase, strip punctuation/numbers, split on whitespace.
    Keeps stopwords (UED uses all words).
    No NLTK dependency for portability.
    """
    text = text.lower()
    # Remove punctuation and digits; keep apostrophes inside words (can't → can't)
    text = re.sub(r"[^a-z\s']", " ", text)
    # Collapse whitespace
    tokens = text.split()
    return tokens


# ─────────────────────────────────────────────
# STEP 5 — Emotion arc via rolling window
# ─────────────────────────────────────────────

def compute_emotion_arc(
    tokens: list[str],
    lexicon: dict,
    window_size: int = 10,
    step: int = 1,
) -> tuple[np.ndarray | None, list[int]]:
    """
    Sliding window over tokens.  Each window → mean(V, A, D) of lexicon-covered tokens.
    Returns arc shape (N, 3) and valid window indices.
    """
    arc = []
    valid_indices = []

    for i in range(0, len(tokens) - window_size + 1, step):
        window = tokens[i : i + window_size]
        scores = [lexicon[w] for w in window if w in lexicon]

        if len(scores) == 0:
            continue

        scores_arr = np.array(scores, dtype=float)
        mean_vad = scores_arr.mean(axis=0)   # shape (3,)
        arc.append(mean_vad)
        valid_indices.append(i)

    if len(arc) == 0:
        return None, []

    return np.array(arc), valid_indices


# ─────────────────────────────────────────────
# STEP 6 — UED metrics (per dimension)
# ─────────────────────────────────────────────

def compute_ued_metrics(arc_1d: np.ndarray) -> dict | None:
    """
    Compute all 14 UED metrics for one VAD dimension.
    arc_1d: shape (N,) — must have len >= 10.
    """
    if arc_1d is None or len(arc_1d) < 10:
        return None

    mean = float(np.mean(arc_1d))
    std  = float(np.std(arc_1d))

    home_low  = mean - std
    home_high = mean + std

    # ── Find displacements (contiguous runs outside home base) ──
    displacements = []
    current_disp  = None

    for t, val in enumerate(arc_1d):
        outside = val < home_low or val > home_high

        if outside:
            if current_disp is None:
                current_disp = {
                    "start":     t,
                    "values":    [val],
                    "direction": "low" if val < home_low else "high",
                }
            else:
                current_disp["values"].append(val)
        else:
            if current_disp is not None:
                current_disp["end"] = t - 1
                displacements.append(current_disp)
                current_disp = None

    if current_disp is not None:
        current_disp["end"] = len(arc_1d) - 1
        displacements.append(current_disp)

    # ── Aggregate per-displacement metrics ──
    all_peak_dist, all_disp_length, all_rise_rate, all_recovery_rate = [], [], [], []
    low_pk, low_dl, low_rr, low_rec = [], [], [], []
    high_pk, high_dl, high_rr, high_rec = [], [], [], []

    for disp in displacements:
        values = np.array(disp["values"])
        length = len(values)

        if disp["direction"] == "low":
            peak_val = float(np.min(values))
            peak_idx = int(np.argmin(values))
        else:
            peak_val = float(np.max(values))
            peak_idx = int(np.argmax(values))

        peak_dist = abs(peak_val - mean)
        rise_dur  = peak_idx + 1
        rec_dur   = length - peak_idx

        rise_rate = peak_dist / rise_dur if rise_dur > 0 else 0.0
        rec_rate  = peak_dist / rec_dur  if rec_dur  > 0 else 0.0

        all_peak_dist.append(peak_dist)
        all_disp_length.append(length)
        all_rise_rate.append(rise_rate)
        all_recovery_rate.append(rec_rate)

        if disp["direction"] == "low":
            low_pk.append(peak_dist);  low_dl.append(length)
            low_rr.append(rise_rate);  low_rec.append(rec_rate)
        else:
            high_pk.append(peak_dist); high_dl.append(length)
            high_rr.append(rise_rate); high_rec.append(rec_rate)

    def safe_mean(lst):
        return float(np.mean(lst)) if len(lst) > 0 else None

    return {
        "emo_mean":             mean,
        "emo_std":              std,
        "emo_avg_peak_dist":    safe_mean(all_peak_dist),
        "emo_avg_disp_length":  safe_mean(all_disp_length),
        "emo_rise_rate":        safe_mean(all_rise_rate),
        "emo_recovery_rate":    safe_mean(all_recovery_rate),
        "emo_low_peak_dist":    safe_mean(low_pk),
        "emo_low_disp_length":  safe_mean(low_dl),
        "emo_low_rise_rate":    safe_mean(low_rr),
        "emo_low_recovery_rate": safe_mean(low_rec),
        "emo_high_peak_dist":   safe_mean(high_pk),
        "emo_high_disp_length": safe_mean(high_dl),
        "emo_high_rise_rate":   safe_mean(high_rr),
        "emo_high_recovery_rate": safe_mean(high_rec),
        "n_displacements":      len(displacements),
        "n_low_displacements":  len(low_pk),
        "n_high_displacements": len(high_pk),
    }


def compute_full_ued(arc_3d: np.ndarray) -> dict:
    """Compute UED metrics for all 3 VAD dimensions. Returns flat dict with prefixed keys."""
    all_metrics = {}
    for i, dim in enumerate(["valence", "arousal", "dominance"]):
        metrics = compute_ued_metrics(arc_3d[:, i])
        if metrics is None:
            continue
        for key, val in metrics.items():
            all_metrics[f"{dim}_{key}"] = val
    return all_metrics


# ─────────────────────────────────────────────
# STEP 7 — Descriptive stats (NEC, happy-ending)
# ─────────────────────────────────────────────

def compute_descriptive_stats(arc_3d: np.ndarray, ratio: float = 0.2) -> dict:
    """Net Emotional Change (NEC) and happy-ending indicator."""
    n = len(arc_3d)
    k = max(1, int(n * ratio))
    stats = {}
    for i, dim in enumerate(["valence", "arousal", "dominance"]):
        arc = arc_3d[:, i]
        first_k  = float(arc[:k].mean())
        last_k   = float(arc[-k:].mean())
        nec      = last_k - first_k
        stats[f"{dim}_nec"]          = nec
        stats[f"{dim}_first_mean"]   = first_k
        stats[f"{dim}_last_mean"]    = last_k
        stats[f"{dim}_happy_ending"] = bool(nec > 0)
    return stats


# ─────────────────────────────────────────────
# STEP 8 — Lexicon coverage helper
# ─────────────────────────────────────────────

def lexicon_coverage(tokens: list[str], lexicon: dict) -> float:
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in lexicon) / len(tokens)


# ─────────────────────────────────────────────
# STEP 9 — Main pipeline per dialogue
# ─────────────────────────────────────────────

def process_dialogue(dlg: dict, lexicon: dict) -> dict:
    """Run full DimC pipeline for one cactus dialogue (EN, Approach A)."""
    row = {
        "dialogue_id": dlg["dialogue_id"],
        "dataset":     dlg["dataset"],
        "language":    dlg["language"],
        "attitude":    dlg.get("_attitude", "unknown"),
        "technique":   dlg.get("_technique", "unknown"),
    }

    # ── Client ──
    _, client_words    = extract_speaker_texts(dlg, "client")
    tokens_client      = tokenize_en(client_words)
    coverage_client    = lexicon_coverage(tokens_client, lexicon)

    row["client_n_tokens"]    = len(tokens_client)
    row["client_lex_coverage"] = round(coverage_client, 4)

    arc_client = None
    if len(tokens_client) >= CONFIG["min_tokens"]:
        arc_client, _ = compute_emotion_arc(
            tokens_client, lexicon, CONFIG["window_size"], CONFIG["step"]
        )

    row["client_arc_length"] = len(arc_client) if arc_client is not None else 0

    if arc_client is not None and len(arc_client) >= 10:
        ued = compute_full_ued(arc_client)
        desc = compute_descriptive_stats(arc_client)
        for k, v in ued.items():
            row[f"client_{k}"] = v
        for k, v in desc.items():
            row[f"client_{k}"] = v

    # ── Counselor ──
    _, counselor_words  = extract_speaker_texts(dlg, "counselor")
    tokens_counselor    = tokenize_en(counselor_words)
    coverage_counselor  = lexicon_coverage(tokens_counselor, lexicon)

    row["counselor_n_tokens"]     = len(tokens_counselor)
    row["counselor_lex_coverage"] = round(coverage_counselor, 4)

    arc_counselor = None
    if len(tokens_counselor) >= CONFIG["min_tokens"]:
        arc_counselor, _ = compute_emotion_arc(
            tokens_counselor, lexicon, CONFIG["window_size"], CONFIG["step"]
        )

    row["counselor_arc_length"] = len(arc_counselor) if arc_counselor is not None else 0

    if arc_counselor is not None and len(arc_counselor) >= 10:
        ued_c = compute_full_ued(arc_counselor)
        for k, v in ued_c.items():
            row[f"counselor_{k}"] = v

    # ── Variability ratio (client / counselor) ──
    if arc_client is not None and arc_counselor is not None:
        for dim in ["valence", "arousal", "dominance"]:
            c_std = row.get(f"client_{dim}_emo_std")
            t_std = row.get(f"counselor_{dim}_emo_std")
            if c_std and t_std and t_std > 0:
                row[f"{dim}_variability_ratio"] = round(c_std / t_std, 4)

    return row


# ─────────────────────────────────────────────
# STEP 10 — Sanity check vs. Feel the Difference
# ─────────────────────────────────────────────

def sanity_check(df: pd.DataFrame) -> str:
    """
    Compare pilot means against Wang et al. (2025) reference values.
    Tolerance: ±20% (pilot uses only 20 records; paper uses full dataset).
    """
    lines = ["=== SANITY CHECK: CACTUS pilot vs. 'Feel the Difference' (Wang et al. 2025) ===",
             f"  Pilot size: {len(df)} dialogues",
             "  NOTE: Wang et al. used NRC-VAD v1 (scale 0-1); this run uses v2.1 (scale -1 to +1).",
             "  Direct numeric comparison will show large diffs — focus on direction & ranking, not absolute values.",
             "  Tolerance: +-20% (for reference only)",
             ""]

    tolerance = 0.20

    for metric_key, ref_val in REFERENCE_CACTUS.items():
        # Map reference key to column name
        col_map = {
            "valence_emo_mean":               "client_valence_emo_mean",
            "valence_emo_std":                "client_valence_emo_std",
            "valence_emo_avg_peak_dist":      "client_valence_emo_avg_peak_dist",
            "valence_emo_avg_disp_length":    "client_valence_emo_avg_disp_length",
            "valence_emo_rise_rate":          "client_valence_emo_rise_rate",
            "valence_emo_recovery_rate":      "client_valence_emo_recovery_rate",
            "valence_client_emo_mean":        "client_valence_emo_mean",
            "valence_client_emo_std":         "client_valence_emo_std",
            "valence_client_emo_rise_rate":   "client_valence_emo_rise_rate",
            "valence_client_emo_recovery_rate": "client_valence_emo_recovery_rate",
        }
        col = col_map.get(metric_key)
        if col and col in df.columns:
            your_val = df[col].mean()
            diff_pct = abs(your_val - ref_val) / abs(ref_val) * 100 if ref_val != 0 else float("inf")
            status = "[OK]" if diff_pct <= tolerance * 100 else "[CHECK]"
            lines.append(
                f"  {metric_key:<40} yours={your_val:+.4f}  ref={ref_val:+.4f}  "
                f"diff={diff_pct:.1f}%  {status}"
            )

    return "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  DimC Pipeline — CACTUS Pilot (20 records)")
    print("=" * 60)

    # 1. Load lexicon
    lexicon = load_vad_lexicon(LEXICON_EN_PATH)

    # 2. Load data
    dialogues = load_cactus(CACTUS_DATA, n=CONFIG["pilot_n"])

    # 3. Process each dialogue
    results = []
    skipped = 0
    for dlg in dialogues:
        row = process_dialogue(dlg, lexicon)
        results.append(row)
        if row["client_arc_length"] == 0:
            skipped += 1
            print(f"  [SKIP] {dlg['dialogue_id']} — too short "
                  f"({row['client_n_tokens']} tokens)")

    df = pd.DataFrame(results)

    # 4. Save per-dialogue CSV
    out_csv = OUTPUT_DIR / "cactus_pilot_ued.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # 5. Summary stats
    summary_lines = ["=== PILOT SUMMARY ===",
                     f"  Total dialogues:  {len(df)}",
                     f"  Skipped (too short): {skipped}",
                     f"  Processed (arc valid): {len(df) - skipped}",
                     ""]

    metric_cols = [c for c in df.columns if c.startswith("client_valence_emo_") and "happy_ending" not in c]
    if metric_cols:
        summary_lines.append("  Client valence UED metrics (mean over valid dialogues):")
        for col in sorted(metric_cols):
            vals = df[col].dropna()
            if len(vals) > 0:
                summary_lines.append(f"    {col:<50} {vals.mean():+.4f}  (n={len(vals)})")

    summary_lines.append("")
    summary_lines.append("  Lexicon coverage:")
    summary_lines.append(f"    Client   — mean: {df['client_lex_coverage'].mean():.2%}")
    summary_lines.append(f"    Counselor — mean: {df['counselor_lex_coverage'].mean():.2%}")

    summary_lines.append("")
    summary_lines.append("  Happy-ending rates (client valence NEC > 0):")
    he_col = "client_valence_happy_ending"
    if he_col in df.columns:
        rate = df[he_col].dropna().mean()
        summary_lines.append(f"    Valence happy-ending: {rate:.1%}")

    summary_txt = "\n".join(summary_lines)
    out_summary = OUTPUT_DIR / "cactus_pilot_summary.txt"
    with open(out_summary, "w", encoding="utf-8") as f:
        f.write(summary_txt)
    print(f"Saved: {out_summary}")
    print("\n" + summary_txt)

    # 6. Sanity check
    sanity_txt = sanity_check(df)
    out_sanity = OUTPUT_DIR / "sanity_check_cactus.txt"
    with open(out_sanity, "w", encoding="utf-8") as f:
        f.write(sanity_txt)
    print(f"\nSaved: {out_sanity}")
    print("\n" + sanity_txt)

    # 7. Print a compact per-record table
    print("\n=== PER-RECORD OVERVIEW ===")
    disp_cols = ["dialogue_id", "attitude", "client_n_tokens",
                 "client_lex_coverage", "client_arc_length",
                 "client_valence_emo_mean", "client_valence_emo_std",
                 "client_valence_nec"]
    available = [c for c in disp_cols if c in df.columns]
    print(df[available].to_string(index=False))

    print(f"\nDone. All outputs in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
