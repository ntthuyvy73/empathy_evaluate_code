# MindEval Dim-A — Báo cáo phân tích kết quả

> N = 20 record/dataset/setting | Thang điểm 1–6

---

## 1. Điểm trung bình Overall score

| Dataset | Lang | Origin | S1 (EN↔EN) | S2 (NL↔NL) | S3 (NL→EN) |
|---|---|---|---|---|---|
| cactus | en | simulated | 3.508 | - | 3.508 | 
| Psy-Insight | en | human | 3.188 | - | 3.188 | 
| simpsydial | zh | simulated | 3.260 | 3.215 | 3.285 | 
| PsyDial | zh | human | 3.018 | 2.935 | 3.013 | 
| SoulChat | zh | simulated | 2.785 | 2.848 | 2.815 | 
| KMI | ko | human | 2.673 | 2.948 | 2.927 | 
| AnnoMI | en | human | 3.055 | - | 3.055 | 
| CPsyCoun | zh | human | 2.982 | 3.030 | 3.020 | 
| KokoroChat | ja | human | 3.140 | 3.275 | 3.010 | 
| smile | zh | simulated | 2.720 | 2.585 | 2.650 | 
| ESConv | en | human | 2.290 | - | 2.290 | 

## 2. Điểm trung bình theo metric — S1 (EN↔EN)

| Dataset | Clinical | Ethics | Assessment | Alliance | AI-Comm | Overall |
|---|---|---|---|---|---|---|
| cactus | 3.575 | 4.250 | 3.300 | 3.325 | 3.087 | 3.508 |
| Psy-Insight | 3.225 | 3.925 | 2.975 | 2.962 | 2.850 | 3.188 |
| simpsydial | 3.175 | 3.925 | 3.100 | 3.125 | 2.975 | 3.260 |
| PsyDial | 3.000 | 3.325 | 2.962 | 3.138 | 2.663 | 3.018 |
| SoulChat | 2.725 | 3.112 | 2.513 | 2.862 | 2.712 | 2.785 |
| KMI | 2.700 | 3.625 | 2.400 | 2.513 | 2.125 | 2.673 |
| AnnoMI | 3.175 | 3.450 | 2.850 | 2.913 | 2.888 | 3.055 |
| CPsyCoun | 3.025 | 3.750 | 2.625 | 2.737 | 2.775 | 2.982 |
| KokoroChat | 3.075 | 3.712 | 2.925 | 3.112 | 2.875 | 3.140 |
| smile | 2.700 | 2.950 | 2.562 | 2.700 | 2.688 | 2.720 |
| ESConv | 2.350 | 2.325 | 2.125 | 2.450 | 2.200 | 2.290 |

## 3. Ranking theo Z-score — S1 (EN↔EN)

> Z-score (+) = trên trung bình | Mean-rank (thấp = tốt hơn)

| Dataset | Clinical | Ethics | Assessment | Alliance | AI-Comm | Mean-Rank |
|---|---|---|---|---|---|---|
| cactus | 1.880 | 1.484 | 1.654 | 1.642 | 1.311 | 1.000 |
| Psy-Insight | 0.783 | 0.853 | 0.662 | 0.260 | 0.481 | 3.500 |
| simpsydial | 0.627 | 0.853 | 1.044 | 0.879 | 0.918 | 2.600 |
| PsyDial | 0.078 | -0.314 | 0.624 | 0.927 | -0.175 | 6.000 |
| SoulChat | -0.783 | -0.727 | -0.749 | -0.121 | 0.000 | 8.000 |
| KMI | -0.862 | 0.269 | -1.092 | -1.455 | -2.054 | 9.300 |
| AnnoMI | 0.627 | -0.071 | 0.281 | 0.069 | 0.612 | 5.100 |
| CPsyCoun | 0.157 | 0.512 | -0.406 | -0.598 | 0.218 | 6.200 |
| KokoroChat | 0.313 | 0.440 | 0.510 | 0.832 | 0.568 | 4.600 |
| smile | -0.862 | -1.043 | -0.597 | -0.741 | -0.087 | 8.900 |
| ESConv | -1.959 | -2.257 | -1.932 | -1.694 | -1.791 | 10.800 |

## 4. Ranking theo Z-score — S3 (NL→EN)

