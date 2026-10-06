#!/usr/bin/env python3
"""
Phân tích kết quả đánh giá S1, S2, S3 trên mind_eval
Theo quy trình trong PLAN-standardization-and-ranking.md
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr, kendalltau
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Thiết lập matplotlib để hiển thị tiếng Việt
plt.rcParams['font.family'] = ['DejaVu Sans', 'SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# Cấu trúc dữ liệu
DATASETS = {
    'cactus': {'language': 'en', 'available_settings': ['S1', 'S3']},  # S1=S2=S3 cho EN
    'kmi': {'language': 'ko', 'available_settings': ['S1', 'S2', 'S3']},
    'psy_insight': {'language': 'en', 'available_settings': ['S1', 'S3']},  # S1=S2=S3 cho EN
    'simpsydial': {'language': 'zh', 'available_settings': []},  # Chưa có kết quả
    'psydial': {'language': 'zh', 'available_settings': []},  # Chưa có kết quả
    'soulchat': {'language': 'zh', 'available_settings': []}   # Chưa có kết quả
}

METRICS = [
    'Clinical Accuracy & Competence',
    'Ethical & Professional Conduct', 
    'Assessment & Response',
    'Therapeutic Relationship & Alliance',
    'AI-Specific Communication Quality'
]

def load_judgment_file(file_path):
    """Đọc file JSONL kết quả đánh giá"""
    data = []
    if not file_path.exists():
        return data
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def extract_scores(judgment_data):
    """Trích xuất điểm số từ parsed_judgment"""
    scores = []
    for item in judgment_data:
        parsed = item.get('parsed_judgment', {})
        if parsed:
            # Bỏ qua Overall score và Average score
            score_dict = {k: v for k, v in parsed.items() 
                         if k in METRICS and isinstance(v, (int, float))}
            if score_dict:
                scores.append(score_dict)
    return scores

def calculate_statistics(scores):
    """Tính toán thống kê mô tả"""
    if not scores:
        return {}
    
    df = pd.DataFrame(scores)
    stats_dict = {}
    
    for metric in METRICS:
        if metric in df.columns:
            values = df[metric].dropna()
            if len(values) > 0:
                stats_dict[metric] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'median': values.median(),
                    'min': values.min(),
                    'max': values.max(),
                    'count': len(values)
                }
    
    return stats_dict

def analyze_language_effects():
    """Phân tích ảnh hưởng của ngôn ngữ theo section 3 trong PLAN"""
    results = {}
    
    # Thu thập dữ liệu
    all_data = {}
    
    for dataset_name, info in DATASETS.items():
        if not info['available_settings']:
            continue
            
        dataset_folder = Path(f"data/{dataset_name}/results/mind_eval")
        all_data[dataset_name] = {}
        
        for setting in info['available_settings']:
            file_path = dataset_folder / f"{setting}_judgments.jsonl"
            judgment_data = load_judgment_file(file_path)
            scores = extract_scores(judgment_data)
            stats = calculate_statistics(scores)
            
            all_data[dataset_name][setting] = {
                'scores': scores,
                'statistics': stats,
                'language': info['language']
            }
    
    # Tạo DataFrame tổng hợp cho so sánh
    comparison_data = []
    
    for dataset_name, settings_data in all_data.items():
        for setting, data in settings_data.items():
            for metric in METRICS:
                if metric in data['statistics']:
                    stats = data['statistics'][metric]
                    comparison_data.append({
                        'Dataset': dataset_name,
                        'Setting': setting,
                        'Language': data['language'],
                        'Metric': metric,
                        'Mean': stats['mean'],
                        'Std': stats['std'],
                        'Count': stats['count']
                    })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    # Phân tích theo section 3.1: Phân rã hiệu ứng
    analysis_results = {}
    
    # 1. So sánh S1 vs S3 cho datasets có cả hai (hiệu ứng bản dịch)
    print("=== PHÂN TÍCH ẢNH HƯỞNG NGÔN NGỮ ===")
    print("\n1. Hiệu ứng BẢN DỊCH (S1 vs S3)")
    print("S1: dịch hội thoại sang EN + judge EN")
    print("S3: giữ hội thoại gốc + judge EN")
    
    for dataset_name in ['kmi']:  # Chỉ KMI có cả S1, S2, S3
        if dataset_name not in all_data or len(all_data[dataset_name]) < 2:
            continue
            
        print(f"\nDataset: {dataset_name.upper()}")
        
        # So sánh S1 vs S3
        if 'S1' in all_data[dataset_name] and 'S3' in all_data[dataset_name]:
            s1_stats = all_data[dataset_name]['S1']['statistics']
            s3_stats = all_data[dataset_name]['S3']['statistics']
            
            print("  S1 vs S3 (hiệu ứng bản dịch):")
            for metric in METRICS:
                if metric in s1_stats and metric in s3_stats:
                    s1_mean = s1_stats[metric]['mean']
                    s3_mean = s3_stats[metric]['mean']
                    diff = s1_mean - s3_mean
                    print(f"    {metric}: S1={s1_mean:.2f}, S3={s3_mean:.2f}, Δ={diff:.2f}")
        
        # So sánh S3 vs S2 (nếu có S2)
        if 'S2' in all_data[dataset_name] and 'S3' in all_data[dataset_name]:
            s2_stats = all_data[dataset_name]['S2']['statistics']
            s3_stats = all_data[dataset_name]['S3']['statistics']
            
            print("  S3 vs S2 (hiệu ứng ngôn ngữ judge):")
            print("  S2: hội thoại gốc + judge bản địa")
            print("  S3: hội thoại gốc + judge EN")
            for metric in METRICS:
                if metric in s2_stats and metric in s3_stats:
                    s2_mean = s2_stats[metric]['mean']
                    s3_mean = s3_stats[metric]['mean']
                    diff = s3_mean - s2_mean
                    print(f"    {metric}: S2={s2_mean:.2f}, S3={s3_mean:.2f}, Δ={diff:.2f}")
    
    # 2. Datasets tiếng Anh (anchor)
    print("\n2. Datasets tiếng Anh (ANCHOR)")
    print("S1 = S2 = S3 (cùng hội thoại EN + judge EN)")
    
    for dataset_name in ['cactus', 'psy_insight']:
        if dataset_name not in all_data:
            continue
            
        print(f"\nDataset: {dataset_name.upper()}")
        if 'S1' in all_data[dataset_name]:
            s1_stats = all_data[dataset_name]['S1']['statistics']
            for metric in METRICS:
                if metric in s1_stats:
                    mean_score = s1_stats[metric]['mean']
                    std_score = s1_stats[metric]['std']
                    print(f"  {metric}: {mean_score:.2f} ± {std_score:.2f}")
    
    return df_comparison, all_data

def calculate_discriminative_power(df_comparison):
    """Tính sức phân biệt (discriminative power) - section 3.2"""
    print("\n=== SỨC PHÂN BIỆT (Discriminative Power) ===")
    
    # Tính range và variance của điểm giữa các dataset cho mỗi setting
    for setting in df_comparison['Setting'].unique():
        setting_data = df_comparison[df_comparison['Setting'] == setting]
        
        print(f"\nSetting {setting}:")
        for metric in METRICS:
            metric_data = setting_data[setting_data['Metric'] == metric]
            if len(metric_data) > 1:
                means = metric_data['Mean'].values
                score_range = np.max(means) - np.min(means)
                variance = np.var(means)
                print(f"  {metric}: Range={score_range:.2f}, Var={variance:.3f}")

def create_visualization(df_comparison):
    """Tạo biểu đồ so sánh"""
    # Biểu đồ heatmap điểm trung bình
    pivot_data = df_comparison.pivot_table(
        values='Mean', 
        index=['Dataset', 'Setting'], 
        columns='Metric'
    )
    
    plt.figure(figsize=(14, 8))
    sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlBu_r', 
                center=3.5, vmin=1, vmax=6)
    plt.title('Điểm trung bình MindEval theo Dataset và Setting')
    plt.xlabel('Metrics')
    plt.ylabel('Dataset - Setting')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('mind_eval_heatmap.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Box plot so sánh setting
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for i, metric in enumerate(METRICS):
        metric_data = df_comparison[df_comparison['Metric'] == metric]
        if len(metric_data) > 0:
            sns.boxplot(data=metric_data, x='Setting', y='Mean', ax=axes[i])
            axes[i].set_title(metric)
            axes[i].set_ylim(1, 6)
    
    # Ẩn subplot thừa nếu có
    if len(METRICS) < len(axes):
        axes[-1].set_visible(False)
    
    plt.suptitle('Phân bố điểm theo Setting và Metric')
    plt.tight_layout()
    plt.savefig('mind_eval_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()

def ranking_analysis(df_comparison):
    """Phân tích ranking theo section 8 trong PLAN"""
    print("\n=== PHÂN TÍCH RANKING ===")
    
    # Tính z-score cho mỗi metric across datasets trong cùng setting
    ranking_results = {}
    
    for setting in df_comparison['Setting'].unique():
        setting_data = df_comparison[df_comparison['Setting'] == setting]
        ranking_results[setting] = {}
        
        print(f"\nSetting {setting}:")
        
        for metric in METRICS:
            metric_data = setting_data[setting_data['Metric'] == metric]
            if len(metric_data) > 1:
                means = metric_data['Mean'].values
                datasets = metric_data['Dataset'].values
                
                # Tính z-score
                z_scores = stats.zscore(means)
                
                # Tạo ranking
                ranked = sorted(zip(datasets, means, z_scores), 
                              key=lambda x: x[1], reverse=True)
                
                print(f"  {metric}:")
                for rank, (dataset, mean, z_score) in enumerate(ranked, 1):
                    print(f"    {rank}. {dataset}: {mean:.2f} (z={z_score:.2f})")
                
                ranking_results[setting][metric] = ranked
    
    return ranking_results

def generate_summary_report():
    """Tạo báo cáo tổng kết theo PLAN"""
    print("\n" + "="*60)
    print("BÁO CÁO TỔNG KẾT PHÂN TÍCH MIND_EVAL")
    print("="*60)
    
    print("\n1. TÌNH TRẠNG DỮ LIỆU:")
    for dataset_name, info in DATASETS.items():
        status = "✓" if info['available_settings'] else "✗"
        settings = ", ".join(info['available_settings']) or "Chưa có"
        print(f"   {status} {dataset_name} ({info['language']}): {settings}")
    
    print("\n2. PHƯƠNG PHÁP PHÂN TÍCH:")
    print("   - S1 vs S3: Hiệu ứng bản dịch (cùng judge EN)")
    print("   - S3 vs S2: Hiệu ứng ngôn ngữ judge (cùng hội thoại gốc)")
    print("   - Datasets EN: Anchor baseline (S1=S2=S3)")
    
    print("\n3. KẾT QUẢ CHÍNH:")
    
    # Phân tích dữ liệu có sẵn
    df_comparison, all_data = analyze_language_effects()
    
    if len(df_comparison) > 0:
        # Sức phân biệt
        calculate_discriminative_power(df_comparison)
        
        # Ranking
        ranking_results = ranking_analysis(df_comparison)
        
        # Tạo biểu đồ
        create_visualization(df_comparison)
        
        print("\n4. KẾT LUẬN VÀ KHUYẾN NGHỊ:")
        print("   - Dựa trên dữ liệu hiện có (KMI, cactus, psy_insight)")
        print("   - Cần bổ sung kết quả cho datasets tiếng Trung (simpsydial, psydial, soulchat)")
        print("   - Thực hiện phân tích đầy đủ khi có đủ 6 datasets")
        
    else:
        print("   Chưa có đủ dữ liệu để phân tích")
    
    print("\n5. BƯỚC TIẾP THEO:")
    print("   - Chạy đánh giá cho các datasets ZH còn lại")
    print("   - Phân tích reliability (n_runs cho WAI)")
    print("   - So sánh với kết quả WAI (Dim-B)")
    print("   - Chọn trục ranking cuối cùng (S1 hoặc S3)")

if __name__ == "__main__":
    generate_summary_report()