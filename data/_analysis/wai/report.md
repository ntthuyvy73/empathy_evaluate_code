# WAI-O-S Analysis Report

**Setting**: S3 (original-language dialogue + English judge)  
**Judge**: gpt  
**N per dataset**: 20  
**Scale**: 1–5 (WAI-O-S)  
**Dimensions**: Goal (Q1-Q4) · Approach (Q5-Q8) · Affective Bond (Q9-Q12)  

---

## 1. Raw Mean Scores

| Dataset | Goal | Approach | Affective Bond | **Total** |
|---|---|---|---|---|
| cactus | 4.73 ±0.28 | 4.30 ±0.54 | 4.04 ±0.26 | **4.36 ±0.32** |
| PsyInsight | 3.46 ±0.53 | 3.30 ±0.40 | 3.27 ±0.32 | **3.35 ±0.38** |
| simpsydial | 4.30 ±0.25 | 4.32 ±0.09 | 4.05 ±0.12 | **4.22 ±0.11** |
| PsyDial | 4.20 ±0.25 | 3.92 ±0.41 | 4.24 ±0.35 | **4.12 ±0.29** |
| SoulChat | 4.00 ±0.17 | 4.01 ±0.14 | 4.08 ±0.20 | **4.03 ±0.11** |
| KMI | 4.05 ±0.33 | 3.58 ±0.40 | 3.70 ±0.21 | **3.78 ±0.26** |

## 2. Z-score Ranking (S3)

*Z-score: (+) = above cross-dataset mean. Mean-rank: lower = better.*

| Dataset | Goal | Approach | Affective Bond | **Mean-Rank** |
|---|---|---|---|---|
| simpsydial | +0.45 | +1.13 | +0.48 | **2.0** |
| cactus | +1.60 | +1.08 | +0.44 | **2.3** |
| PsyDial | +0.21 | +0.04 | +1.06 | **2.7** |
| SoulChat | -0.32 | +0.28 | +0.57 | **3.3** |
| KMI | -0.21 | -0.89 | -0.60 | **4.7** |
| PsyInsight | -1.74 | -1.64 | -1.94 | **6.0** |

## 3. Per-Question Mean Scores

| Dataset | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Q11 | Q12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cactus | 4.78 | 4.83 | 4.87 | 4.45 | 4.72 | 3.80 | 4.65 | 4.03 | 4.20 | 3.80 | 4.05 | 4.10 |
| PsyInsight | 3.48 | 3.37 | 3.47 | 3.53 | 3.20 | 3.20 | 3.62 | 3.20 | 3.20 | 3.15 | 3.18 | 3.57 |
| simpsydial | 4.08 | 4.33 | 4.58 | 4.18 | 4.93 | 4.00 | 4.28 | 4.05 | 4.05 | 4.00 | 4.00 | 4.15 |
| PsyDial | 4.20 | 4.13 | 4.50 | 3.98 | 3.87 | 3.68 | 4.15 | 3.98 | 4.27 | 4.05 | 4.18 | 4.45 |
| SoulChat | 3.88 | 3.98 | 4.15 | 4.00 | 4.10 | 3.92 | 4.00 | 4.02 | 4.13 | 4.00 | 4.12 | 4.07 |
| KMI | 3.95 | 3.92 | 4.30 | 4.02 | 3.48 | 3.35 | 4.05 | 3.43 | 3.83 | 3.22 | 3.77 | 4.00 |

## 4. Thematic Strength Profile

| Dataset | Điểm nổi bật | Điểm yếu nhất |
|---|---|---|
| **cactus** | Goal (4.73) | Affective Bond (4.04) |
| **PsyInsight** | Goal (3.46) | Affective Bond (3.27) |
| **simpsydial** | Approach (4.32) | Affective Bond (4.05) |
| **PsyDial** | Affective Bond (4.24) | Approach (3.92) |
| **SoulChat** | Affective Bond (4.08) | Goal (4.00) |
| **KMI** | Goal (4.05) | Approach (3.58) |

## 5. Ghi chú phương pháp luận

**Rubric Q1 & Q3 đã được sửa**: Trong rubric gốc của Li et al. (2024) Appendix A.3,
level 2 và level 4 của Q1 và Q3 bị đảo ngữ nghĩa so với chiều thang điểm (level 2 mô tả
hành vi liên minh TỐT, level 4 mô tả hành vi XẤU). Điều này gây ra artifact: hội thoại
có liên minh tốt nhưng không 'gọi tên' mục tiêu tường minh bị phạt xuống 2 điểm thay vì
được thưởng 4 điểm. Fix đã áp dụng: hoán đổi nội dung level 2 ↔ 4 trong Q1 và Q3.

**n_runs = 1**: Kết quả này dùng n_runs=1 (1 LLM call/question thay vì 3) để giảm chi phí
token. Với temperature=0.3 thấp và model GPT-5.1 mạnh, variance giữa các run nhỏ; kết quả
pilot đủ để phân tích định hướng. Nên chạy lại với n_runs=3 cho kết quả chính thức.

## 6. Charts

```
data/_analysis/wai/charts/
  01_dimension_heatmap.png    — heatmap 3 dims × 6 datasets
  02_per_question_heatmap.png — heatmap Q1-Q12 × 6 datasets
  03_strength_profile.png     — radar z-score strength profile
  04_ranking_bar.png          — grouped bar z-score per dimension
  05_boxplot_dims.png         — boxplot Total WAI per dataset
  06_total_bar.png            — horizontal bar Total mean ranked
```
