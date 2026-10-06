"""
Analyze SimPsyDial evaluation results from Mind-Eval judgments.

This script provides comprehensive analysis of SimPsyDial dialogues evaluated
using the Mind-Eval framework, including:
- Basic statistics (mean, std, distribution)
- Per-criterion analysis
- Comparison with Mind-Eval baseline (if available)
- Translation quality comparison (GPT-4 vs Google Translate)
- Visualization and reporting

Usage:
    # Basic analysis
    python mindeval/scripts/analyze_simpsydial.py \
        --judgments_path data/simpsydial/judgments/judgments_pilot.jsonl \
        --output_dir data/simpsydial/analysis

    # Compare translation methods
    python mindeval/scripts/analyze_simpsydial.py \
        --judgments_path data/simpsydial/judgments/judgments_gpt4.jsonl \
        --comparison_judgments_path data/simpsydial/judgments/judgments_google.jsonl \
        --output_dir data/simpsydial/analysis \
        --comparison_label "Google Translate"

    # Compare with Mind-Eval baseline
    python mindeval/scripts/analyze_simpsydial.py \
        --judgments_path data/simpsydial/judgments/judgments_full.jsonl \
        --baseline_judgments_path data/mindeval_baseline.jsonl \
        --output_dir data/simpsydial/analysis
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import matplotlib.pyplot as plt
import seaborn as sns

from mindeval.utils import load_jsonl
from mindeval.significance_testing import rank_systems, build_head_to_heads


def extract_scores(judgments: List[Dict]) -> pd.DataFrame:
    """
    Extract scores from judgments into DataFrame.
    
    Args:
        judgments: List of judgment dicts with 'parsed_judgment' field
        
    Returns:
        DataFrame with scores for each criterion
    """
    scores = [j['parsed_judgment'] for j in judgments]
    df = pd.DataFrame(scores)
    
    # Ensure all expected columns exist
    expected_columns = [
        "Clinical Accuracy & Competence",
        "Ethical & Professional Conduct",
        "Assessment & Response",
        "Therapeutic Relationship & Alliance",
        "AI-Specific Communication Quality",
        "Overall score"
    ]
    
    for col in expected_columns:
        if col not in df.columns:
            print(f"Warning: Missing column '{col}', setting to NaN")
            df[col] = np.nan
    
    return df[expected_columns]


def compute_basic_statistics(df: pd.DataFrame) -> Dict:
    """
    Compute basic statistics for scores.
    
    Returns:
        Dict with mean, std, min, max, median for each criterion
    """
    stats = {
        "mean": df.mean().to_dict(),
        "std": df.std().to_dict(),
        "min": df.min().to_dict(),
        "max": df.max().to_dict(),
        "median": df.median().to_dict(),
        "n_dialogues": len(df)
    }
    return stats


def print_basic_analysis(df: pd.DataFrame, label: str = "SimPsyDial"):
    """Print basic analysis to console."""
    print(f"\n{'='*80}")
    print(f"  {label} EVALUATION RESULTS")
    print(f"{'='*80}\n")
    
    print(f"Number of dialogues: {len(df)}\n")
    
    print("Average Scores:")
    print("-" * 60)
    for col in df.columns:
        mean = df[col].mean()
        std = df[col].std()
        print(f"  {col:50s}: {mean:.2f} ± {std:.2f}")
    
    print("\n" + "="*80 + "\n")
    
    print("Score Distribution:")
    print("-" * 60)
    print(df.describe().round(2))
    
    print("\n" + "="*80 + "\n")
    
    print("Per-Criterion Analysis:")
    print("-" * 60)
    for col in df.columns:
        if col == "Overall score":
            continue
        print(f"\n{col}:")
        print(f"  Mean:   {df[col].mean():.2f}")
        print(f"  Median: {df[col].median():.2f}")
        print(f"  Std:    {df[col].std():.2f}")
        print(f"  Min:    {df[col].min():.2f}")
        print(f"  Max:    {df[col].max():.2f}")
        
        # Score distribution
        score_counts = df[col].value_counts().sort_index()
        print(f"  Distribution:")
        for score, count in score_counts.items():
            pct = count / len(df) * 100
            print(f"    {score:.1f}: {count:3d} ({pct:5.1f}%)")


def compare_with_baseline(
    simpsydial_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    output_dir: Path
):
    """
    Compare SimPsyDial scores with Mind-Eval baseline.
    
    Args:
        simpsydial_df: SimPsyDial scores
        baseline_df: Mind-Eval baseline scores
        output_dir: Output directory for results
    """
    print("\n" + "="*80)
    print("  COMPARISON WITH MIND-EVAL BASELINE")
    print("="*80 + "\n")
    
    # Ensure same length for comparison
    min_len = min(len(simpsydial_df), len(baseline_df))
    simpsydial_subset = simpsydial_df.iloc[:min_len]
    baseline_subset = baseline_df.iloc[:min_len]
    
    # Combine into single DataFrame
    comparison_df = pd.DataFrame({
        'SimPsyDial': simpsydial_subset['Overall score'].values,
        'MindEval_Baseline': baseline_subset['Overall score'].values
    })
    
    # Statistical comparison
    print("Overall Score Comparison:")
    print("-" * 60)
    print(f"  SimPsyDial:        {comparison_df['SimPsyDial'].mean():.2f} ± {comparison_df['SimPsyDial'].std():.2f}")
    print(f"  MindEval Baseline: {comparison_df['MindEval_Baseline'].mean():.2f} ± {comparison_df['MindEval_Baseline'].std():.2f}")
    
    # Head-to-head comparison
    try:
        head_to_heads = build_head_to_heads(comparison_df)
        print("\nHead-to-Head Comparison:")
        print("-" * 60)
        print(head_to_heads)
        
        # Save to file
        with open(output_dir / "head_to_head_comparison.txt", 'w') as f:
            f.write(str(head_to_heads))
    except Exception as e:
        print(f"Warning: Could not compute head-to-head comparison: {e}")
    
    # Rankings
    try:
        rankings = rank_systems(comparison_df, bootstrap_resampling=True)
        print("\nSystem Rankings:")
        print("-" * 60)
        print(rankings)
        
        # Save to file
        rankings.to_csv(output_dir / "system_rankings.csv")
    except Exception as e:
        print(f"Warning: Could not compute rankings: {e}")
    
    # Per-criterion comparison
    print("\nPer-Criterion Comparison:")
    print("-" * 60)
    criteria = [col for col in simpsydial_df.columns if col != "Overall score"]
    
    criterion_comparison = []
    for criterion in criteria:
        simpsydial_mean = simpsydial_subset[criterion].mean()
        baseline_mean = baseline_subset[criterion].mean()
        diff = simpsydial_mean - baseline_mean
        
        criterion_comparison.append({
            "Criterion": criterion,
            "SimPsyDial": simpsydial_mean,
            "Baseline": baseline_mean,
            "Difference": diff
        })
        
        print(f"\n{criterion}:")
        print(f"  SimPsyDial: {simpsydial_mean:.2f}")
        print(f"  Baseline:   {baseline_mean:.2f}")
        print(f"  Difference: {diff:+.2f}")
    
    # Save comparison
    criterion_df = pd.DataFrame(criterion_comparison)
    criterion_df.to_csv(output_dir / "criterion_comparison.csv", index=False)


def compare_translation_methods(
    method1_df: pd.DataFrame,
    method2_df: pd.DataFrame,
    method1_label: str,
    method2_label: str,
    output_dir: Path
):
    """
    Compare two translation methods (e.g., GPT-4 vs Google Translate).
    
    Args:
        method1_df: Scores from first translation method
        method2_df: Scores from second translation method
        method1_label: Label for first method
        method2_label: Label for second method
        output_dir: Output directory for results
    """
    print("\n" + "="*80)
    print(f"  TRANSLATION METHOD COMPARISON: {method1_label} vs {method2_label}")
    print("="*80 + "\n")
    
    # Overall comparison
    print("Overall Score Comparison:")
    print("-" * 60)
    print(f"  {method1_label:20s}: {method1_df['Overall score'].mean():.2f} ± {method1_df['Overall score'].std():.2f}")
    print(f"  {method2_label:20s}: {method2_df['Overall score'].mean():.2f} ± {method2_df['Overall score'].std():.2f}")
    
    diff = method1_df['Overall score'].mean() - method2_df['Overall score'].mean()
    print(f"  Difference:          {diff:+.2f}")
    
    # Per-criterion comparison
    print("\nPer-Criterion Comparison:")
    print("-" * 60)
    
    comparison_data = []
    criteria = [col for col in method1_df.columns if col != "Overall score"]
    
    for criterion in criteria:
        mean1 = method1_df[criterion].mean()
        mean2 = method2_df[criterion].mean()
        diff = mean1 - mean2
        
        comparison_data.append({
            "Criterion": criterion,
            method1_label: mean1,
            method2_label: mean2,
            "Difference": diff
        })
        
        print(f"\n{criterion}:")
        print(f"  {method1_label:20s}: {mean1:.2f}")
        print(f"  {method2_label:20s}: {mean2:.2f}")
        print(f"  Difference:          {diff:+.2f}")
    
    # Save comparison
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(output_dir / "translation_comparison.csv", index=False)
    
    # Recommendation
    print("\n" + "="*80)
    print("  RECOMMENDATION")
    print("="*80 + "\n")
    
    if abs(diff) < 0.1:
        print("The two translation methods produce very similar results.")
        print("Recommendation: Use the more cost-effective method (Google Translate).")
    elif diff > 0:
        print(f"{method1_label} produces higher scores (+{diff:.2f}).")
        print(f"Recommendation: Review sample translations to determine which is more accurate.")
    else:
        print(f"{method2_label} produces higher scores (+{-diff:.2f}).")
        print(f"Recommendation: Review sample translations to determine which is more accurate.")


def create_visualizations(df: pd.DataFrame, output_dir: Path, label: str = "SimPsyDial"):
    """
    Create visualization plots for scores.
    
    Args:
        df: Scores DataFrame
        output_dir: Output directory for plots
        label: Label for the dataset
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        sns.set_style("whitegrid")
        
        # 1. Box plot for all criteria
        fig, ax = plt.subplots(figsize=(12, 6))
        criteria = [col for col in df.columns if col != "Overall score"]
        df[criteria].boxplot(ax=ax, rot=45)
        ax.set_title(f"{label} - Score Distribution by Criterion")
        ax.set_ylabel("Score (1-6)")
        plt.tight_layout()
        plt.savefig(output_dir / "score_distribution.png", dpi=300)
        plt.close()
        
        # 2. Histogram for overall score
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(df['Overall score'], bins=20, edgecolor='black', alpha=0.7)
        ax.set_title(f"{label} - Overall Score Distribution")
        ax.set_xlabel("Overall Score")
        ax.set_ylabel("Frequency")
        ax.axvline(df['Overall score'].mean(), color='red', linestyle='--', 
                   label=f"Mean: {df['Overall score'].mean():.2f}")
        ax.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "overall_score_histogram.png", dpi=300)
        plt.close()
        
        # 3. Heatmap of score correlations
        fig, ax = plt.subplots(figsize=(10, 8))
        corr = df[criteria].corr()
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=ax)
        ax.set_title(f"{label} - Criterion Correlation Matrix")
        plt.tight_layout()
        plt.savefig(output_dir / "correlation_heatmap.png", dpi=300)
        plt.close()
        
        print(f"\n✓ Visualizations saved to {output_dir}")
        
    except ImportError:
        print("\nWarning: matplotlib/seaborn not installed. Skipping visualizations.")
        print("Install with: pip install matplotlib seaborn")


