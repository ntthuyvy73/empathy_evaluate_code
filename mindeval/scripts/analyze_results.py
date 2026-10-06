"""
Phân tích toàn diện kết quả MindEval (Dim-A) trên 6 dataset × 3 setting (S1/S2/S3).

Thực hiện Phase 5 (phân tích ảnh hưởng ngôn ngữ) và Phase 6 (ranking & báo cáo).

Chạy:
    python -m mindeval.scripts.analyze_results [--output_dir PATH]

Output mặc định: data/_analysis/mind_eval/
  tables/
    summary_raw_means.csv        — mean score mỗi dataset × setting × metric
    ranking_S1.csv               — z-score + mean-rank theo S1
    ranking_S3.csv               — z-score + mean-rank theo S3
    language_effect.csv          — Spearman/Kendall, MAD, t-test giữa các cặp setting
    discriminative_power.csv     — std of dataset means (spread) per metric per setting
  charts/
    01_overall_heatmap.png       — heatmap tổng quát Overall score
    02_per_metric_heatmap_S1.png — heatmap 5 metric theo S1
    03_per_metric_heatmap_S3.png — heatmap 5 metric theo S3
    04_language_effect_S1_S3.png — scatter S1 vs S3 (translation effect)
    05_language_effect_S2_S3.png — scatter S2 vs S3 (judge-lang effect)
    06_boxplot_settings.png      — boxplot phân phối Overall score
    07_strength_profile_S1.png   — radar chart z-score theo S1
    08_ranking_bar_S1.png        — mean-rank bar chart theo S1
    09_spearman_heatmap.png      — Spearman corr matrix giữa 3 setting
    10_criterion_comparison.png  — grouped bar: per metric per dataset (S1 vs S3)
  report.md                      — báo cáo tổng hợp markdown
"""

import json
import sys
import argparse
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Force UTF-8 for stdout/stderr so Vietnamese/CJK chars print correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)

# ─────────────────────── CONFIG ────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[2] / "data"

DATASETS_META = {
    "cactus":      {"language": "en", "origin_type": "simulated", "label": "cactus"},
    "Psy-Insight": {"language": "en", "origin_type": "human",     "label": "PsyInsight"},
    "simpsydial":  {"language": "zh", "origin_type": "simulated", "label": "simpsydial"},
    "PsyDial":     {"language": "zh", "origin_type": "human",     "label": "PsyDial"},
    "SoulChat":    {"language": "zh", "origin_type": "simulated", "label": "SoulChat"},
    "KMI":         {"language": "ko", "origin_type": "human",     "label": "KMI"},
    "AnnoMI":      {"language": "en", "origin_type": "human",     "label": "AnnoMI"},
    "CPsyCoun":    {"language": "zh", "origin_type": "human",     "label": "CPsyCoun"},
    "KokoroChat":  {"language": "ja", "origin_type": "human",     "label": "KokoroChat"},
    "smile":       {"language": "zh", "origin_type": "simulated", "label": "SMILE"},
    "ESConv":      {"language": "en", "origin_type": "human",     "label": "ESConv"},
}

METRICS = [
    "Clinical Accuracy & Competence",
    "Ethical & Professional Conduct",
    "Assessment & Response",
    "Therapeutic Relationship & Alliance",
    "AI-Specific Communication Quality",
]
OVERALL_KEY = "Overall score"
ALL_METRICS = METRICS + [OVERALL_KEY]

METRIC_SHORT = {
    "Clinical Accuracy & Competence":      "Clinical",
    "Ethical & Professional Conduct":       "Ethics",
    "Assessment & Response":               "Assessment",
    "Therapeutic Relationship & Alliance": "Alliance",
    "AI-Specific Communication Quality":   "AI-Comm",
    "Overall score":                       "Overall",
}

SETTINGS = ["S1", "S2", "S3"]

SETTING_LABELS = {
    "S1": "S1 (EN↔EN)",
    "S2": "S2 (NL↔NL)",
    "S3": "S3 (NL→EN)",
}

COLORS = {
    "S1": "#2196F3",
    "S2": "#FF9800",
    "S3": "#4CAF50",
}

DATASET_ORDER = [
    "cactus", "Psy-Insight", "simpsydial", "PsyDial", "SoulChat", "KMI",
    "AnnoMI", "CPsyCoun", "KokoroChat", "smile", "ESConv",
]

# ─────────────────────── DATA LOADING ──────────────────────────────────────

def load_judgments(
    dataset: str,
    setting: str,
    judge_name: Optional[str] = None,
) -> Optional[List[Dict]]:
    """Load judgment file for (dataset, setting).

    File naming convention: {dataset}_{setting}_{judge_name}_judgments.jsonl
      e.g. KMI_S1_gpt_judgments.jsonl, simpsydial_S3_qwen_judgments.jsonl
    Falls back to legacy {setting}_{judge_name}_judgments.jsonl and
    {setting}_judgments.jsonl for files generated before this convention.
    """
    effective_judge = judge_name or "gpt"
    results_dir = BASE_DIR / dataset / "results" / "mind_eval"
    # Primary: new convention <dataset>_<setting>_<judge>_judgments.jsonl
    fname = f"{dataset}_{setting}_{effective_judge}_judgments.jsonl"
    path = results_dir / fname
    if not path.exists():
        # Fallback 1: old convention without dataset prefix
        path = results_dir / f"{setting}_{effective_judge}_judgments.jsonl"
    if not path.exists():
        # Fallback 2: legacy files without judge suffix
        path = results_dir / f"{setting}_judgments.jsonl"
    if not path.exists():
        return None
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records if records else None


def build_long_df(judge_name: Optional[str] = None) -> pd.DataFrame:
    """
    Load all results into a long-form DataFrame.

    judge_name: if given, loads named-judge files (<S>_<judge>_judgments.jsonl).
                Default (None) loads standard files (<S>_judgments.jsonl).

    EN datasets (cactus, Psy-Insight): S1 = S3 (same dialogue + same EN judge).
    We load S1 once and replicate it for both S1 and S3 labels.
    S2 does NOT exist for EN datasets.
    """
    rows = []
    for ds in DATASET_ORDER:
        is_en = DATASETS_META[ds]["language"] == "en"
        settings_to_load = SETTINGS if not is_en else ["S1"]

        for setting in settings_to_load:
            records = load_judgments(ds, setting, judge_name=judge_name)
            if records is None:
                continue

            target_settings = ["S1", "S3"] if is_en else [setting]

            for ts in target_settings:
                for idx, rec in enumerate(records):
                    pj = rec.get("parsed_judgment", {})
                    iid = rec.get("interaction_id", f"{ds}_{ts}_{idx}")
                    row = {
                        "dataset": ds,
                        "dataset_label": DATASETS_META[ds]["label"],
                        "language": DATASETS_META[ds]["language"],
                        "origin_type": DATASETS_META[ds]["origin_type"],
                        "setting": ts,
                        "interaction_id": iid,
                        "record_idx": idx,
                    }
                    for m in ALL_METRICS:
                        row[m] = pj.get(m, np.nan)
                    rows.append(row)
    return pd.DataFrame(rows)


# ─────────────────────── SUMMARY TABLES ────────────────────────────────────

