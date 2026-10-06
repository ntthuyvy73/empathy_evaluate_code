"""
Compare results from three evaluation methods (Options A, B, C).

This script analyzes and compares the evaluation results from:
- Option A: Translated dialogues + English judge
- Option B: Original language dialogues + Translated judge
- Option C: Bilingual evaluation

Usage:
    python mindeval/scripts/compare_evaluation_methods.py \
        --option_a_path data/simpsydial/three_way/option_a_judgments.jsonl \
        --option_b_path data/simpsydial/three_way/option_b_judgments.jsonl \
        --option_c_path data/simpsydial/three_way/option_c_judgments.jsonl \
        --output_dir data/simpsydial/three_way/comparison
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from scipy import stats

from mindeval.utils import load_jsonl


def load_all_judgments(
    option_a_path: Optional[str],
    option_b_path: Optional[str],
    option_c_path: Optional[str]
) -> Dict[str, pd.DataFrame]:
    """
    Load judgments from all three options.
    
    Returns:
        Dict mapping option name to DataFrame of scores
    """
    results = {}
    
    if option_a_path:
        judgments_a = load_jsonl(option_a_path)
        scores_a = [j['parsed_judgment'] for j in judgments_a]
        results['Option A (Translate Dialogue)'] = pd.DataFrame(scores_a)
    
    if option_b_path:
        judgments_b = load_jsonl(option_b_path)
        scores_b = [j['parsed_judgment'] for j in judgments_b]
        results['Option B (Translate Judge)'] = pd.DataFrame(scores_b)
    
    if option_c_path:
        judgments_c = load_jsonl(option_c_path)
        scores_c = [j['parsed_judgment'] for j in judgments_c]
        results['Option C (Bilingual)'] = pd.DataFrame(scores_c)
    
    return results


def compute_correlations(scores_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute correlations between options.
    
    Returns:
        DataFrame with correlation matrix
    """
    options = list(scores_dict.keys())
    n_options = len(options)
    
    # Create correlation matrix
    corr_matrix = pd.DataFrame(
        index=options,
        columns=options,
        dtype=float
    )
    
    for i, opt1 in enumerate(options):
        for j, opt2 in enumerate(options):
            if i == j:
                corr_matrix.loc[opt1, opt2] = 1.0
            elif i < j:
                # Compute correlation on Overall score
                scores1 = scores_dict[opt1]['Overall score']
                scores2 = scores_dict[opt2]['Overall score']
                
                corr, pval = stats.pearsonr(scores1, scores2)
                corr_matrix.loc[opt1, opt2] = corr
                corr_matrix.loc[opt2, opt1] = corr
    
    return corr_matrix


def compute_agreement_stats(
    scores_dict: Dict[str, pd.DataFrame]
) -> Dict[str, Dict]:
    """
    Compute agreement statistics between options.
    
    Returns:
        Dict with agreement metrics
    """
    options = list(scores_dict.keys())
    agreements = {}
    
    for i, opt1 in enumerate(options):
        for j, opt2 in enumerate(options):
            if i < j:
                key = f"{opt1} vs {opt2}"
                
                scores1 = scores_dict[opt1]['Overall score']
                scores2 = scores_dict[opt2]['Overall score']
                
                # Mean absolute difference
                mad = np.mean(np.abs(scores1 - scores2))
                
                # Percentage within 0.5 points
                within_half = np.mean(np.abs(scores1 - scores2) <= 0.5) * 100
                
                # Paired t-test
                tstat, pval = stats.ttest_rel(scores1, scores2)
                
                agreements[key] = {
                    "mean_absolute_difference": mad,
                    "percent_within_0.5": within_half,
                    "t_statistic": tstat,
                    "p_value": pval,
                    "significant_difference": pval < 0.05
                }
    
    return agreements


