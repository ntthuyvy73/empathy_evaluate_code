#!/usr/bin/env python3
"""
Phân tích chi tiết kết quả đánh giá - tạo bảng so sánh và insights
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

def load_and_process_data():
    """Tải và xử lý dữ liệu từ tất cả datasets có sẵn"""
    results = {}
    
    datasets_info = {
        'cactus': {'lang': 'en', 'settings': ['S1', 'S3']},
        'kmi': {'lang': 'ko', 'settings': ['S1', 'S2', 'S3']}, 
        'psy_insight': {'lang': 'en', 'settings': ['S1', 'S3']}
    }
    
    metrics = [
        'Clinical Accuracy & Competence',
        'Ethical & Professional Conduct', 
        'Assessment & Response',
        'Therapeutic Relationship & Alliance',
        'AI-Specific Communication Quality'
    ]
    
    for dataset, info in datasets_info.items():
        results[dataset] = {}
        dataset_path = Path(f"data/{dataset}/results/mind_eval")
        
        for setting in info['settings']:
            file_path = dataset_path / f"{setting}_judgments.jsonl"
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = []
                    for line in f:
                        if line.strip():
                            item = json.loads(line)
                            parsed = item.get('parsed_judgment', {})
                            if parsed:
                                # Extract only the 5 main metrics
                                scores = {k: v for k, v in parsed.items() 
                                         if k in metrics and isinstance(v, (int, float))}
                                if scores:
                                    data.append(scores)
                    
                    if data:
                        df = pd.DataFrame(data)
                        results[dataset][setting] = {
                            'scores': data,
                            'mean': df.mean().to_dict(),
                            'std': df.std().to_dict(),
                            'count': len(data),
                            'language': info['lang']
                        }
    
    return results, metrics

def create_summary_table(results, metrics):
    """Tạo bảng tổng kết điểm trung bình"""
    rows = []
    
    for dataset, settings_data in results.items():
        for setting, data in settings_data.items():
            row = {
                'Dataset': dataset.upper(),
                'Setting': setting,
                'Language': data['language'].upper(),
                'N': data['count']
            }
            # Add mean scores for each metric
            for metric in metrics:
                if metric in data['mean']:
                    row[metric.replace(' & ', ' &\n')] = f"{data['mean'][metric]:.2f}"
                else:
                    row[metric.replace(' & ', ' &\n')] = "-"
            
            rows.append(row)
    
    df = pd.DataFrame(rows)
    return df

def analyze_language_effects_detailed(results):
    """Phân tích chi tiết ảnh hưởng ngôn ngữ"""
    print("=== PHÂN TÍCH CHI TIẾT ẢNH HƯỞNG NGÔN NGỮ ===\n")
    
    # KMI analysis (only dataset with all 3 settings)
    if 'kmi' in results and len(results['kmi']) >= 3:
        kmi_data = results['kmi']
        
        print("📊 DATASET KMI (Korean) - Phân tích đầy đủ 3 settings:")
        print("=" * 60)
        
        # Create comparison table for KMI
        kmi_comparison = []
        metrics = [
            'Clinical Accuracy & Competence',
            'Ethical & Professional Conduct', 
            'Assessment & Response',
            'Therapeutic Relationship & Alliance',
            'AI-Specific Communication Quality'
        ]
        
        for metric in metrics:
            row = {'Metric': metric}
            for setting in ['S1', 'S2', 'S3']:
                if setting in kmi_data:
                    row[setting] = f"{kmi_data[setting]['mean'][metric]:.2f}"
                else:
                    row[setting] = "-"
            
            # Calculate differences
            if 'S1' in kmi_data and 'S3' in kmi_data:
                s1_val = kmi_data['S1']['mean'][metric]
                s3_val = kmi_data['S3']['mean'][metric]
                diff_s1_s3 = s1_val - s3_val
                row['S1-S3'] = f"{diff_s1_s3:+.2f}"
            else:
                row['S1-S3'] = "-"
                
            if 'S2' in kmi_data and 'S3' in kmi_data:
                s2_val = kmi_data['S2']['mean'][metric]
                s3_val = kmi_data['S3']['mean'][metric]
                diff_s2_s3 = s2_val - s3_val
                row['S2-S3'] = f"{diff_s2_s3:+.2f}"
            else:
                row['S2-S3'] = "-"
            
            kmi_comparison.append(row)
        
        kmi_df = pd.DataFrame(kmi_comparison)
        print(kmi_df.to_string(index=False))
        
        print("\n🔍 Giải thích các chênh lệch:")
        print("• S1-S3: Hiệu ứng bản dịch (âm = S3 tốt hơn, dương = S1 tốt hơn)")
        print("• S2-S3: Hiệu ứng ngôn ngữ judge (âm = S3 tốt hơn, dương = S2 tốt hơn)")
        
        # Summary insights
        s1_vs_s3_wins = sum(1 for metric in metrics 
                           if kmi_data['S3']['mean'][metric] > kmi_data['S1']['mean'][metric])
        s2_vs_s3_wins = sum(1 for metric in metrics 
                           if kmi_data['S2']['mean'][metric] > kmi_data['S3']['mean'][metric])
        
        print(f"\n📈 Tổng kết KMI:")
        print(f"• S3 thắng S1 trên {s1_vs_s3_wins}/5 tiêu chí → Hội thoại gốc > Bản dịch")
        print(f"• S2 thắng S3 trên {s2_vs_s3_wins}/5 tiêu chí → Judge bản địa ≈ Judge EN")
        
    # English datasets analysis
    print(f"\n📊 DATASETS TIẾNG ANH (Anchor):")
    print("=" * 40)
    
    for dataset in ['cactus', 'psy_insight']:
        if dataset in results and 'S1' in results[dataset]:
            print(f"\n{dataset.upper()}:")
            data = results[dataset]['S1']
            for metric in metrics:
                if metric in data['mean']:
                    mean_val = data['mean'][metric]
                    std_val = data['std'][metric] if metric in data['std'] else 0
                    print(f"  {metric}: {mean_val:.2f} ± {std_val:.2f}")

def recommend_ranking_axis(results):
    """Khuyến nghị trục ranking dựa trên phân tích"""
    print(f"\n🎯 KHUYẾN NGHỊ TRỤC RANKING:")
    print("=" * 40)
    
    print("Theo Section 3.3 trong PLAN, chỉ S1 và S3 hợp lệ cho ranking chéo datasets.")
    print("(S2 sử dụng judge khác ngôn ngữ → không cùng thang đo)")
    
    # Analysis based on KMI data
    if 'kmi' in results and 'S1' in results['kmi'] and 'S3' in results['kmi']:
        s1_data = results['kmi']['S1']['mean']
        s3_data = results['kmi']['S3']['mean']
        
        s3_better_count = 0
        total_metrics = 0
        avg_diff = 0
        
        for metric in s1_data.keys():
            if metric in s3_data:
                diff = s3_data[metric] - s1_data[metric]
                avg_diff += diff
                if diff > 0:
                    s3_better_count += 1
                total_metrics += 1
        
        avg_diff /= total_metrics if total_metrics > 0 else 1
        
        print(f"\n📊 Phân tích S1 vs S3 (dựa trên KMI):")
        print(f"• S3 tốt hơn S1 trên {s3_better_count}/{total_metrics} tiêu chí")
        print(f"• Chênh lệch trung bình: {avg_diff:+.2f} điểm (S3 - S1)")
        
        if s3_better_count > total_metrics // 2:
            print(f"\n✅ KHUYẾN NGHỊ: Chọn S3 làm trục ranking")
            print("📍 Lý do:")
            print("  • Tránh artifact do bản dịch (S3 > S1 trên KMI)")
            print("  • Tiết kiệm chi phí (không cần dịch)")  
            print("  • Giữ nguyên ngữ nghĩa và sắc thái văn hóa")
            print("  • Phù hợp với thực tế triển khai (đa ngôn ngữ)")
        else:
            print(f"\n⚠️ Kết quả không rõ ràng - cần thêm dữ liệu")
    else:
        print("\n❌ Không đủ dữ liệu để đưa ra khuyến nghị chính xác")
        print("Cần kết quả từ datasets tiếng Trung để phân tích đầy đủ")

def generate_action_items():
    """Tạo danh sách hành động cần thực hiện"""
    print(f"\n📋 DANH SÁCH HÀNH ĐỘNG CẦN THỰC HIỆN:")
    print("=" * 50)
    
    print("\n🔴 Ưu tiên CAO (cần làm ngay):")
    print("  1. Chạy đánh giá cho 3 datasets tiếng Trung:")
    print("     • simpsydial: S1, S2, S3")
    print("     • PsyDial: S1, S2, S3") 
    print("     • SoulChat: S1, S2, S3")
    
    print("  2. Kiểm tra và sửa dữ liệu Psy-Insight:")
    print("     • Verify S1_judgments.jsonl integrity")
    print("     • Ensure consistent scoring format")
    
    print("\n🟡 Ưu tiên TRUNG (sau khi có đủ data):")
    print("  3. Chạy đánh giá WAI (Dim-B) với multiple runs")
    print("  4. Tính toán reliability metrics")
    print("  5. Phân tích theo length buckets")
    
    print("\n🟢 Ưu tiên THẤP (báo cáo cuối):")
    print("  6. Tạo strength profiles chi tiết từng dataset")
    print("  7. Chuẩn hóa z-score cross-dataset")
    print("  8. Viết caveat về provenance differences")
    
    print("\n💡 Đề xuất cải tiến:")
    print("  • Tăng sample size lên N=10+ mỗi setting")
    print("  • Thêm human annotation để validate")
    print("  • So sánh với baseline models khác")

def main():
    """Chạy phân tích chi tiết"""
    print("🔍 PHÂN TÍCH CHI TIẾT KẾT QUẢ ĐÁNH GIÁ MIND_EVAL")
    print("=" * 60)
    
    # Load data
    results, metrics = load_and_process_data()
    
    # Create summary table
    summary_df = create_summary_table(results, metrics)
    print("\n📊 BẢNG TỔNG KẾT ĐIỂM TRUNG BÌNH:")
    print("=" * 80)
    print(summary_df.to_string(index=False))
    
    # Detailed analysis
    analyze_language_effects_detailed(results)
    
    # Recommendations
    recommend_ranking_axis(results)
    
    # Action items
    generate_action_items()
    
    # Save results
    summary_df.to_csv('mind_eval_summary.csv', index=False)
    print(f"\n💾 Đã lưu bảng tổng kết: mind_eval_summary.csv")

if __name__ == "__main__":
    main()