def compute_raw_means(df: pd.DataFrame) -> pd.DataFrame:
    """Mean ± std per dataset × setting × metric."""
    grouped = df.groupby(["dataset", "setting"])[ALL_METRICS]
    mean_df = grouped.mean().reset_index()
    std_df  = grouped.std().reset_index()
    return mean_df, std_df


def pivot_overall(mean_df: pd.DataFrame) -> pd.DataFrame:
    """
    Wide table: rows = datasets, cols = settings, value = Overall mean.
    EN datasets have NaN for S2 (not applicable — no separate NL judge).
    """
    piv = mean_df.pivot(index="dataset", columns="setting", values=OVERALL_KEY).reindex(
        index=DATASET_ORDER
    )
    # Force S2 = NaN for EN datasets
    for ds in DATASET_ORDER:
        if DATASETS_META[ds]["language"] == "en" and "S2" in piv.columns:
            piv.loc[ds, "S2"] = np.nan
    return piv


def compute_z_scores(mean_df: pd.DataFrame, setting: str) -> pd.DataFrame:
    """
    Z-score per metric across 6 datasets for a given setting.
    Returns DataFrame with index=dataset, columns=metrics + 'mean_rank'.
    """
    s_df = mean_df[mean_df["setting"] == setting].set_index("dataset")
    z_df = s_df[METRICS].apply(lambda col: stats.zscore(col, nan_policy="omit"), axis=0)
    # Mean-rank: rank each dataset per metric (descending), then average ranks
    rank_df = s_df[METRICS].rank(ascending=False, method="average")
    z_df["mean_rank"] = rank_df.mean(axis=1)
    z_df = z_df.reindex(DATASET_ORDER)
    return z_df


# ─────────────────────── LANGUAGE EFFECT ANALYSIS ─────────────────────────