def analyze_per_criterion(
    scores_dict: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Analyze differences per criterion.
    
    Returns:
        DataFrame with mean scores per criterion per option
    """
    criteria = [
        "Clinical Accuracy & Competence",
        "Ethical & Professional Conduct",
        "Assessment & Response",
        "Therapeutic Relationship & Alliance",
        "AI-Specific Communication Quality",
        "Overall score"
    ]
    
    results = []
    
    for criterion in criteria:
        row = {"Criterion": criterion}
        for option_name, scores_df in scores_dict.items():
            if criterion in scores_df.columns:
                row[option_name] = scores_df[criterion].mean()
        results.append(row)
    
    return pd.DataFrame(results)


def identify_discrepancies(
    scores_dict: Dict[str, pd.DataFrame],
    threshold: float = 1.0
) -> List[Dict]:
    """
    Identify dialogues with large score discrepancies.
    
    Args:
        threshold: Minimum difference to flag as discrepancy
        
    Returns:
        List of discrepancy cases
    """
    options = list(scores_dict.keys())
    if len(options) < 2:
        return []
    
    discrepancies = []
    
    # Compare first two options
    opt1, opt2 = options[0], options[1]
    scores1 = scores_dict[opt1]['Overall score']
    scores2 = scores_dict[opt2]['Overall score']
    
    for idx in range(len(scores1)):
        diff = abs(scores1.iloc[idx] - scores2.iloc[idx])
        
        if diff >= threshold:
            discrepancies.append({
                "dialogue_index": idx,
                f"{opt1}_score": scores1.iloc[idx],
                f"{opt2}_score": scores2.iloc[idx],
                "difference": diff
            })
    
    # Sort by difference
    discrepancies.sort(key=lambda x: x['difference'], reverse=True)
    
    return discrepancies


def create_visualizations(
    scores_dict: Dict[str, pd.DataFrame],
    output_dir: Path
):
    """Create comparison visualizations."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        sns.set_style("whitegrid")
        
        # 1. Box plot comparison
        fig, ax = plt.subplots(figsize=(12, 6))
        
        data_for_plot = []
        for option_name, scores_df in scores_dict.items():
            for score in scores_df['Overall score']:
                data_for_plot.append({
                    "Option": option_name,
                    "Overall Score": score
                })
        
        plot_df = pd.DataFrame(data_for_plot)
        sns.boxplot(data=plot_df, x="Option", y="Overall Score", ax=ax)
        ax.set_title("Overall Score Distribution by Evaluation Method")
        ax.set_ylabel("Overall Score (1-6)")
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        plt.savefig(output_dir / "score_distribution_comparison.png", dpi=300)
        plt.close()
        
        # 2. Scatter plot (if 2+ options)
        if len(scores_dict) >= 2:
            options = list(scores_dict.keys())
            opt1, opt2 = options[0], options[1]
            
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.scatter(
                scores_dict[opt1]['Overall score'],
                scores_dict[opt2]['Overall score'],
                alpha=0.6
            )
            ax.plot([1, 6], [1, 6], 'r--', label='Perfect agreement')
            ax.set_xlabel(f"{opt1} Score")
            ax.set_ylabel(f"{opt2} Score")
            ax.set_title(f"Score Agreement: {opt1} vs {opt2}")
            ax.legend()
            ax.set_xlim(1, 6)
            ax.set_ylim(1, 6)
            plt.tight_layout()
            plt.savefig(output_dir / "score_agreement_scatter.png", dpi=300)
            plt.close()
        
        # 3. Per-criterion comparison
        criteria = [
            "Clinical Accuracy & Competence",
            "Ethical & Professional Conduct",
            "Assessment & Response",
            "Therapeutic Relationship & Alliance",
            "AI-Specific Communication Quality"
        ]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(criteria))
        width = 0.25
        
        for i, (option_name, scores_df) in enumerate(scores_dict.items()):
            means = [scores_df[c].mean() for c in criteria]
            ax.bar(x + i*width, means, width, label=option_name, alpha=0.8)
        
        ax.set_xlabel('Criterion')
        ax.set_ylabel('Mean Score')
        ax.set_title('Mean Scores by Criterion and Evaluation Method')
        ax.set_xticks(x + width)
        ax.set_xticklabels([c.replace(' & ', '\n& ') for c in criteria], rotation=0, ha='center', fontsize=9)
        ax.legend()
        ax.set_ylim(1, 6)
        plt.tight_layout()
        plt.savefig(output_dir / "criterion_comparison.png", dpi=300)
        plt.close()
        
        print(f"\n✓ Visualizations saved to {output_dir}")
        
    except ImportError:
        print("\nWarning: matplotlib/seaborn not installed. Skipping visualizations.")