| Dataset | Clinical | Ethics | Assessment | Alliance | AI-Comm | Mean-Rank |
|---|---|---|---|---|---|---|
| cactus | 1.844 | 1.380 | 1.779 | 1.911 | 1.399 | 1.000 |
| Psy-Insight | 0.739 | 0.769 | 0.694 | 0.277 | 0.505 | 3.500 |
| simpsydial | 0.976 | 0.769 | 0.903 | 0.897 | 1.305 | 2.300 |
| PsyDial | 0.029 | -0.100 | 0.402 | 0.840 | -0.342 | 5.500 |
| SoulChat | -0.603 | -0.617 | -0.683 | -0.118 | -0.248 | 8.200 |
| KMI | -0.366 | 0.886 | -0.391 | -0.400 | -1.519 | 7.200 |
| AnnoMI | 0.581 | -0.124 | 0.277 | 0.051 | 0.646 | 5.200 |
| CPsyCoun | 0.029 | 0.510 | -0.057 | -0.512 | 0.222 | 6.500 |
| KokoroChat | -0.129 | -0.030 | 0.235 | 0.164 | 0.411 | 5.800 |
| smile | -1.076 | -1.205 | -1.016 | -1.076 | -0.436 | 9.800 |
| ESConv | -2.023 | -2.238 | -2.143 | -2.034 | -1.942 | 11.000 |

## 5. Phân tích ảnh hưởng ngôn ngữ

### 5.1 Spearman correlation trung bình giữa các setting (non-EN)

|    |    S1 |    S2 |    S3 |
|:---|------:|------:|------:|
| S1 | 1     | 0.409 | 0.432 |
| S2 | 0.409 | 1     | 0.538 |
| S3 | 0.432 | 0.538 | 1     |

### 5.2 Chi tiết per dataset

| dataset    | comparison                |   n |   mean_A |   mean_B |   mean_delta (A-B) |   MAD |   Spearman_r |   Spearman_p | sig_diff   |
|:-----------|:--------------------------|----:|---------:|---------:|-------------------:|------:|-------------:|-------------:|:-----------|
| simpsydial | S1 vs S3 (Translation)    |  20 |    3.26  |    3.285 |             -0.025 | 0.16  |        0.133 |        0.576 | False      |
| simpsydial | S2 vs S3 (Judge Language) |  20 |    3.215 |    3.285 |             -0.07  | 0.155 |        0.138 |        0.562 | False      |
| simpsydial | S1 vs S2 (Combined)       |  20 |    3.26  |    3.215 |              0.045 | 0.13  |        0.369 |        0.11  | False      |
| PsyDial    | S1 vs S3 (Translation)    |  20 |    3.018 |    3.012 |              0.005 | 0.22  |        0.611 |        0.004 | False      |
| PsyDial    | S2 vs S3 (Judge Language) |  20 |    2.935 |    3.012 |             -0.078 | 0.158 |        0.809 |        0     | False      |
| PsyDial    | S1 vs S2 (Combined)       |  20 |    3.018 |    2.935 |              0.083 | 0.223 |        0.524 |        0.018 | False      |
| SoulChat   | S1 vs S3 (Translation)    |  20 |    2.785 |    2.815 |             -0.03  | 0.17  |        0.706 |        0.001 | False      |
| SoulChat   | S2 vs S3 (Judge Language) |  20 |    2.848 |    2.815 |              0.032 | 0.118 |        0.754 |        0     | False      |
| SoulChat   | S1 vs S2 (Combined)       |  20 |    2.785 |    2.848 |             -0.063 | 0.218 |        0.57  |        0.009 | False      |
| KMI        | S1 vs S3 (Translation)    |  20 |    2.673 |    2.927 |             -0.255 | 0.285 |        0.562 |        0.01  | True       |
| KMI        | S2 vs S3 (Judge Language) |  20 |    2.948 |    2.927 |              0.02  | 0.19  |        0.302 |        0.196 | False      |
| KMI        | S1 vs S2 (Combined)       |  20 |    2.673 |    2.948 |             -0.275 | 0.29  |        0.578 |        0.008 | True       |
| CPsyCoun   | S1 vs S3 (Translation)    |  20 |    2.982 |    3.02  |             -0.038 | 0.128 |        0.599 |        0.005 | False      |
| CPsyCoun   | S2 vs S3 (Judge Language) |  20 |    3.03  |    3.02  |              0.01  | 0.155 |        0.367 |        0.112 | False      |
| CPsyCoun   | S1 vs S2 (Combined)       |  20 |    2.982 |    3.03  |             -0.048 | 0.173 |        0.19  |        0.421 | False      |
| KokoroChat | S1 vs S3 (Translation)    |  20 |    3.14  |    3.01  |              0.13  | 0.28  |        0.022 |        0.925 | False      |
| KokoroChat | S2 vs S3 (Judge Language) |  20 |    3.275 |    3.01  |              0.265 | 0.27  |        0.597 |        0.005 | True       |
| KokoroChat | S1 vs S2 (Combined)       |  20 |    3.14  |    3.275 |             -0.135 | 0.305 |        0.268 |        0.253 | False      |
| smile      | S1 vs S3 (Translation)    |  20 |    2.72  |    2.65  |              0.07  | 0.385 |        0.389 |        0.09  | False      |
| smile      | S2 vs S3 (Judge Language) |  20 |    2.585 |    2.65  |             -0.065 | 0.21  |        0.799 |        0     | False      |
| smile      | S1 vs S2 (Combined)       |  20 |    2.72  |    2.585 |              0.135 | 0.375 |        0.364 |        0.115 | False      |