def language_effect_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phân rã ảnh hưởng ngôn ngữ cho từng dataset có đủ dữ liệu.

    Cặp so sánh:
      S3 vs S2  → judge-language effect   (same NL dialogue, EN vs NL judge)
      S1 vs S3  → translation effect      (same EN judge, EN vs NL dialogue)
      S1 vs S2  → combined effect

    Metrics: Spearman r, Kendall tau, MAD, paired t-test p-value.
    Only datasets with both settings present are included.
    """
    results = []
    pairs = [
        ("S1", "S3", "translation_effect",  "S1 vs S3 (Translation)"),
        ("S2", "S3", "judge_lang_effect",    "S2 vs S3 (Judge Language)"),
        ("S1", "S2", "combined_effect",      "S1 vs S2 (Combined)"),
    ]

    for ds in DATASET_ORDER:
        # EN datasets: S1=S2=S3 by definition — no language effect to measure
        if DATASETS_META[ds]["language"] == "en":
            continue

        ds_df = df[df["dataset"] == ds]
        available_settings = ds_df["setting"].unique()

        for sa, sb, effect_type, effect_label in pairs:
            if sa not in available_settings or sb not in available_settings:
                continue
            a_df = ds_df[ds_df["setting"] == sa].sort_values("record_idx")
            b_df = ds_df[ds_df["setting"] == sb].sort_values("record_idx")

            min_len = min(len(a_df), len(b_df))
            if min_len < 3:
                continue

            a_overall = a_df[OVERALL_KEY].values[:min_len]
            b_overall = b_df[OVERALL_KEY].values[:min_len]

            spearman_r, spearman_p = stats.spearmanr(a_overall, b_overall)
            kendall_tau, kendall_p  = stats.kendalltau(a_overall, b_overall)
            pearson_r, pearson_p    = stats.pearsonr(a_overall, b_overall)
            mad = float(np.mean(np.abs(a_overall - b_overall)))
            mean_delta = float(np.mean(a_overall - b_overall))

            try:
                tstat, tpval = stats.ttest_rel(a_overall, b_overall)
            except Exception:
                tstat, tpval = np.nan, np.nan

            results.append({
                "dataset":      ds,
                "language":     DATASETS_META[ds]["language"],
                "comparison":   effect_label,
                "effect_type":  effect_type,
                "setting_A":    sa,
                "setting_B":    sb,
                "n":            min_len,
                "mean_A":       float(a_overall.mean()),
                "mean_B":       float(b_overall.mean()),
                "mean_delta (A-B)": mean_delta,
                "MAD":          mad,
                "Pearson_r":    float(pearson_r),
                "Spearman_r":   float(spearman_r),
                "Spearman_p":   float(spearman_p),
                "Kendall_tau":  float(kendall_tau),
                "Kendall_p":    float(kendall_p),
                "paired_t":     float(tstat) if not np.isnan(tstat) else None,
                "paired_p":     float(tpval) if not np.isnan(tpval) else None,
                "sig_diff":     bool(tpval < 0.05) if not np.isnan(tpval) else None,
            })

    return pd.DataFrame(results)


def compute_discriminative_power(mean_df: pd.DataFrame) -> pd.DataFrame:
    """Std of dataset means per metric per setting (higher = more spread = more discriminative)."""
    rows = []
    for setting in SETTINGS:
        s_df = mean_df[mean_df["setting"] == setting]
        if s_df.empty:
            continue
        row = {"setting": setting}
        for m in ALL_METRICS:
            row[m] = float(s_df[m].std())
        rows.append(row)
    return pd.DataFrame(rows)


# ─────────────────────── KMI TRANSLATION COMPARISON ────────────────────────

def load_kmi_translation_comparison() -> Optional[dict]:
    """
    Load S1-utt, S1-llm, S2-ko judgment files for KMI.
    Returns dict with keys 's1_utt', 's1_llm', 's2_ko' or None if any file is missing.
    """
    paths = {
        "s1_utt": BASE_DIR / "KMI" / "results" / "mind_eval" / "S1_gpt_judgments.jsonl",
        "s1_llm": BASE_DIR / "KMI" / "results" / "mind_eval" / "S1_ko_translated_gpt_judgments.jsonl",
        "s2_ko":  BASE_DIR / "KMI" / "results" / "mind_eval" / "S2_gpt_judgments.jsonl",
    }
    result = {}
    for key, path in paths.items():
        if not path.exists():
            return None
        recs = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
        result[key] = recs
    return result


def compute_kmi_translation_means(kmi_data: dict) -> pd.DataFrame:
    """Mean scores per condition (S1-utt, S1-llm, S2-ko) × metric."""
    labels = {
        "s1_utt": "S1-utt\n(utterance_en)",
        "s1_llm": "S1-llm\n(GPT-5.1 dịch KO)",
        "s2_ko":  "S2-ko\n(KO gốc)",
    }
    rows = []
    for key, recs in kmi_data.items():
        row = {"condition": labels[key], "condition_key": key, "n": len(recs)}
        for m in ALL_METRICS:
            vals = [r["parsed_judgment"].get(m, np.nan) for r in recs]
            row[m] = float(np.nanmean(vals))
        rows.append(row)
    return pd.DataFrame(rows)


# ─────────────────────── JUDGE COMPARISON ───────────────────────────────────

def load_judgments_for_judge(judge_name: str) -> Optional[List[Dict]]:
    """
    Load named-judge files for all datasets × all applicable settings.
    File pattern: data/<ds>/results/mind_eval/<ds>_<setting>_<judge_name>_judgments.jsonl
    Falls back to legacy <setting>_<judge_name>_judgments.jsonl if new name not found.
    EN datasets: only S1 (S3 is a copy; S2 does not exist).
    Returns list of dicts {dataset, setting, judge, records}, or None if none found.
    """
    results = []
    for ds in DATASET_ORDER:
        is_en = DATASETS_META[ds]["language"] == "en"
        settings_to_check = ["S1"] if is_en else SETTINGS
        for setting in settings_to_check:
            # Primary: new convention <dataset>_<setting>_<judge>_judgments.jsonl
            path = (BASE_DIR / ds / "results" / "mind_eval"
                    / f"{ds}_{setting}_{judge_name}_judgments.jsonl")
            if not path.exists():
                # Fallback: old convention without dataset prefix
                path = (BASE_DIR / ds / "results" / "mind_eval"
                        / f"{setting}_{judge_name}_judgments.jsonl")
            if not path.exists():
                continue
            recs = []
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        recs.append(json.loads(line))
            if recs:
                results.append({
                    "dataset": ds,
                    "setting": setting,
                    "judge": judge_name,
                    "records": recs,
                })
    return results if results else None


def build_judge_comparison_df(
    default_mean_df: pd.DataFrame,
    named_judge_data: List[Dict],
    judge_name: str,
) -> pd.DataFrame:
    """
    Compare default judge (GPT) vs named judge per dataset × setting × metric.
    default_mean_df: mean_df from build_long_df() (standard judge, all settings).
    named_judge_data: output of load_judgments_for_judge().
    """
    rows = []
    gpt_means = default_mean_df.set_index(["dataset", "setting"])

    for entry in named_judge_data:
        ds      = entry["dataset"]
        setting = entry["setting"]
        recs    = entry["records"]

        # Replicate EN S1 → S3 for symmetry (same as default judge logic)
        target_settings = ["S1", "S3"] if DATASETS_META[ds]["language"] == "en" else [setting]

        for ts in target_settings:
            for m in ALL_METRICS:
                key = (ds, ts)
                gpt_mean = (gpt_means.loc[key, m]
                            if key in gpt_means.index else np.nan)
                alt_vals = [r["parsed_judgment"].get(m, np.nan) for r in recs]
                alt_mean = float(np.nanmean(alt_vals))
                rows.append({
                    "dataset":       ds,
                    "setting":       ts,
                    "metric":        m,
                    "metric_short":  METRIC_SHORT[m],
                    "gpt_mean":      gpt_mean,
                    f"{judge_name}_mean": alt_mean,
                    "delta":         alt_mean - gpt_mean,
                })
    return pd.DataFrame(rows)


# ─────────────────────── CHARTS ────────────────────────────────────────────

def fig_overall_heatmap(mean_df: pd.DataFrame, out_dir: Path):
    """Chart 01: Heatmap Overall score — datasets × settings. NaN cells = N/A."""
    pivot = pivot_overall(mean_df).astype(float)
    mask = pivot.isna()  # mask N/A cells (S2 for EN datasets)

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        pivot,
        annot=True, fmt=".2f",
        cmap="YlOrRd", vmin=1, vmax=6,
        mask=mask,
        ax=ax, linewidths=0.5,
        cbar_kws={"label": "Overall score (1-6)"},
    )
    # Label masked cells with "-"
    for r, ds in enumerate(pivot.index):
        for c, col in enumerate(pivot.columns):
            if mask.iloc[r, c]:
                ax.text(c + 0.5, r + 0.5, "-", ha="center", va="center",
                        fontsize=12, color="grey")
    ax.set_title("Overall Score Heatmap\n(MindEval Dim-A, N=20/cell)", fontsize=12, pad=10)
    ax.set_xlabel("Setting", fontsize=10)
    ax.set_ylabel("Dataset", fontsize=10)
    ax.set_xticklabels([SETTING_LABELS.get(c, c) for c in pivot.columns], rotation=0)
    plt.tight_layout()
    plt.savefig(out_dir / "01_overall_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_per_metric_heatmap(mean_df: pd.DataFrame, setting: str, chart_num: str, out_dir: Path):
    """Charts 02-03: Heatmap 5 metrics for a given setting."""
    s_df = mean_df[mean_df["setting"] == setting].set_index("dataset").reindex(DATASET_ORDER)
    data = s_df[METRICS].rename(columns=METRIC_SHORT).astype(float)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.heatmap(
        data,
        annot=True, fmt=".2f",
        cmap="YlOrRd", vmin=1, vmax=6,
        ax=ax, linewidths=0.5,
        cbar_kws={"label": "Mean score (1–6)"},
    )
    ax.set_title(
        f"Per-Metric Score Heatmap — {SETTING_LABELS[setting]}\n(N=20/cell)",
        fontsize=12, pad=10
    )
    ax.set_xlabel("Metric", fontsize=10)
    ax.set_ylabel("Dataset", fontsize=10)
    plt.tight_layout()
    plt.savefig(out_dir / f"{chart_num}_per_metric_heatmap_{setting}.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_language_effect_scatter(df: pd.DataFrame, sa: str, sb: str,
                                 chart_num: str, title_suffix: str, out_dir: Path):
    """Charts 04-05: Scatter setting A vs setting B, per metric, coloured by dataset."""
    non_en_datasets = [d for d in DATASET_ORDER if DATASETS_META[d]["language"] != "en"]
    available = []
    for ds in non_en_datasets:
        ds_df = df[df["dataset"] == ds]
        if sa in ds_df["setting"].values and sb in ds_df["setting"].values:
            available.append(ds)

    if not available:
        return

    palette = sns.color_palette("tab10", len(available))
    ds_colors = {ds: palette[i] for i, ds in enumerate(available)}

    fig, axes = plt.subplots(1, len(METRICS), figsize=(4 * len(METRICS), 4), sharey=False)

    for ax, metric in zip(axes, METRICS):
        for ds in available:
            ds_df = df[df["dataset"] == ds]
            a_vals = ds_df[ds_df["setting"] == sa][metric].values
            b_vals = ds_df[ds_df["setting"] == sb][metric].values
            n = min(len(a_vals), len(b_vals))
            ax.scatter(a_vals[:n], b_vals[:n], alpha=0.5, s=20,
                       color=ds_colors[ds], label=ds)

        lo, hi = 1, 6
        ax.plot([lo, hi], [lo, hi], "r--", lw=1, alpha=0.7)
        ax.set_xlim(lo - 0.2, hi + 0.2)
        ax.set_ylim(lo - 0.2, hi + 0.2)
        ax.set_xlabel(SETTING_LABELS[sa], fontsize=8)
        ax.set_ylabel(SETTING_LABELS[sb], fontsize=8)
        ax.set_title(METRIC_SHORT[metric], fontsize=9)
        ax.set_aspect("equal")

    handles = [mpatches.Patch(color=ds_colors[ds], label=ds) for ds in available]
    fig.legend(handles=handles, loc="lower center", ncol=len(available),
               bbox_to_anchor=(0.5, -0.05), fontsize=8)
    fig.suptitle(
        f"Language Effect: {SETTING_LABELS[sa]} vs {SETTING_LABELS[sb]}\n{title_suffix}",
        fontsize=11, y=1.01
    )
    plt.tight_layout()
    plt.savefig(out_dir / f"{chart_num}_language_effect_{sa}_{sb}.png",
                dpi=150, bbox_inches="tight")
    plt.close()


def fig_boxplot_settings(df: pd.DataFrame, out_dir: Path):
    """Chart 06: Boxplot Overall score per dataset × setting."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharey=True)
    axes = axes.flatten()

    for ax, ds in zip(axes, DATASET_ORDER):
        ds_df = df[df["dataset"] == ds]
        data_list, labels, palette = [], [], []
        for setting in SETTINGS:
            s_data = ds_df[ds_df["setting"] == setting][OVERALL_KEY].dropna()
            if len(s_data):
                data_list.append(s_data.values)
                labels.append(SETTING_LABELS[setting])
                palette.append(COLORS[setting])

        bp = ax.boxplot(data_list, tick_labels=labels, patch_artist=True, widths=0.5)
        for patch, color in zip(bp["boxes"], palette):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.set_ylim(0.5, 6.5)
        ax.set_title(ds, fontsize=10, fontweight="bold")
        ax.set_ylabel("Overall Score (1–6)" if ax == axes[0] or ax == axes[3] else "")
        ax.tick_params(axis="x", labelsize=7)

    fig.suptitle("Overall Score Distribution by Dataset and Setting (N=20)", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_dir / "06_boxplot_settings.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_radar_strength_profile(mean_df: pd.DataFrame, setting: str, out_dir: Path):
    """Chart 07: Radar chart z-score strength profile per dataset."""
    s_df = mean_df[mean_df["setting"] == setting].set_index("dataset").reindex(DATASET_ORDER)
    metrics_data = s_df[METRICS].astype(float)

    z_scores = metrics_data.apply(lambda col: stats.zscore(col, nan_policy="omit"), axis=0)
    labels = [METRIC_SHORT[m] for m in METRICS]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # close polygon

    palette = sns.color_palette("tab10", len(DATASET_ORDER))

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, (ds, row) in enumerate(z_scores.iterrows()):
        if row.isnull().all():
            continue
        values = row.tolist() + [row.iloc[0]]
        ax.plot(angles, values, label=DATASETS_META[ds]["label"],
                color=palette[i], linewidth=2)
        ax.fill(angles, values, alpha=0.08, color=palette[i])

    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=9)
    ax.set_ylim(-2.5, 2.5)
    ax.set_yticks([-2, -1, 0, 1, 2])
    ax.set_yticklabels(["-2", "-1", "0", "+1", "+2"], fontsize=7, color="grey")
    ax.set_title(f"Strength Profile (Z-score) — {SETTING_LABELS[setting]}",
                 fontsize=11, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "07_strength_profile_S1.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_ranking_bar(mean_df: pd.DataFrame, setting: str, out_dir: Path):
    """Chart 08: Grouped bar — mean z-score per metric, coloured by dataset."""
    z_df = compute_z_scores(mean_df, setting)
    z_sub = z_df[METRICS].rename(columns=METRIC_SHORT)
    palette = sns.color_palette("tab10", len(z_sub))

    x = np.arange(len(METRICS))
    width = 0.12
    fig, ax = plt.subplots(figsize=(12, 5))

    for i, (ds, row) in enumerate(z_sub.iterrows()):
        ax.bar(x + i * width, row.values, width, label=DATASETS_META[ds]["label"],
               color=palette[i], alpha=0.85)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x + width * (len(z_sub) - 1) / 2)
    ax.set_xticklabels([METRIC_SHORT[m] for m in METRICS], fontsize=9)
    ax.set_ylabel("Z-score", fontsize=10)
    ax.set_title(f"Per-Metric Z-score by Dataset — {SETTING_LABELS[setting]}", fontsize=12)
    ax.legend(fontsize=8, ncol=3)
    plt.tight_layout()
    plt.savefig(out_dir / "08_ranking_bar_S1.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_spearman_heatmap(df: pd.DataFrame, out_dir: Path):
    """Chart 09: Spearman correlation heatmap between settings (Overall score, per dataset)."""
    non_en_datasets = [d for d in DATASET_ORDER if DATASETS_META[d]["language"] != "en"]
    # For each pair of settings, compute cross-dataset avg Spearman
    setting_pairs = []
    for ds in non_en_datasets:
        ds_df = df[df["dataset"] == ds]
        available = ds_df["setting"].unique()
        if "S1" in available and "S2" in available and "S3" in available:
            setting_pairs.append(ds)

    corr_matrix = pd.DataFrame(index=SETTINGS, columns=SETTINGS, dtype=float)
    for i, sa in enumerate(SETTINGS):
        for j, sb in enumerate(SETTINGS):
            if i == j:
                corr_matrix.loc[sa, sb] = 1.0
                continue
            rs_list = []
            for ds in setting_pairs:
                ds_df = df[df["dataset"] == ds]
                a_vals = ds_df[ds_df["setting"] == sa][OVERALL_KEY].values
                b_vals = ds_df[ds_df["setting"] == sb][OVERALL_KEY].values
                n = min(len(a_vals), len(b_vals))
                if n >= 3:
                    r, _ = stats.spearmanr(a_vals[:n], b_vals[:n])
                    rs_list.append(r)
            corr_matrix.loc[sa, sb] = float(np.mean(rs_list)) if rs_list else np.nan

    corr_matrix = corr_matrix.astype(float)

    fig, ax = plt.subplots(figsize=(5, 4))
    mask = np.eye(len(SETTINGS), dtype=bool)
    sns.heatmap(
        corr_matrix, annot=True, fmt=".3f", cmap="coolwarm",
        vmin=-1, vmax=1, ax=ax, linewidths=0.5, mask=False,
        cbar_kws={"label": "Spearman r"},
        xticklabels=[SETTING_LABELS[s] for s in SETTINGS],
        yticklabels=[SETTING_LABELS[s] for s in SETTINGS],
    )
    ax.set_title(
        "Avg Spearman Correlation Between Settings\n(Overall score, non-EN datasets)",
        fontsize=10, pad=10
    )
    plt.tight_layout()
    plt.savefig(out_dir / "09_spearman_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()

    return corr_matrix


def fig_criterion_comparison_all(mean_df: pd.DataFrame, out_dir: Path):
    """
    Chart 10: Per-dataset profile — 6 subplots, one per dataset.
    X-axis = 5 metrics; bars = S1 / S2 / S3.
    S2 absent (no bar) for EN datasets; annotated on title.
    """
    width = 0.25
    x = np.arange(len(METRICS))
    metric_labels = [METRIC_SHORT[m] for m in METRICS]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    axes = axes.flatten()

    for ax, ds in zip(axes, DATASET_ORDER):
        is_en = DATASETS_META[ds]["language"] == "en"
        ds_df = mean_df[mean_df["dataset"] == ds]

        s1_row = ds_df[ds_df["setting"] == "S1"]
        s2_row = ds_df[ds_df["setting"] == "S2"]
        s3_row = ds_df[ds_df["setting"] == "S3"]

        s1_vals = [s1_row[m].values[0] if not s1_row.empty else np.nan for m in METRICS]
        s3_vals = [s3_row[m].values[0] if not s3_row.empty else np.nan for m in METRICS]

        if is_en:
            # EN datasets: S1 only (S2=N/A, S3=S1 → no need to show S3)
            ax.bar(x, s1_vals, width * 1.2, color=COLORS["S1"], alpha=0.85, label="S1")
        else:
            s2_vals = [s2_row[m].values[0] if not s2_row.empty else np.nan for m in METRICS]
            ax.bar(x - width, s1_vals, width, color=COLORS["S1"], alpha=0.85, label="S1")
            ax.bar(x,          s2_vals, width, color=COLORS["S2"], alpha=0.80, label="S2")
            ax.bar(x + width,  s3_vals, width, color=COLORS["S3"], alpha=0.85, label="S3")

        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels, fontsize=8)
        ax.set_ylim(1, 6.5)
        ax.axhline(3.5, color="grey", linestyle=":", linewidth=0.7)
        lang = DATASETS_META[ds]["language"].upper()
        s2_note = "  [S1 only]" if is_en else ""
        ax.set_title(f"{ds}  [{lang}]{s2_note}", fontsize=9, fontweight="bold")
        if ax in (axes[0], axes[3]):
            ax.set_ylabel("Mean Score (1-6)", fontsize=8)

    handles = [
        mpatches.Patch(color=COLORS["S1"], label="S1 (EN↔EN)"),
        mpatches.Patch(color=COLORS["S2"], label="S2 (NL↔NL)"),
        mpatches.Patch(color=COLORS["S3"], label="S3 (NL→EN)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("S1 / S2 / S3 Comparison per Dataset and Metric",
                 fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(out_dir / "10_criterion_comparison_all.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_per_metric_heatmap_s2(mean_df: pd.DataFrame, out_dir: Path):
    """Chart 11: Heatmap 5 metrics for S2 (non-EN datasets only)."""
    s2_df = mean_df[mean_df["setting"] == "S2"].set_index("dataset")
    # Build full-index df with NaN for EN datasets
    full_df = pd.DataFrame(index=DATASET_ORDER, columns=METRICS, dtype=float)
    for ds in DATASET_ORDER:
        if ds in s2_df.index:
            full_df.loc[ds] = s2_df.loc[ds, METRICS].values
        # else: stays NaN

    data = full_df.rename(columns=METRIC_SHORT)
    mask = data.isna()

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.heatmap(
        data,
        annot=True, fmt=".2f",
        cmap="YlOrRd", vmin=1, vmax=6,
        mask=mask,
        ax=ax, linewidths=0.5,
        cbar_kws={"label": "Mean score (1-6)"},
    )
    # Label N/A cells
    for r, ds in enumerate(full_df.index):
        for c in range(len(METRICS)):
            if mask.iloc[r, c]:
                ax.text(c + 0.5, r + 0.5, "-", ha="center", va="center",
                        fontsize=12, color="grey")
    ax.set_title(
        "Per-Metric Score Heatmap — S2 (NL↔NL)\n"
        "(non-EN datasets only; EN datasets shown as '-')",
        fontsize=11, pad=10
    )
    ax.set_xlabel("Metric", fontsize=10)
    ax.set_ylabel("Dataset", fontsize=10)
    plt.tight_layout()
    plt.savefig(out_dir / "11_per_metric_heatmap_S2.png", dpi=150, bbox_inches="tight")
    plt.close()


# ─────────────────────── NEW CHARTS (12, 13) ────────────────────────────────

def fig_kmi_translation_comparison(kmi_means: pd.DataFrame, out_dir: Path):
    """
    Chart 12: Grouped bar — S1-utt vs S1-llm vs S2-ko per metric for KMI.
    Highlights the utterance_en artifact vs GPT-5.1 translation vs native KO judge.
    """
    conditions = kmi_means["condition"].tolist()
    condition_keys = kmi_means["condition_key"].tolist()
    colors = {
        "s1_utt": "#E57373",   # red — baseline utterance_en
        "s1_llm": "#42A5F5",   # blue — GPT-5.1 translated
        "s2_ko":  "#66BB6A",   # green — native KO judge
    }

    metric_labels = [METRIC_SHORT[m] for m in METRICS]
    x = np.arange(len(METRICS))
    width = 0.25
    n_cond = len(conditions)
    offsets = np.linspace(-(n_cond - 1) * width / 2, (n_cond - 1) * width / 2, n_cond)

    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (cond, key) in enumerate(zip(conditions, condition_keys)):
        vals = [kmi_means.loc[kmi_means["condition_key"] == key, m].values[0]
                for m in METRICS]
        bars = ax.bar(x + offsets[i], vals, width, label=cond.replace("\n", " "),
                      color=colors[key], alpha=0.85, edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=10)
    ax.set_ylim(1, 6)
    ax.set_ylabel("Mean Score (1–6)", fontsize=10)
    ax.set_title(
        "KMI — Translation Variant Comparison (N=20)\n"
        "S1-utt (utterance_en)  vs  S1-llm (GPT-5.1 KO→EN)  vs  S2-ko (KO gốc + KO judge)",
        fontsize=11, pad=10
    )
    ax.legend(fontsize=9, ncol=3, loc="upper right")
    ax.axhline(y=1, color="lightgrey", lw=0.5)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "12_kmi_translation_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_judge_comparison(
    comp_df: pd.DataFrame,
    judge_name: str,
    out_dir: Path,
):
    """
    Chart 13: Judge comparison GPT-5.1 vs <judge_name> across ALL settings (S1/S2/S3).

    Row 1: Overall score grouped bar per dataset, one panel per setting.
    Row 2: Delta heatmap (named_judge − GPT) per dataset × metric, one panel per setting.
    """
    if comp_df.empty:
        return

    settings_present = [s for s in SETTINGS if s in comp_df["setting"].unique()]
    n_settings = len(settings_present)
    alt_col = f"{judge_name}_mean"

    fig, axes = plt.subplots(2, n_settings, figsize=(7 * n_settings, 10),
                              gridspec_kw={"height_ratios": [1, 1.4]})
    if n_settings == 1:
        axes = axes.reshape(2, 1)

    metric_col_order = [METRIC_SHORT[m] for m in METRICS + [OVERALL_KEY]]

    for col_idx, setting in enumerate(settings_present):
        s_df = comp_df[comp_df["setting"] == setting]
        overall_s = s_df[s_df["metric"] == OVERALL_KEY].copy()
        datasets_s = [d for d in DATASET_ORDER if d in overall_s["dataset"].values]

        # ── Row 0: grouped bar Overall ─────────────────────────
        ax_bar = axes[0, col_idx]
        x = np.arange(len(datasets_s))
        width = 0.35
        gpt_vals = [overall_s.loc[overall_s["dataset"] == d, "gpt_mean"].values[0]
                    for d in datasets_s]
        alt_vals = [overall_s.loc[overall_s["dataset"] == d, alt_col].values[0]
                    for d in datasets_s]

        ax_bar.bar(x - width / 2, gpt_vals, width, label="GPT-5.1",
                   color="#42A5F5", alpha=0.85)
        ax_bar.bar(x + width / 2, alt_vals, width, label=judge_name,
                   color="#FF7043", alpha=0.85)
        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels(datasets_s, rotation=25, ha="right", fontsize=8)
        ax_bar.set_ylim(1, 6)
        ax_bar.set_ylabel("Overall Score (1–6)", fontsize=9)
        ax_bar.set_title(
            f"Overall — {SETTING_LABELS[setting]}\nGPT-5.1 vs {judge_name}",
            fontsize=10
        )
        ax_bar.legend(fontsize=8)
        ax_bar.grid(axis="y", alpha=0.3)

        # ── Row 1: delta heatmap (all metrics) ─────────────────
        ax_hm = axes[1, col_idx]
        pivot = (s_df.pivot(index="dataset", columns="metric_short", values="delta")
                 .reindex(index=[d for d in DATASET_ORDER if d in s_df["dataset"].values]))
        pivot = pivot.reindex(
            columns=[c for c in metric_col_order if c in pivot.columns]
        )

        flat = pivot.values[~np.isnan(pivot.values)]
        vmax = max(abs(flat).max(), 0.5) if len(flat) else 1.0
        sns.heatmap(
            pivot,
            annot=True, fmt=".2f",
            cmap="RdYlGn", center=0, vmin=-vmax, vmax=vmax,
            ax=ax_hm, linewidths=0.5,
            cbar_kws={"label": f"{judge_name} − GPT"},
        )
        ax_hm.set_title(
            f"Delta ({judge_name} − GPT)\n{SETTING_LABELS[setting]}",
            fontsize=10
        )
        ax_hm.set_xlabel("Metric", fontsize=8)
        ax_hm.set_ylabel("Dataset", fontsize=8)
        ax_hm.tick_params(axis="x", labelsize=8)
        ax_hm.tick_params(axis="y", labelsize=8)

    fig.suptitle(
        f"Judge Comparison: GPT-5.1 vs {judge_name}  (N=20/cell)\n"
        f"Green = {judge_name} higher  |  Red = GPT higher",
        fontsize=12, y=1.01
    )
    plt.tight_layout()
    plt.savefig(out_dir / f"13_judge_comparison_{judge_name}.png",
                dpi=150, bbox_inches="tight")
    plt.close()


# ─────────────────────── REPORT GENERATION ─────────────────────────────────

def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def generate_report(
    mean_df: pd.DataFrame,
    std_df: pd.DataFrame,
    lang_effect_df: pd.DataFrame,
    disc_power_df: pd.DataFrame,
    corr_matrix: pd.DataFrame,
    z_s1: pd.DataFrame,
    z_s3: pd.DataFrame,
    out_dir: Path,
    kmi_means: Optional[pd.DataFrame] = None,
    judge_comp_df: Optional[pd.DataFrame] = None,
    judge_name: Optional[str] = None,
):
    """Tạo báo cáo markdown tổng hợp."""
    report_path = out_dir / "report.md"

    # ── Overall pivot ──────────────────────────
    overall_pivot = pivot_overall(mean_df).astype(float)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# MindEval Dim-A — Báo cáo phân tích kết quả\n\n")
        f.write(f"> N = 20 record/dataset/setting | Thang điểm 1–6\n\n")
        f.write("---\n\n")

        # Section 1: Raw means overall
        f.write("## 1. Điểm trung bình Overall score\n\n")
        f.write("| Dataset | Lang | Origin | ")
        settings_available = [s for s in SETTINGS if s in mean_df["setting"].values]
        f.write(" | ".join(SETTING_LABELS[s] for s in settings_available))
        f.write(" |\n")
        f.write("|" + "---|" * (3 + len(settings_available)) + "\n")
        for ds in DATASET_ORDER:
            is_en = DATASETS_META[ds]["language"] == "en"
            row = f"| {ds} | {DATASETS_META[ds]['language']} | {DATASETS_META[ds]['origin_type']} | "
            for s in settings_available:
                # S2 for EN datasets = not applicable (no separate NL judge)
                if is_en and s == "S2":
                    row += "- | "
                else:
                    val = overall_pivot.loc[ds, s] if s in overall_pivot.columns else np.nan
                    row += f"{_fmt(val)} | "
            f.write(row + "\n")
        f.write("\n")

        # Section 2: Per-metric means S1
        f.write("## 2. Điểm trung bình theo metric — S1 (EN↔EN)\n\n")
        s1_df = mean_df[mean_df["setting"] == "S1"].set_index("dataset").reindex(DATASET_ORDER)
        f.write("| Dataset | " + " | ".join(METRIC_SHORT[m] for m in METRICS) + " | Overall |\n")
        f.write("|" + "---|" * (1 + len(METRICS) + 1) + "\n")
        for ds in DATASET_ORDER:
            row_data = s1_df.loc[ds] if ds in s1_df.index else pd.Series({})
            row = f"| {ds} | "
            for m in METRICS:
                row += f"{_fmt(row_data.get(m, np.nan))} | "
            row += f"{_fmt(row_data.get(OVERALL_KEY, np.nan))} |"
            f.write(row + "\n")
        f.write("\n")

        # Section 3: Z-score ranking S1
        f.write("## 3. Ranking theo Z-score — S1 (EN↔EN)\n\n")
        f.write("> Z-score (+) = trên trung bình | Mean-rank (thấp = tốt hơn)\n\n")
        f.write("| Dataset | " + " | ".join(METRIC_SHORT[m] for m in METRICS) + " | Mean-Rank |\n")
        f.write("|" + "---|" * (1 + len(METRICS) + 1) + "\n")
        for ds in DATASET_ORDER:
            row_data = z_s1.loc[ds] if ds in z_s1.index else pd.Series({})
            row = f"| {ds} | "
            for m in METRICS:
                row += f"{_fmt(row_data.get(m, np.nan))} | "
            row += f"{_fmt(row_data.get('mean_rank', np.nan))} |"
            f.write(row + "\n")
        f.write("\n")

        # Section 4: Z-score ranking S3
        if not z_s3.empty:
            f.write("## 4. Ranking theo Z-score — S3 (NL→EN)\n\n")
            f.write("| Dataset | " + " | ".join(METRIC_SHORT[m] for m in METRICS) + " | Mean-Rank |\n")
            f.write("|" + "---|" * (1 + len(METRICS) + 1) + "\n")
            for ds in DATASET_ORDER:
                row_data = z_s3.loc[ds] if ds in z_s3.index else pd.Series({})
                row = f"| {ds} | "
                for m in METRICS:
                    row += f"{_fmt(row_data.get(m, np.nan))} | "
                row += f"{_fmt(row_data.get('mean_rank', np.nan))} |"
                f.write(row + "\n")
            f.write("\n")

        # Section 5: Language effect
        f.write("## 5. Phân tích ảnh hưởng ngôn ngữ\n\n")
        f.write("### 5.1 Spearman correlation trung bình giữa các setting (non-EN)\n\n")
        if not corr_matrix.empty:
            f.write(corr_matrix.round(3).to_markdown())
            f.write("\n\n")

        f.write("### 5.2 Chi tiết per dataset\n\n")
        if not lang_effect_df.empty:
            cols = ["dataset", "comparison", "n", "mean_A", "mean_B",
                    "mean_delta (A-B)", "MAD", "Spearman_r", "Spearman_p",
                    "sig_diff"]
            avail_cols = [c for c in cols if c in lang_effect_df.columns]
            f.write(lang_effect_df[avail_cols].round(3).to_markdown(index=False))
            f.write("\n\n")

        # Section 6: Discriminative power
        f.write("## 6. Sức phân biệt (Discriminative Power)\n\n")
        f.write("> Std của dataset-mean per metric per setting — cao = phân biệt tốt hơn\n\n")
        f.write(disc_power_df.round(3).to_markdown(index=False))
        f.write("\n\n")

        # Section 7: Interpretation
        f.write("## 7. Giải thích & Khuyến nghị\n\n")

        # Pick best setting
        disc_overall = disc_power_df.set_index("setting")[OVERALL_KEY]
        best_setting = disc_overall.idxmax() if not disc_overall.empty else "S1"
        f.write(f"**Setting có sức phân biệt cao nhất (Overall):** `{best_setting}` "
                f"(std = {disc_overall.get(best_setting, np.nan):.3f})\n\n")

        # Spearman S1 vs S3
        if "S1" in corr_matrix.index and "S3" in corr_matrix.columns:
            r_s1_s3 = corr_matrix.loc["S1", "S3"]
            f.write(f"**Tương quan Spearman S1 vs S3:** r = {r_s1_s3:.3f}")
            if r_s1_s3 >= 0.8:
                f.write(" → **Cao** (bản dịch ít ảnh hưởng đến ranking). "
                        "Có thể dùng S3 thay S1 để tránh artifact dịch.\n")
            elif r_s1_s3 >= 0.6:
                f.write(" → **Vừa** (bản dịch có ảnh hưởng vừa phải). "
                        "Nên báo cáo cả S1 và S3.\n")
            else:
                f.write(" → **Thấp** (bản dịch ảnh hưởng đáng kể đến ranking). "
                        "Cần kiểm tra chất lượng dịch.\n")
            f.write("\n")

        f.write("### Caveat\n\n")
        f.write(
            "Ranking này phản ánh **thế mạnh tương đối** trong điều kiện pilot N=20, "
            "không phải chất lượng tuyệt đối. Cần xem xét cùng với confound nguồn gốc "
            "(human/simulated), độ dài hội thoại, và chất lượng bản dịch (S1).\n"
        )

        # Section 8: KMI translation comparison
        if kmi_means is not None and not kmi_means.empty:
            f.write("## 8. KMI — So sánh bản dịch (S1-utt vs S1-llm vs S2-ko)\n\n")
            f.write(
                "> S1-utt = `utterance_en` có sẵn | "
                "S1-llm = GPT-5.1 dịch từ KO | "
                "S2-ko = hội thoại KO gốc + judge KO\n\n"
            )

            # Table: mean per condition per metric
            metric_cols = [METRIC_SHORT[m] for m in METRICS] + ["Overall"]
            f.write("| Condition | " + " | ".join(metric_cols) + " |\n")
            f.write("|" + "---|" * (1 + len(metric_cols)) + "\n")
            for _, row in kmi_means.iterrows():
                label = row["condition"].replace("\n", " ")
                f.write(f"| {label} | ")
                for m in METRICS:
                    f.write(f"{_fmt(row.get(m, np.nan))} | ")
                f.write(f"{_fmt(row.get(OVERALL_KEY, np.nan))} |\n")
            f.write("\n")

            # Deltas
            utt_row = kmi_means[kmi_means["condition_key"] == "s1_utt"].iloc[0]
            llm_row = kmi_means[kmi_means["condition_key"] == "s1_llm"].iloc[0]
            s2_row  = kmi_means[kmi_means["condition_key"] == "s2_ko"].iloc[0]
            delta_llm_utt  = llm_row[OVERALL_KEY] - utt_row[OVERALL_KEY]
            delta_llm_s2   = llm_row[OVERALL_KEY] - s2_row[OVERALL_KEY]

            f.write(f"**Delta Overall (S1-llm − S1-utt):** {delta_llm_utt:+.3f}  \n")
            f.write(f"**Delta Overall (S1-llm − S2-ko):**  {delta_llm_s2:+.3f}  \n\n")

            if abs(delta_llm_s2) < 0.15:
                f.write(
                    "> **Kết luận**: S1-llm xap xỉ S2-ko (|Δ| < 0.15) — GPT-5.1 translation "
                    "giữ được sắc thái gần với bản gốc. `utterance_en` bị artifact "
                    f"(S1-utt thấp hơn S1-llm {abs(delta_llm_utt):.3f} điểm).\n"
                    "> Khuyến nghị: dùng S1-llm làm S1 chính thức của KMI.\n\n"
                )
            else:
                f.write(
                    f"> **Ghi chú**: Δ(S1-llm − S2-ko) = {delta_llm_s2:+.3f} — "
                    "cần phân tích thêm để xác nhận nguồn bias.\n\n"
                )

        # Section 9: Judge comparison (all settings)
        if judge_comp_df is not None and not judge_comp_df.empty and judge_name:
            f.write(f"## 9. So sánh judge: GPT-5.1 vs {judge_name}\n\n")
            f.write(
                f"> Cả hai judge dùng cùng rubric. Delta = {judge_name} − GPT-5.1.  \n"
                f"> Green (Δ > 0): {judge_name} chấm cao hơn | Red (Δ < 0): GPT chấm cao hơn.\n\n"
            )
            settings_present = [s for s in SETTINGS
                                 if s in judge_comp_df["setting"].unique()]
            alt_col = f"{judge_name}_mean"
            for setting in settings_present:
                s_df = judge_comp_df[
                    (judge_comp_df["setting"] == setting) &
                    (judge_comp_df["metric"] == OVERALL_KEY)
                ].copy()
                if s_df.empty:
                    continue
                f.write(f"### {SETTING_LABELS[setting]}\n\n")
                f.write(f"| Dataset | GPT-5.1 | {judge_name} | Delta |\n")
                f.write("|---|---|---|---|\n")
                for _, row in s_df.iterrows():
                    f.write(
                        f"| {row['dataset']} | {_fmt(row['gpt_mean'])} | "
                        f"{_fmt(row[alt_col])} | {row['delta']:+.3f} |\n"
                    )
                mean_delta = s_df["delta"].mean()
                f.write(f"\n**Mean Δ Overall ({setting}):** {mean_delta:+.3f}  \n\n")

            # Cross-setting summary
            overall_all = judge_comp_df[judge_comp_df["metric"] == OVERALL_KEY]
            global_mean = overall_all["delta"].mean()
            f.write(f"**Global mean Δ Overall (all settings):** {global_mean:+.3f}  \n\n")
            if abs(global_mean) < 0.2:
                f.write("> **Kết luận**: Hai judge nhất quán cao (|mean Δ| < 0.2) "
                        "— kết quả ranking đáng tin cậy.\n\n")
            else:
                f.write(
                    f"> **Ghi chú**: Global mean Δ = {global_mean:+.3f} — "
                    "cần kiểm tra xem judge nào systematic higher/lower "
                    "và ảnh hưởng đến ranking.\n\n"
                )

        f.write("\n---\n")
        f.write("*Generated by `mindeval/scripts/analyze_results.py`*\n")

    print(f"  [report] Saved -> {report_path}")
    return report_path


# ─────────────────────── MAIN ──────────────────────────────────────────────

def main(output_dir: Optional[str] = None, judge_name: Optional[str] = None):
    out_root = Path(output_dir) if output_dir else (BASE_DIR / "_analysis" / "mind_eval")
    tables_dir = out_root / "tables"
    charts_dir = out_root / "charts"
    tables_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("  MindEval -- Full Results Analysis")
    print("=" * 70 + "\n")

    # 1. Load data
    print("[1/7] Loading data...")
    df = build_long_df()
    print(f"  Total records: {len(df)}")
    avail = df.groupby(["dataset", "setting"]).size().reset_index(name="n")
    print(avail.to_string(index=False))

    # 2. Raw means
    print("\n[2/7] Computing raw means...")
    mean_df, std_df = compute_raw_means(df)
    mean_df.to_csv(tables_dir / "summary_raw_means.csv", index=False, float_format="%.4f")
    std_df.to_csv(tables_dir  / "summary_std.csv",       index=False, float_format="%.4f")
    print("  Saved: summary_raw_means.csv, summary_std.csv")

    # 3. Z-score rankings
    print("\n[3/7] Computing z-scores & mean-rank...")
    z_s1 = compute_z_scores(mean_df, "S1")
    z_s3 = compute_z_scores(mean_df, "S3")
    z_s1.to_csv(tables_dir / "ranking_S1.csv", float_format="%.4f")
    z_s3.to_csv(tables_dir / "ranking_S3.csv", float_format="%.4f")
    print("  Saved: ranking_S1.csv, ranking_S3.csv")
    print("\n  Ranking S1 (mean-rank, lower = better):")
    print(z_s1["mean_rank"].sort_values().to_string())

    # 4. Language effect
    print("\n[4/7] Language effect analysis...")
    lang_effect_df = language_effect_analysis(df)
    lang_effect_df.to_csv(tables_dir / "language_effect.csv", index=False, float_format="%.4f")
    print(f"  Saved: language_effect.csv ({len(lang_effect_df)} comparisons)")

    # 5. Discriminative power
    disc_power_df = compute_discriminative_power(mean_df)
    disc_power_df.to_csv(tables_dir / "discriminative_power.csv", index=False, float_format="%.4f")
    print("  Saved: discriminative_power.csv")

    # 6. Charts
    print("\n[5/7] Generating charts...")
    sns.set_theme(style="whitegrid", font_scale=1.0)

    fig_overall_heatmap(mean_df, charts_dir)
    print("  01_overall_heatmap.png [OK]")

    fig_per_metric_heatmap(mean_df, "S1", "02", charts_dir)
    print("  02_per_metric_heatmap_S1.png [OK]")

    fig_per_metric_heatmap(mean_df, "S3", "03", charts_dir)
    print("  03_per_metric_heatmap_S3.png [OK]")

    fig_language_effect_scatter(df, "S1", "S3", "04", "Translation Effect", charts_dir)
    print("  04_language_effect_S1_S3.png [OK]")

    fig_language_effect_scatter(df, "S2", "S3", "05", "Judge-Language Effect", charts_dir)
    print("  05_language_effect_S2_S3.png [OK]")

    fig_boxplot_settings(df, charts_dir)
    print("  06_boxplot_settings.png [OK]")

    fig_radar_strength_profile(mean_df, "S1", charts_dir)
    print("  07_strength_profile_S1.png [OK]")

    fig_ranking_bar(mean_df, "S1", charts_dir)
    print("  08_ranking_bar_S1.png [OK]")

    corr_matrix = fig_spearman_heatmap(df, charts_dir)
    print("  09_spearman_heatmap.png [OK]")

    fig_criterion_comparison_all(mean_df, charts_dir)
    print("  10_criterion_comparison_all.png [OK]")

    fig_per_metric_heatmap_s2(mean_df, charts_dir)
    print("  11_per_metric_heatmap_S2.png [OK]")

    # 6b. KMI translation comparison (chart 12) — only if S1_ko_translated file exists
    kmi_data = load_kmi_translation_comparison()
    kmi_means: Optional[pd.DataFrame] = None
    if kmi_data is not None:
        print("\n[5b/7] KMI translation comparison analysis...")
        kmi_means = compute_kmi_translation_means(kmi_data)
        kmi_means.to_csv(tables_dir / "kmi_translation_comparison.csv",
                         index=False, float_format="%.4f")
        print("  Saved: kmi_translation_comparison.csv")
        fig_kmi_translation_comparison(kmi_means, charts_dir)
        print("  12_kmi_translation_comparison.png [OK]")
    else:
        print("\n[5b/7] KMI translation comparison: SKIP "
              "(S1_ko_translated_gpt_judgments.jsonl not found)")

    # 6c. Judge comparison (chart 13) — explicit or auto-detect
    judge_comp_df: Optional[pd.DataFrame] = None
    active_judge_name: Optional[str] = None

    candidates = [judge_name] if judge_name else ["claude", "qwen", "gemini"]
    for candidate_judge in candidates:
        named_data = load_judgments_for_judge(candidate_judge)
        if named_data:
            settings_found = sorted({d["setting"] for d in named_data})
            datasets_found = sorted({d["dataset"] for d in named_data})
            print(f"\n[5c/7] Judge comparison: GPT vs {candidate_judge}")
            print(f"  Found: {len(named_data)} files — "
                  f"datasets={datasets_found}  settings={settings_found}")
            judge_comp_df = build_judge_comparison_df(mean_df, named_data, candidate_judge)
            judge_comp_df.to_csv(
                tables_dir / f"judge_comparison_{candidate_judge}.csv",
                index=False, float_format="%.4f"
            )
            print(f"  Saved: judge_comparison_{candidate_judge}.csv")
            fig_judge_comparison(judge_comp_df, candidate_judge, charts_dir)
            print(f"  13_judge_comparison_{candidate_judge}.png [OK]")
            active_judge_name = candidate_judge
            break
    else:
        print("\n[5c/7] Judge comparison: SKIP (no named judge files found — "
              "run: python -m mindeval.scripts.run_eval_matrix --pilot "
              "--judge_name claude --eval mind-eval)")

    # 7. Report
    print("\n[6/7] Generating markdown report...")
    report_path = generate_report(
        mean_df, std_df, lang_effect_df, disc_power_df,
        corr_matrix, z_s1, z_s3, out_root,
        kmi_means=kmi_means,
        judge_comp_df=judge_comp_df,
        judge_name=active_judge_name,
    )

    print("\n[7/7] Done!")
    print("=" * 70)
    print(f"\n  Output : {out_root}")
    print(f"  Tables : {tables_dir}")
    print(f"  Charts : {charts_dir}")
    print(f"  Report : {report_path}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phân tích kết quả MindEval Dim-A")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Thư mục output (default: data/_analysis/mind_eval)")
    parser.add_argument("--judge_name", type=str, default=None,
                        help="Named judge to compare against GPT default "
                             "(e.g. 'claude'). Auto-detected if not given.")
    args = parser.parse_args()
    main(output_dir=args.output_dir, judge_name=args.judge_name)