def generate_report(
    scores_dict: Dict[str, pd.DataFrame],
    correlations: pd.DataFrame,
    agreements: Dict,
    per_criterion: pd.DataFrame,
    discrepancies: List[Dict],
    output_dir: Path
):
    """Generate comprehensive comparison report."""
    
    report_path = output_dir / "comparison_report.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Three-Way Evaluation Method Comparison Report\n\n")
        
        # Summary statistics
        f.write("## 1. Summary Statistics\n\n")
        f.write("| Method | N | Mean | Std | Min | Max |\n")
        f.write("|--------|---|------|-----|-----|-----|\n")
        
        for option_name, scores_df in scores_dict.items():
            overall = scores_df['Overall score']
            f.write(f"| {option_name} | {len(overall)} | "
                   f"{overall.mean():.2f} | {overall.std():.2f} | "
                   f"{overall.min():.2f} | {overall.max():.2f} |\n")
        
        # Correlations
        f.write("\n## 2. Inter-Method Correlations\n\n")
        f.write("Pearson correlation coefficients between methods:\n\n")
        f.write(correlations.to_markdown())
        f.write("\n\n")
        
        # Interpretation
        f.write("**Interpretation:**\n")
        if len(scores_dict) >= 2:
            options = list(scores_dict.keys())
            for i, opt1 in enumerate(options):
                for j, opt2 in enumerate(options):
                    if i < j:
                        corr = correlations.loc[opt1, opt2]
                        f.write(f"- {opt1} vs {opt2}: r = {corr:.3f}")
                        if corr > 0.8:
                            f.write(" (Strong agreement)\n")
                        elif corr > 0.6:
                            f.write(" (Moderate agreement)\n")
                        else:
                            f.write(" (Weak agreement)\n")
        
        # Agreement statistics
        f.write("\n## 3. Agreement Statistics\n\n")
        
        for comparison, stats in agreements.items():
            f.write(f"### {comparison}\n\n")
            f.write(f"- Mean Absolute Difference: {stats['mean_absolute_difference']:.3f}\n")
            f.write(f"- Scores within 0.5 points: {stats['percent_within_0.5']:.1f}%\n")
            f.write(f"- Paired t-test: t = {stats['t_statistic']:.3f}, p = {stats['p_value']:.4f}\n")
            
            if stats['significant_difference']:
                f.write(f"- **Significant difference detected** (p < 0.05)\n")
            else:
                f.write(f"- No significant difference (p >= 0.05)\n")
            f.write("\n")
        
        # Per-criterion analysis
        f.write("\n## 4. Per-Criterion Comparison\n\n")
        f.write(per_criterion.to_markdown(index=False))
        f.write("\n\n")
        
        # Discrepancies
        if discrepancies:
            f.write("\n## 5. Large Discrepancies (>1.0 point difference)\n\n")
            f.write(f"Found {len(discrepancies)} dialogues with large score differences:\n\n")
            f.write("| Dialogue | Option A | Option B | Difference |\n")
            f.write("|----------|----------|----------|------------|\n")
            
            for disc in discrepancies[:10]:  # Top 10
                f.write(f"| {disc['dialogue_index']} | ")
                
                for key, val in disc.items():
                    if 'score' in key or key == 'difference':
                        f.write(f"{val:.2f} | ")
                f.write("\n")
        
        # Recommendations
        f.write("\n## 6. Recommendations\n\n")
        
        if len(scores_dict) >= 2:
            options = list(scores_dict.keys())
            opt1, opt2 = options[0], options[1]
            corr = correlations.loc[opt1, opt2]
            
            if corr > 0.8:
                f.write(f"✅ **High agreement** between methods (r = {corr:.3f})\n\n")
                f.write("**Recommendation:** Any method can be used. Choose based on:\n")
                f.write("- Cost: Option B is cheapest (no dialogue translation)\n")
                f.write("- Comparability: Option A allows comparison with English baselines\n")
                f.write("- Accuracy: Option C preserves most cultural context\n")
            
            elif corr > 0.6:
                f.write(f"⚠️ **Moderate agreement** between methods (r = {corr:.3f})\n\n")
                f.write("**Recommendation:** Methods show some differences. Consider:\n")
                f.write("- Using Option A for cross-dataset comparison\n")
                f.write("- Using Option C for highest accuracy\n")
                f.write("- Investigating discrepancy cases to understand differences\n")
            
            else:
                f.write(f"❌ **Low agreement** between methods (r = {corr:.3f})\n\n")
                f.write("**Recommendation:** Methods produce substantially different results.\n")
                f.write("- Review translation quality (Option A)\n")
                f.write("- Validate translated judge prompt (Option B)\n")
                f.write("- Check bilingual prompt effectiveness (Option C)\n")
                f.write("- Consider using multiple methods and triangulating results\n")
    
    print(f"\n✓ Comparison report saved to {report_path}")