def main(
    judgments_path: str,
    output_dir: str,
    comparison_judgments_path: Optional[str] = None,
    comparison_label: Optional[str] = "Comparison",
    baseline_judgments_path: Optional[str] = None,
    create_plots: bool = True
):
    """
    Analyze SimPsyDial evaluation results.
    
    Args:
        judgments_path: Path to judgments JSONL file
        output_dir: Output directory for analysis results
        comparison_judgments_path: Optional path to comparison judgments (e.g., different translation)
        comparison_label: Label for comparison dataset
        baseline_judgments_path: Optional path to Mind-Eval baseline judgments
        create_plots: Whether to create visualization plots
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load judgments
    print(f"Loading judgments from {judgments_path}...")
    judgments = load_jsonl(judgments_path)
    df = extract_scores(judgments)
    
    # Basic analysis
    print_basic_analysis(df, label="SimPsyDial")
    
    # Save basic statistics
    stats = compute_basic_statistics(df)
    with open(output_path / "summary_statistics.json", 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n✓ Summary statistics saved to {output_path / 'summary_statistics.json'}")
    
    # Save detailed scores
    df.to_csv(output_path / "detailed_scores.csv", index=False)
    print(f"✓ Detailed scores saved to {output_path / 'detailed_scores.csv'}")
    
    # Comparison with another translation method
    if comparison_judgments_path:
        print(f"\nLoading comparison judgments from {comparison_judgments_path}...")
        comparison_judgments = load_jsonl(comparison_judgments_path)
        comparison_df = extract_scores(comparison_judgments)
        
        compare_translation_methods(
            df, comparison_df,
            "Primary Method", comparison_label,
            output_path
        )
    
    # Comparison with baseline
    if baseline_judgments_path:
        print(f"\nLoading baseline judgments from {baseline_judgments_path}...")
        baseline_judgments = load_jsonl(baseline_judgments_path)
        baseline_df = extract_scores(baseline_judgments)
        
        compare_with_baseline(df, baseline_df, output_path)
    
    # Create visualizations
    if create_plots:
        print("\nCreating visualizations...")
        create_visualizations(df, output_path)
    
    # Generate summary report
    report_path = output_path / "analysis_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# SimPsyDial Evaluation Analysis Report\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Number of dialogues**: {len(df)}\n")
        f.write(f"- **Overall score**: {df['Overall score'].mean():.2f} ± {df['Overall score'].std():.2f}\n")
        f.write(f"- **Score range**: {df['Overall score'].min():.2f} - {df['Overall score'].max():.2f}\n\n")
        
        f.write(f"## Average Scores by Criterion\n\n")
        f.write("| Criterion | Mean | Std | Min | Max |\n")
        f.write("|-----------|------|-----|-----|-----|\n")
        for col in df.columns:
            f.write(f"| {col} | {df[col].mean():.2f} | {df[col].std():.2f} | "
                   f"{df[col].min():.2f} | {df[col].max():.2f} |\n")
        
        f.write(f"\n## Files Generated\n\n")
        f.write(f"- `summary_statistics.json`: Basic statistics\n")
        f.write(f"- `detailed_scores.csv`: All scores in CSV format\n")
        if create_plots:
            f.write(f"- `score_distribution.png`: Box plot of score distribution\n")
            f.write(f"- `overall_score_histogram.png`: Histogram of overall scores\n")
            f.write(f"- `correlation_heatmap.png`: Correlation matrix heatmap\n")
        if comparison_judgments_path:
            f.write(f"- `translation_comparison.csv`: Translation method comparison\n")
        if baseline_judgments_path:
            f.write(f"- `criterion_comparison.csv`: Comparison with baseline\n")
            f.write(f"- `system_rankings.csv`: System rankings\n")
    
    print(f"\n✓ Analysis report saved to {report_path}")
    print(f"\n{'='*80}")
    print("  ANALYSIS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([main], as_positional=False)