## 6. Sức phân biệt (Discriminative Power)

> Std của dataset-mean per metric per setting — cao = phân biệt tốt hơn

| setting   |   Clinical Accuracy & Competence |   Ethical & Professional Conduct |   Assessment & Response |   Therapeutic Relationship & Alliance |   AI-Specific Communication Quality |   Overall score |
|:----------|---------------------------------:|---------------------------------:|------------------------:|--------------------------------------:|------------------------------------:|----------------:|
| S1        |                            0.335 |                            0.54  |                   0.344 |                                 0.275 |                               0.3   |           0.333 |
| S2        |                            0.213 |                            0.43  |                   0.196 |                                 0.206 |                               0.292 |           0.231 |
| S3        |                            0.332 |                            0.558 |                   0.314 |                                 0.233 |                               0.279 |           0.322 |

## 7. Giải thích & Khuyến nghị

**Setting có sức phân biệt cao nhất (Overall):** `S1` (std = 0.333)

**Tương quan Spearman S1 vs S3:** r = 0.432 → **Thấp** (bản dịch ảnh hưởng đáng kể đến ranking). Cần kiểm tra chất lượng dịch.

### Caveat

Ranking này phản ánh **thế mạnh tương đối** trong điều kiện pilot N=20, không phải chất lượng tuyệt đối. Cần xem xét cùng với confound nguồn gốc (human/simulated), độ dài hội thoại, và chất lượng bản dịch (S1).
## 8. KMI — So sánh bản dịch (S1-utt vs S1-llm vs S2-ko)

> S1-utt = `utterance_en` có sẵn | S1-llm = GPT-5.1 dịch từ KO | S2-ko = hội thoại KO gốc + judge KO

| Condition | Clinical | Ethics | Assessment | Alliance | AI-Comm | Overall |
|---|---|---|---|---|---|---|
| S1-utt (utterance_en) | 2.700 | 3.625 | 2.400 | 2.513 | 2.125 | 2.673 |
| S1-llm (GPT-5.1 dịch KO) | 2.962 | 3.987 | 2.812 | 2.925 | 2.500 | 3.038 |
| S2-ko (KO gốc) | 2.625 | 3.950 | 2.837 | 2.913 | 2.413 | 2.948 |

**Delta Overall (S1-llm − S1-utt):** +0.365  
**Delta Overall (S1-llm − S2-ko):**  +0.090  

> **Kết luận**: S1-llm xap xỉ S2-ko (|Δ| < 0.15) — GPT-5.1 translation giữ được sắc thái gần với bản gốc. `utterance_en` bị artifact (S1-utt thấp hơn S1-llm 0.365 điểm).
> Khuyến nghị: dùng S1-llm làm S1 chính thức của KMI.

## 9. So sánh judge: GPT-5.1 vs claude

> Cả hai judge dùng cùng rubric. Delta = claude − GPT-5.1.  
> Green (Δ > 0): claude chấm cao hơn | Red (Δ < 0): GPT chấm cao hơn.

### S1 (EN↔EN)

| Dataset | GPT-5.1 | claude | Delta |
|---|---|---|---|
| cactus | 3.508 | 3.267 | -0.240 |
| Psy-Insight | 3.188 | 2.935 | -0.253 |
| simpsydial | 3.260 | 3.120 | -0.140 |
| PsyDial | 3.018 | 2.690 | -0.328 |
| SoulChat | 2.785 | 2.290 | -0.495 |
| KMI | 2.673 | 2.345 | -0.328 |

**Mean Δ Overall (S1):** -0.297  

### S2 (NL↔NL)

| Dataset | GPT-5.1 | claude | Delta |
|---|---|---|---|
| simpsydial | 3.215 | 2.845 | -0.370 |
| PsyDial | 2.935 | 2.768 | -0.167 |
| SoulChat | 2.848 | 2.135 | -0.713 |
| KMI | 2.948 | 2.435 | -0.513 |

**Mean Δ Overall (S2):** -0.441  

### S3 (NL→EN)

| Dataset | GPT-5.1 | claude | Delta |
|---|---|---|---|
| cactus | 3.508 | 3.267 | -0.240 |
| Psy-Insight | 3.188 | 2.935 | -0.253 |
| simpsydial | 3.285 | 3.005 | -0.280 |
| PsyDial | 3.013 | 2.585 | -0.428 |
| SoulChat | 2.815 | 2.130 | -0.685 |
| KMI | 2.927 | 2.485 | -0.442 |

**Mean Δ Overall (S3):** -0.388  

**Global mean Δ Overall (all settings):** -0.367  

> **Ghi chú**: Global mean Δ = -0.367 — cần kiểm tra xem judge nào systematic higher/lower và ảnh hưởng đến ranking.


---
*Generated by `mindeval/scripts/analyze_results.py`*