def main(
    option_a_path: Optional[str] = None,
    option_b_path: Optional[str] = None,
    option_c_path: Optional[str] = None,
    output_dir: str = "comparison_results",
    create_plots: bool = True
):
    """
    Compare evaluation results from three methods.
    
    Args:
        option_a_path: Path to Option A judgments
        option_b_path: Path to Option B judgments
        option_c_path: Path to Option C judgments
        output_dir: Output directory for comparison results
        create_plots: Whether to create visualization plots
    """
    if not any([option_a_path, option_b_path, option_c_path]):
        raise ValueError("At least one option path must be provided")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("  EVALUATION METHOD COMPARISON")
    print("="*80 + "\n")
    
    # Load judgments
    print("Loading judgments...")
    scores_dict = load_all_judgments(option_a_path, option_b_path, option_c_path)
    
    print(f"Loaded {len(scores_dict)} evaluation methods:")
    for name, df in scores_dict.items():
        print(f"  - {name}: {len(df)} dialogues")
    
    # Compute correlations
    print("\nComputing correlations...")
    correlations = compute_correlations(scores_dict)
    print("\nCorrelation Matrix:")
    print(correlations.round(3))
    
    # Compute agreement statistics
    print("\nComputing agreement statistics...")
    agreements = compute_agreement_stats(scores_dict)
    
    # Per-criterion analysis
    print("\nAnalyzing per-criterion differences...")
    per_criterion = analyze_per_criterion(scores_dict)
    print("\nMean Scores by Criterion:")
    print(per_criterion.round(2))
    
    # Identify discrepancies
    print("\nIdentifying large discrepancies...")
    discrepancies = identify_discrepancies(scores_dict, threshold=1.0)
    print(f"Found {len(discrepancies)} dialogues with >1.0 point difference")
    
    # Save results
    print("\nSaving results...")
    
    correlations.to_csv(output_path / "correlations.csv")
    per_criterion.to_csv(output_path / "per_criterion_comparison.csv", index=False)
    
    with open(output_path / "agreement_statistics.json", 'w') as f:
        json.dump(agreements, f, indent=2)
    
    if discrepancies:
        pd.DataFrame(discrepancies).to_csv(
            output_path / "discrepancies.csv",
            index=False
        )
    
    # Create visualizations
    if create_plots:
        print("\nCreating visualizations...")
        create_visualizations(scores_dict, output_path)
    
    # Generate report
    print("\nGenerating comparison report...")
    generate_report(
        scores_dict,
        correlations,
        agreements,
        per_criterion,
        discrepancies,
        output_path
    )
    
    print("\n" + "="*80)
    print("  COMPARISON COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_dir}")
    print("\nKey files:")
    print(f"  - comparison_report.md: Comprehensive analysis")
    print(f"  - correlations.csv: Inter-method correlations")
    print(f"  - per_criterion_comparison.csv: Criterion-level comparison")
    print(f"  - agreement_statistics.json: Detailed agreement metrics")
    if discrepancies:
        print(f"  - discrepancies.csv: Cases with large score differences")


if __name__ == "__main__":
    from jsonargparse import CLI
    CLI([main], as_positional=False)
