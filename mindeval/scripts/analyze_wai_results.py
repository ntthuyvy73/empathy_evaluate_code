"""
Phân tích kết quả WAI-O-S (Dim-B) trên 6 dataset, setting S3 (NL→EN).

Output mặc định: data/_analysis/wai/
  tables/
    summary_raw_means.csv      — mean ± std per dataset × dimension + Total
    ranking_S3.csv             — z-score + mean-rank theo S3
    per_question_means.csv     — mean per dataset × Q1-Q12
    compare_S1_vs_S3.csv       — delta + correlation S1 vs S3 (khi dùng --compare)
  charts/
    01_dimension_heatmap.png   — heatmap 3 dims × 6 datasets
    02_per_question_heatmap.png — heatmap Q1-Q12 × 6 datasets
    03_strength_profile.png    — radar z-score strength profile
    04_ranking_bar.png         — grouped bar z-score per dimension per dataset
    05_boxplot_dims.png        — boxplot Total per dataset
    06_total_bar.png           — bar chart Total WAI mean per dataset (ranked)
    07_compare_heatmap.png     — delta heatmap S1 vs S3 (khi dùng --compare)
  report.md                    — báo cáo tổng hợp markdown

Chạy:
    python -m mindeval.scripts.analyze_wai_results
    python -m mindeval.scripts.analyze_wai_results --output_dir data/_analysis/wai_v2
    python -m mindeval.scripts.analyze_wai_results --judge_name gpt --setting S3

    # Sau khi có kết quả S1 WAI: so sánh S1 vs S3
    python -m mindeval.scripts.analyze_wai_results --compare --setting_a S1 --setting_b S3
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)

# ─────────────────────── CONFIG ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[2] / "data"

DATASETS_META = {
    "AnnoMI":      {"language": "en", "origin_type": "human",     "label": "AnnoMI"},
    "cactus":      {"language": "en", "origin_type": "simulated", "label": "cactus"},
    "Psy-Insight": {"language": "en", "origin_type": "human",     "label": "PsyInsight"},
    "ESConv":      {"language": "en", "origin_type": "human",     "label": "ESConv"},
    "simpsydial":  {"language": "zh", "origin_type": "simulated", "label": "simpsydial"},
    "PsyDial":     {"language": "zh", "origin_type": "human",     "label": "PsyDial"},
    "CPsyCoun":    {"language": "zh", "origin_type": "human",     "label": "CPsyCoun"},
    "SoulChat":    {"language": "zh", "origin_type": "simulated", "label": "SoulChat"},
    "smile":       {"language": "zh", "origin_type": "simulated", "label": "smile"},
    "KokoroChat":  {"language": "ja", "origin_type": "human",     "label": "KokoroChat"},
    "KMI":         {"language": "ko", "origin_type": "human",     "label": "KMI"},
}

DATASET_ORDER = [
    "AnnoMI", "cactus", "Psy-Insight", "ESConv",           # EN
    "simpsydial", "PsyDial", "CPsyCoun", "SoulChat", "smile",  # ZH
    "KokoroChat",                                            # JA
    "KMI",                                                   # KO
]

DIMENSIONS   = ["Goal", "Approach", "Affective Bond"]
QUESTIONS    = [f"Q{i}" for i in range(1, 13)]
DIM_METRICS  = DIMENSIONS + ["Total"]

DIM_QIDS: Dict[str, List[str]] = {
    "Goal":           ["Q1", "Q2", "Q3", "Q4"],
    "Approach":       ["Q5", "Q6", "Q7", "Q8"],
    "Affective Bond": ["Q9", "Q10", "Q11", "Q12"],
}

COLORS_DS = {
    "AnnoMI":      "#607D8B",
    "cactus":      "#2196F3",
    "Psy-Insight": "#9C27B0",
    "ESConv":      "#3F51B5",
    "simpsydial":  "#FF9800",
    "PsyDial":     "#F44336",
    "CPsyCoun":    "#00BCD4",
    "SoulChat":    "#4CAF50",
    "smile":       "#CDDC39",
    "KokoroChat":  "#E91E63",
    "KMI":         "#795548",
}

# ─────────────────────── DATA LOADING ───────────────────────────────────────

def load_wai_judgments(
    dataset: str,
    setting: str = "S3",
    judge_name: str = "gpt",
) -> Optional[List[Dict]]:
    """Load WAI judgment file.

    Primary convention:  data/<dataset>/results/wai/<dataset>_<setting>_<judge>_wai_judgments.jsonl
    Fallback (legacy):   data/<dataset>/results/wai/<setting>_<judge>_wai_judgments.jsonl
    """
    results_dir = BASE_DIR / dataset / "results" / "wai"
    path = results_dir / f"{dataset}_{setting}_{judge_name}_wai_judgments.jsonl"
    if not path.exists():
        path = results_dir / f"{setting}_{judge_name}_wai_judgments.jsonl"
    if not path.exists():
        return None
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records if records else None


def build_long_df(setting: str = "S3", judge_name: str = "gpt") -> pd.DataFrame:
    """
    Build long-form DataFrame with one row per record.

    Columns: dataset, dataset_label, language, origin_type, interaction_id,
             Goal, Approach, Affective Bond, Total, Q1..Q12
    """
    rows = []
    for ds in DATASET_ORDER:
        records = load_wai_judgments(ds, setting=setting, judge_name=judge_name)
        if records is None:
            print(f"  [SKIP] {ds}: no WAI file for {setting}_{judge_name}")
            continue
        print(f"  [OK]   {ds}: {len(records)} records")
        for idx, rec in enumerate(records):
            dims = rec.get("dimensions", {})
            qs   = rec.get("questions", {})
            row: Dict = {
                "dataset":      ds,
                "dataset_label": DATASETS_META[ds]["label"],
                "language":     DATASETS_META[ds]["language"],
                "origin_type":  DATASETS_META[ds]["origin_type"],
                "setting":      setting,
                "interaction_id": rec.get("interaction_id", f"{ds}_{idx}"),
                "record_idx":   idx,
            }
            for dim in DIMENSIONS:
                row[dim] = dims.get(dim, np.nan)
            row["Total"] = rec.get("total", np.nan)
            for qid in QUESTIONS:
                q_data = qs.get(qid, {})
                row[qid] = q_data.get("score", np.nan)
            rows.append(row)
    return pd.DataFrame(rows)


# ─────────────────────── SUMMARY TABLES ─────────────────────────────────────

def compute_raw_means(df: pd.DataFrame) -> pd.DataFrame:
    """Mean ± std per dataset × dimension/Total."""
    grouped = df.groupby("dataset")[DIM_METRICS]
    mean_df = grouped.mean().reindex(DATASET_ORDER)
    std_df  = grouped.std().reindex(DATASET_ORDER)
    return mean_df, std_df


def compute_z_scores(mean_df: pd.DataFrame) -> pd.DataFrame:
    """
    Z-score per dimension across 6 datasets.
    Returns DataFrame with index=dataset, columns=DIMENSIONS + 'mean_rank'.
    """
    z_df = mean_df[DIMENSIONS].apply(
        lambda col: stats.zscore(col.values, nan_policy="omit"), axis=0
    )
    z_df = pd.DataFrame(z_df, index=mean_df.index, columns=DIMENSIONS)
    rank_df = mean_df[DIMENSIONS].rank(ascending=False, method="average")
    z_df["mean_rank"] = rank_df.mean(axis=1)
    return z_df


def compute_per_question_means(df: pd.DataFrame) -> pd.DataFrame:
    """Mean per dataset × Q1-Q12."""
    return df.groupby("dataset")[QUESTIONS].mean().reindex(DATASET_ORDER)


# ─────────────────────── CHARTS ─────────────────────────────────────────────

def _ds_labels() -> List[str]:
    return [DATASETS_META[d]["label"] for d in DATASET_ORDER]


def chart_dimension_heatmap(mean_df: pd.DataFrame, out_path: Path) -> None:
    """Heatmap: rows=datasets, cols=3 dimensions + Total, value=raw mean."""
    data = mean_df[DIM_METRICS].copy()
    data.index = _ds_labels()

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        data,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        vmin=1, vmax=5,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Mean score (1–5)"},
    )
    ax.set_title("WAI-O-S: Mean Dimension Scores by Dataset (S3, N=20)", fontsize=13, pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_per_question_heatmap(q_means: pd.DataFrame, out_path: Path) -> None:
    """Heatmap: rows=datasets, cols=Q1-Q12."""
    data = q_means.copy()
    data.index = _ds_labels()

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        data,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        vmin=1, vmax=5,
        linewidths=0.4,
        ax=ax,
        cbar_kws={"label": "Mean score (1–5)"},
    )
    # Dimension separators
    ax.axvline(4,  color="black", linewidth=1.5)
    ax.axvline(8,  color="black", linewidth=1.5)
    ax.axvline(12, color="black", linewidth=1.5)
    ax.set_title("WAI-O-S: Per-Question Scores by Dataset (S3, N=20)", fontsize=13, pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_strength_profile(z_df: pd.DataFrame, out_path: Path) -> None:
    """Radar chart: z-score strength profile per dataset."""
    dims = DIMENSIONS
    n = len(dims)
    angles = [i / n * 2 * math.pi for i in range(n)] + [0]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks([i / n * 2 * math.pi for i in range(n)])
    ax.set_xticklabels(dims, size=11)
    ax.set_ylim(-2.5, 2.5)
    ax.set_yticks([-2, -1, 0, 1, 2])
    ax.yaxis.set_tick_params(labelsize=8)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")

    for ds in DATASET_ORDER:
        label = DATASETS_META[ds]["label"]
        values = [z_df.loc[ds, d] for d in dims]
        values += [values[0]]
        ax.plot(angles, values, linewidth=2, label=label, color=COLORS_DS[ds])
        ax.fill(angles, values, alpha=0.08, color=COLORS_DS[ds])

    ax.set_title("WAI-O-S: Z-score Strength Profile (S3)", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=9)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_ranking_bar(z_df: pd.DataFrame, out_path: Path) -> None:
    """Grouped bar chart: z-score per dimension per dataset, sorted by mean_rank."""
    sorted_ds = z_df.sort_values("mean_rank").index.tolist()
    labels    = [DATASETS_META[d]["label"] for d in sorted_ds]
    x         = np.arange(len(sorted_ds))
    w         = 0.22
    offsets   = [-w, 0, w]
    dim_colors = ["#2196F3", "#FF9800", "#4CAF50"]

    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (dim, col) in enumerate(zip(DIMENSIONS, dim_colors)):
        vals = [z_df.loc[ds, dim] for ds in sorted_ds]
        ax.bar(x + offsets[i], vals, width=w, label=dim, color=col, alpha=0.85)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Z-score")
    ax.set_title("WAI-O-S: Strength Profile by Dimension (S3, ranked by mean_rank)", fontsize=12)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_boxplot(df: pd.DataFrame, out_path: Path) -> None:
    """Boxplot: Total WAI score distribution per dataset."""
    order  = DATASET_ORDER
    labels = _ds_labels()
    colors = [COLORS_DS[d] for d in order]

    fig, ax = plt.subplots(figsize=(10, 5))
    data_per_ds = [df[df["dataset"] == ds]["Total"].dropna().values for ds in order]

    bp = ax.boxplot(
        data_per_ds,
        tick_labels=labels,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 2},
        whiskerprops={"linewidth": 1.2},
        capprops={"linewidth": 1.2},
    )
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col)
        patch.set_alpha(0.7)

    ax.set_ylim(1, 5.2)
    ax.axhline(3, color="grey", linewidth=0.8, linestyle="--", alpha=0.7)
    ax.set_ylabel("Total WAI score (1–5)")
    ax.set_title("WAI-O-S: Total Score Distribution per Dataset (S3, N=20)", fontsize=12)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_total_bar(mean_df: pd.DataFrame, std_df: pd.DataFrame, out_path: Path) -> None:
    """Horizontal bar chart: Total WAI mean ± std per dataset, sorted."""
    ds_sorted = mean_df["Total"].sort_values(ascending=False).index.tolist()
    labels    = [DATASETS_META[d]["label"] for d in ds_sorted]
    means     = [mean_df.loc[d, "Total"] for d in ds_sorted]
    stds      = [std_df.loc[d, "Total"] for d in ds_sorted]
    colors    = [COLORS_DS[d] for d in ds_sorted]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(ds_sorted))
    bars = ax.barh(y, means, xerr=stds, align="center",
                   color=colors, alpha=0.85, ecolor="black", capsize=4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlim(1, 5.3)
    ax.axvline(3, color="grey", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Total WAI score (1–5)")
    ax.set_title("WAI-O-S: Total Score Ranking (S3, N=20)", fontsize=12)
    for bar, mean in zip(bars, means):
        ax.text(mean + 0.06, bar.get_y() + bar.get_height() / 2,
                f"{mean:.2f}", va="center", fontsize=10)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────── REPORT ─────────────────────────────────────────────

def generate_report(
    mean_df: pd.DataFrame,
    std_df: pd.DataFrame,
    z_df: pd.DataFrame,
    q_means: pd.DataFrame,
    df: pd.DataFrame,
    setting: str,
    judge_name: str,
    n_records: int,
    out_path: Path,
) -> None:
    lines = []
    add = lines.append

    add("# WAI-O-S Analysis Report")
    add("")
    add(f"**Setting**: {setting} (original-language dialogue + English judge)  ")
    add(f"**Judge**: {judge_name}  ")
    add(f"**N per dataset**: {n_records}  ")
    add(f"**Scale**: 1–5 (WAI-O-S)  ")
    add(f"**Dimensions**: Goal (Q1-Q4) · Approach (Q5-Q8) · Affective Bond (Q9-Q12)  ")
    add("")
    add("---")
    add("")

    # Section 1: Raw means
    add("## 1. Raw Mean Scores")
    add("")
    header = "| Dataset | Goal | Approach | Affective Bond | **Total** |"
    sep    = "|---|---|---|---|---|"
    add(header); add(sep)
    for ds in DATASET_ORDER:
        if ds not in mean_df.index:
            continue
        label = DATASETS_META[ds]["label"]
        g  = mean_df.loc[ds, "Goal"]
        ap = mean_df.loc[ds, "Approach"]
        ab = mean_df.loc[ds, "Affective Bond"]
        tt = mean_df.loc[ds, "Total"]
        sg  = std_df.loc[ds, "Goal"]
        sap = std_df.loc[ds, "Approach"]
        sab = std_df.loc[ds, "Affective Bond"]
        stt = std_df.loc[ds, "Total"]
        add(f"| {label} | {g:.2f} ±{sg:.2f} | {ap:.2f} ±{sap:.2f} | "
            f"{ab:.2f} ±{sab:.2f} | **{tt:.2f} ±{stt:.2f}** |")
    add("")

    # Section 2: Z-score ranking
    add("## 2. Z-score Ranking (S3)")
    add("")
    add("*Z-score: (+) = above cross-dataset mean. Mean-rank: lower = better.*")
    add("")
    header2 = "| Dataset | Goal | Approach | Affective Bond | **Mean-Rank** |"
    sep2    = "|---|---|---|---|---|"
    add(header2); add(sep2)
    for ds in z_df.sort_values("mean_rank").index:
        if ds not in DATASETS_META:
            continue
        label = DATASETS_META[ds]["label"]
        g  = z_df.loc[ds, "Goal"]
        ap = z_df.loc[ds, "Approach"]
        ab = z_df.loc[ds, "Affective Bond"]
        mr = z_df.loc[ds, "mean_rank"]
        add(f"| {label} | {g:+.2f} | {ap:+.2f} | {ab:+.2f} | **{mr:.1f}** |")
    add("")

    # Section 3: Per-question means
    add("## 3. Per-Question Mean Scores")
    add("")
    q_header = "| Dataset | " + " | ".join(QUESTIONS) + " |"
    q_sep    = "|---|" + "---|" * len(QUESTIONS)
    add(q_header); add(q_sep)
    for ds in DATASET_ORDER:
        if ds not in q_means.index:
            continue
        label = DATASETS_META[ds]["label"]
        vals  = " | ".join(f"{q_means.loc[ds, q]:.2f}" for q in QUESTIONS)
        add(f"| {label} | {vals} |")
    add("")

    # Section 4: Thematic strength
    add("## 4. Thematic Strength Profile")
    add("")
    add("| Dataset | Điểm nổi bật | Điểm yếu nhất |")
    add("|---|---|---|")
    for ds in DATASET_ORDER:
        if ds not in mean_df.index:
            continue
        label = DATASETS_META[ds]["label"]
        scores = {d: mean_df.loc[ds, d] for d in DIMENSIONS}
        best  = max(scores, key=scores.get)
        worst = min(scores, key=scores.get)
        add(f"| **{label}** | {best} ({scores[best]:.2f}) | {worst} ({scores[worst]:.2f}) |")
    add("")

    # Section 5: Q1/Q3 rubric note
    add("## 5. Ghi chú phương pháp luận")
    add("")
    add("**Rubric Q1 & Q3 đã được sửa**: Trong rubric gốc của Li et al. (2024) Appendix A.3,")
    add("level 2 và level 4 của Q1 và Q3 bị đảo ngữ nghĩa so với chiều thang điểm (level 2 mô tả")
    add("hành vi liên minh TỐT, level 4 mô tả hành vi XẤU). Điều này gây ra artifact: hội thoại")
    add("có liên minh tốt nhưng không 'gọi tên' mục tiêu tường minh bị phạt xuống 2 điểm thay vì")
    add("được thưởng 4 điểm. Fix đã áp dụng: hoán đổi nội dung level 2 ↔ 4 trong Q1 và Q3.")
    add("")
    add("**n_runs = 1**: Kết quả này dùng n_runs=1 (1 LLM call/question thay vì 3) để giảm chi phí")
    add("token. Với temperature=0.3 thấp và model GPT-5.1 mạnh, variance giữa các run nhỏ; kết quả")
    add("pilot đủ để phân tích định hướng. Nên chạy lại với n_runs=3 cho kết quả chính thức.")
    add("")

    # Section 6: Charts
    add("## 6. Charts")
    add("")
    add("```")
    add("data/_analysis/wai/charts/")
    add("  01_dimension_heatmap.png    — heatmap 3 dims × 6 datasets")
    add("  02_per_question_heatmap.png — heatmap Q1-Q12 × 6 datasets")
    add("  03_strength_profile.png     — radar z-score strength profile")
    add("  04_ranking_bar.png          — grouped bar z-score per dimension")
    add("  05_boxplot_dims.png         — boxplot Total WAI per dataset")
    add("  06_total_bar.png            — horizontal bar Total mean ranked")
    add("```")
    add("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report written: {out_path}")


# ─────────────────────── S1 vs S3 COMPARISON ────────────────────────────────

def build_comparison_df(
    setting_a: str,
    setting_b: str,
    judge_name: str,
) -> pd.DataFrame:
    """
    Build a comparison DataFrame: delta = setting_a − setting_b per dataset × metric.

    Returns long-form DataFrame with columns:
        dataset, dataset_label, language, metric, mean_a, mean_b, delta
    where metric ∈ {Goal, Approach, Affective Bond, Total}.
    """
    rows = []
    for ds in DATASET_ORDER:
        recs_a = load_wai_judgments(ds, setting=setting_a, judge_name=judge_name)
        recs_b = load_wai_judgments(ds, setting=setting_b, judge_name=judge_name)
        if recs_a is None or recs_b is None:
            skipped = setting_a if recs_a is None else setting_b
            print(f"  [SKIP compare] {ds}: missing {skipped}_{judge_name} file")
            continue
        for metric in DIM_METRICS:
            if metric == "Total":
                vals_a = [r.get("total") for r in recs_a if r.get("total") is not None]
                vals_b = [r.get("total") for r in recs_b if r.get("total") is not None]
            else:
                vals_a = [r.get("dimensions", {}).get(metric)
                          for r in recs_a if r.get("dimensions", {}).get(metric) is not None]
                vals_b = [r.get("dimensions", {}).get(metric)
                          for r in recs_b if r.get("dimensions", {}).get(metric) is not None]
            if not vals_a or not vals_b:
                continue
            mean_a = float(np.mean(vals_a))
            mean_b = float(np.mean(vals_b))
            rows.append({
                "dataset":       ds,
                "dataset_label": DATASETS_META[ds]["label"],
                "language":      DATASETS_META[ds]["language"],
                "metric":        metric,
                "mean_a":        mean_a,
                "mean_b":        mean_b,
                "delta":         mean_a - mean_b,
            })
    return pd.DataFrame(rows)


def save_comparison_csv(
    cmp_df: pd.DataFrame,
    setting_a: str,
    setting_b: str,
    out_path: Path,
) -> None:
    """Save wide-format comparison table: rows=datasets, cols=metric × {mean_a, mean_b, delta}."""
    pivot = cmp_df.pivot_table(index="dataset", columns="metric",
                               values=["mean_a", "mean_b", "delta"], aggfunc="first")
    pivot = pivot.reindex([ds for ds in DATASET_ORDER if ds in cmp_df["dataset"].values])
    pivot.columns = [f"{col[1]}_{col[0].replace('mean_a', setting_a).replace('mean_b', setting_b)}"
                     for col in pivot.columns]
    pivot.index.name = "dataset"
    pivot.to_csv(out_path, float_format="%.4f")
    print(f"  Saved: {out_path.name}")


def chart_compare_heatmap(
    cmp_df: pd.DataFrame,
    setting_a: str,
    setting_b: str,
    out_path: Path,
) -> None:
    """
    Heatmap: rows=datasets, cols=DIM_METRICS, value=delta (setting_a − setting_b).

    Green = setting_a higher; red = setting_b higher.
    """
    pivot = cmp_df.pivot_table(index="dataset", columns="metric",
                               values="delta", aggfunc="first")
    pivot = pivot.reindex([ds for ds in DATASET_ORDER if ds in pivot.index],
                          columns=DIM_METRICS)
    pivot.index = [DATASETS_META[d]["label"] for d in pivot.index]

    vmax = max(0.5, float(pivot.abs().max().max()))
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        pivot,
        annot=True,
        fmt="+.2f",
        cmap="RdYlGn",
        center=0,
        vmin=-vmax, vmax=vmax,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": f"Delta ({setting_a} − {setting_b})"},
    )
    ax.set_title(
        f"WAI-O-S: {setting_a} vs {setting_b} Delta\n"
        f"(green = {setting_a} higher, red = {setting_b} higher)",
        fontsize=12, pad=10,
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_comparison_report(
    cmp_df: pd.DataFrame,
    setting_a: str,
    setting_b: str,
    judge_name: str,
    out_path: Path,
) -> None:
    """Generate markdown comparison report for two WAI settings."""
    lines: list[str] = []
    add = lines.append

    add(f"# WAI-O-S Comparison: {setting_a} vs {setting_b}")
    add("")
    add(f"**Settings**: {setting_a} (EN dialogue + EN judge) vs {setting_b} (native dialogue + EN judge)  ")
    add(f"**Judge**: {judge_name}  ")
    add(f"**Scale**: 1–5 (WAI-O-S)  ")
    add("")
    add(f"Delta = {setting_a} − {setting_b} (positive = {setting_a} higher).")
    add("")
    add("---")
    add("")

    add("## 1. Total WAI: Side-by-Side")
    add("")
    total_df = cmp_df[cmp_df["metric"] == "Total"].set_index("dataset")
    header = f"| Dataset | Language | {setting_a} | {setting_b} | Delta |"
    sep    = "|---|---|---|---|---|"
    add(header); add(sep)
    for ds in DATASET_ORDER:
        if ds not in total_df.index:
            continue
        row = total_df.loc[ds]
        lang = DATASETS_META[ds]["language"]
        add(f"| {row['dataset_label']} | {lang} | {row['mean_a']:.3f} | "
            f"{row['mean_b']:.3f} | {row['delta']:+.3f} |")
    add("")

    add("## 2. Dimension Deltas")
    add("")
    add(f"| Dataset | Goal Δ | Approach Δ | Bond Δ | Total Δ |")
    add("|---|---|---|---|---|")
    for ds in DATASET_ORDER:
        ds_rows = cmp_df[cmp_df["dataset"] == ds].set_index("metric")
        if ds_rows.empty:
            continue
        label = DATASETS_META[ds]["label"]
        deltas = {m: ds_rows.loc[m, "delta"] if m in ds_rows.index else float("nan")
                  for m in DIM_METRICS}
        add(f"| {label} | {deltas['Goal']:+.3f} | {deltas['Approach']:+.3f} | "
            f"{deltas['Affective Bond']:+.3f} | {deltas['Total']:+.3f} |")
    add("")

    add("## 3. Interpretation")
    add("")
    total_df2 = cmp_df[cmp_df["metric"] == "Total"]
    if not total_df2.empty:
        mean_delta = total_df2["delta"].mean()
        max_row = total_df2.loc[total_df2["delta"].abs().idxmax()]
        add(f"- **Mean delta** across datasets: {mean_delta:+.3f}")
        add(f"- **Largest divergence**: {max_row['dataset_label']} "
            f"(Δ = {max_row['delta']:+.3f})")
        non_en = total_df2[total_df2["language"] != "en"]
        if not non_en.empty:
            add(f"- **Non-EN mean delta**: {non_en['delta'].mean():+.3f} "
                f"(translation effect for ZH/KO datasets)")
    add("")
    add("*S1 uses EN-translated dialogue; S3 uses original-language dialogue.*  ")
    add("*Near-zero delta → translation does not substantially change WAI score.*")
    add("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Comparison report written: {out_path}")


# ─────────────────────── MAIN ────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze WAI-O-S results")
    parser.add_argument("--output_dir", default="data/_analysis/wai",
                        help="Output directory (default: data/_analysis/wai)")
    parser.add_argument("--judge_name", default="gpt",
                        help="Judge name in filename (default: gpt)")
    parser.add_argument("--setting", default="S3",
                        help="Single setting to analyze (default: S3)")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare two settings (--setting_a vs --setting_b). "
             "Generates delta table and comparison chart in addition to the main report.",
    )
    parser.add_argument("--setting_a", default="S1",
                        help="First setting for comparison (default: S1)")
    parser.add_argument("--setting_b", default="S3",
                        help="Second setting for comparison (default: S3)")
    args = parser.parse_args()

    root    = Path(__file__).resolve().parents[2]
    out_dir = root / args.output_dir
    tables_dir = out_dir / "tables"
    charts_dir = out_dir / "charts"
    tables_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("WAI-O-S Analysis")
    print(f"{'='*60}")
    print(f"Setting  : {args.setting}")
    print(f"Judge    : {args.judge_name}")
    print(f"Output   : {out_dir}")
    if args.compare:
        print(f"Compare  : {args.setting_a} vs {args.setting_b}")
    print(f"{'='*60}\n")

    # ── Load data ──────────────────────────────────────────────────────────
    print("Loading data...")
    df = build_long_df(setting=args.setting, judge_name=args.judge_name)

    if df.empty:
        print("ERROR: No data loaded. Check that WAI result files exist.")
        return

    n_datasets = df["dataset"].nunique()
    n_records  = df.groupby("dataset").size().min()
    print(f"\nLoaded: {len(df)} rows across {n_datasets} datasets")
    print(f"Records per dataset: {dict(df.groupby('dataset').size())}")

    # ── Compute tables ─────────────────────────────────────────────────────
    print("\nComputing summary tables...")
    mean_df, std_df = compute_raw_means(df)
    z_df            = compute_z_scores(mean_df)
    q_means         = compute_per_question_means(df)

    # Save tables
    summary = mean_df.copy()
    summary.index.name = "dataset"
    summary.to_csv(tables_dir / "summary_raw_means.csv", float_format="%.4f")
    print(f"  Saved: tables/summary_raw_means.csv")

    z_out = z_df.copy()
    z_out.index.name = "dataset"
    z_out.to_csv(tables_dir / "ranking_S3.csv", float_format="%.4f")
    print(f"  Saved: tables/ranking_S3.csv")

    q_out = q_means.copy()
    q_out.index.name = "dataset"
    q_out.to_csv(tables_dir / "per_question_means.csv", float_format="%.4f")
    print(f"  Saved: tables/per_question_means.csv")

    # ── Generate charts ────────────────────────────────────────────────────
    print("\nGenerating charts...")

    chart_dimension_heatmap(mean_df, charts_dir / "01_dimension_heatmap.png")
    print("  Chart 1: dimension heatmap")

    chart_per_question_heatmap(q_means, charts_dir / "02_per_question_heatmap.png")
    print("  Chart 2: per-question heatmap")

    chart_strength_profile(z_df, charts_dir / "03_strength_profile.png")
    print("  Chart 3: strength profile radar")

    chart_ranking_bar(z_df, charts_dir / "04_ranking_bar.png")
    print("  Chart 4: ranking bar")

    chart_boxplot(df, charts_dir / "05_boxplot_dims.png")
    print("  Chart 5: boxplot total")

    chart_total_bar(mean_df, std_df, charts_dir / "06_total_bar.png")
    print("  Chart 6: total bar ranked")

    # ── Generate report ────────────────────────────────────────────────────
    print("\nGenerating report...")
    generate_report(
        mean_df=mean_df,
        std_df=std_df,
        z_df=z_df,
        q_means=q_means,
        df=df,
        setting=args.setting,
        judge_name=args.judge_name,
        n_records=n_records,
        out_path=out_dir / "report.md",
    )

    # ── S1 vs S3 comparison (optional) ────────────────────────────────────
    if args.compare:
        sa, sb = args.setting_a, args.setting_b
        print(f"\nComparison: {sa} vs {sb}")
        cmp_df = build_comparison_df(sa, sb, judge_name=args.judge_name)
        if cmp_df.empty:
            print(f"  [SKIP] No datasets have both {sa} and {sb} WAI files.")
        else:
            print(f"  {cmp_df['dataset'].nunique()} datasets with both settings")
            save_comparison_csv(cmp_df, sa, sb,
                                out_path=tables_dir / f"compare_{sa}_vs_{sb}.csv")
            chart_compare_heatmap(cmp_df, sa, sb,
                                  out_path=charts_dir / f"07_compare_{sa}_vs_{sb}_heatmap.png")
            print(f"  Chart 7: delta heatmap {sa} vs {sb}")
            generate_comparison_report(
                cmp_df, sa, sb,
                judge_name=args.judge_name,
                out_path=out_dir / f"report_compare_{sa}_vs_{sb}.md",
            )

    # ── Print summary ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Total WAI Score Ranking (S3):")
    print(f"{'='*60}")
    ranked = mean_df["Total"].sort_values(ascending=False)
    for i, (ds, score) in enumerate(ranked.items(), 1):
        label = DATASETS_META.get(ds, {}).get("label", ds)
        std   = std_df.loc[ds, "Total"]
        mr    = z_df.loc[ds, "mean_rank"]
        print(f"  #{i}  {label:<14s}  Total={score:.3f} ±{std:.3f}  mean-rank={mr:.1f}")

    print(f"\nZ-score Dimension Ranking:")
    print(f"{'Dataset':<14} {'Goal':>7} {'Approach':>9} {'Bond':>7} {'mean-rank':>10}")
    for ds in z_df.sort_values("mean_rank").index:
        label = DATASETS_META.get(ds, {}).get("label", ds)
        g  = z_df.loc[ds, "Goal"]
        ap = z_df.loc[ds, "Approach"]
        ab = z_df.loc[ds, "Affective Bond"]
        mr = z_df.loc[ds, "mean_rank"]
        print(f"  {label:<14} {g:+.2f}   {ap:+.2f}    {ab:+.2f}   {mr:>6.1f}")

    print(f"\n{'='*60}")
    print(f"Output: {out_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
