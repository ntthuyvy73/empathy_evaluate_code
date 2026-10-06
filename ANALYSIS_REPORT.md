# BÁO CÁO PHÂN TÍCH KẾT QUẢ ĐÁNH GIÁ MIND_EVAL

> Phân tích ảnh hưởng ngôn ngữ và ranking theo PLAN-standardization-and-ranking.md

## 1. TÌNH TRẠNG DỮ LIỆU HIỆN TẠI

| Dataset | Ngôn ngữ | Settings có sẵn | Ghi chú |
|---------|----------|-----------------|---------|
| ✅ **cactus** | en | S1, S3 | S1=S2=S3 cho tiếng Anh |
| ✅ **KMI** | ko | S1, S2, S3 | Dataset duy nhất có đầy đủ 3 settings |
| ✅ **Psy-Insight** | en | S1, S3 | S1=S2=S3 cho tiếng Anh |
| ❌ **simpsydial** | zh | Chưa có | Cần chạy đánh giá |
| ❌ **PsyDial** | zh | Chưa có | Cần chạy đánh giá |
| ❌ **SoulChat** | zh | Chưa có | Cần chạy đánh giá |

## 2. PHƯƠNG PHÁP PHÂN TÍCH

Theo Section 3.1 trong PLAN:

- **S1 vs S3**: Hiệu ứng BẢN DỊCH (cùng judge tiếng Anh)
  - S1: dịch hội thoại → EN + judge EN
  - S3: hội thoại gốc + judge EN

- **S3 vs S2**: Hiệu ứng NGÔN NGỮ JUDGE (cùng hội thoại gốc)
  - S2: hội thoại gốc + judge bản địa
  - S3: hội thoại gốc + judge EN

- **Datasets EN**: Anchor baseline (S1=S2=S3)

## 3. KẾT QUẢ PHÂN TÍCH CHI TIẾT

### 3.1 Hiệu ứng Bản dịch (S1 vs S3) - Dataset KMI

| Metric | S1 | S3 | Δ (S1-S3) | Nhận xét |
|--------|----|----|-----------|----------|
| Clinical Accuracy & Competence | 2.60 | 2.90 | **-0.30** | S3 tốt hơn |
| Ethical & Professional Conduct | 3.50 | 4.05 | **-0.55** | S3 tốt hơn đáng kể |
| Assessment & Response | 2.20 | 2.70 | **-0.50** | S3 tốt hơn |
| Therapeutic Relationship & Alliance | 2.40 | 2.85 | **-0.45** | S3 tốt hơn |
| AI-Specific Communication Quality | 2.20 | 2.35 | **-0.15** | S3 hơi tốt hơn |

**Kết luận**: Bản dịch (S1) làm giảm chất lượng đánh giá so với hội thoại gốc (S3).

### 3.2 Hiệu ứng Ngôn ngữ Judge (S3 vs S2) - Dataset KMI

| Metric | S2 (Korean) | S3 (English) | Δ (S3-S2) | Nhận xét |
|--------|-------------|--------------|-----------|----------|
| Clinical Accuracy & Competence | 2.60 | 2.90 | **+0.30** | Judge EN tốt hơn |
| Ethical & Professional Conduct | 3.90 | 4.05 | **+0.15** | Judge EN hơi tốt hơn |
| Assessment & Response | 2.95 | 2.70 | **-0.25** | Judge KO tốt hơn |
| Therapeutic Relationship & Alliance | 2.90 | 2.85 | **-0.05** | Gần như tương đương |
| AI-Specific Communication Quality | 2.40 | 2.35 | **-0.05** | Gần như tương đương |

**Kết luận**: Ảnh hưởng của ngôn ngữ judge không nhất quán - EN judge tốt hơn ở một số tiêu chí, KO judge tốt hơn ở tiêu chí khác.

### 3.3 Datasets Tiếng Anh (Anchor Baseline)

#### CACTUS (S1=S2=S3)
| Metric | Score | Std Dev |
|--------|-------|---------|
| Clinical Accuracy & Competence | 3.50 | 0.00 |
| Ethical & Professional Conduct | 4.20 | 0.27 |
| Assessment & Response | 3.20 | 0.27 |
| Therapeutic Relationship & Alliance | 3.30 | 0.27 |
| AI-Specific Communication Quality | 3.00 | 0.00 |

#### PSY-INSIGHT (dữ liệu chưa đầy đủ)
- Cần kiểm tra lại file kết quả S1_judgments.jsonl

## 4. PHÂN TÍCH SỨC PHÂN BIỆT (Discriminative Power)

### Setting S1
| Metric | Range | Variance |
|--------|-------|----------|
| Clinical Accuracy & Competence | 0.90 | 0.202 |
| **Assessment & Response** | **1.00** | **0.250** | ← Sức phân biệt cao nhất
| Therapeutic Relationship & Alliance | 0.90 | 0.202 |
| AI-Specific Communication Quality | 0.80 | 0.160 |
| Ethical & Professional Conduct | 0.70 | 0.123 |

### Setting S3
| Metric | Range | Variance |
|--------|-------|----------|
| AI-Specific Communication Quality | 0.65 | 0.106 |
| Clinical Accuracy & Competence | 0.60 | 0.090 |
| Assessment & Response | 0.60 | 0.090 |
| Therapeutic Relationship & Alliance | 0.55 | 0.076 |
| Ethical & Professional Conduct | 0.05 | 0.001 |

**Nhận xét**: S1 có sức phân biệt cao hơn S3 (range và variance lớn hơn).

## 5. RANKING DATASETS

### Setting S1 (EN judge, EN dialogue)
**Cactus > KMI** trên tất cả 5 tiêu chí

### Setting S3 (EN judge, native dialogue)  
**Cactus > KMI** trên tất cả 5 tiêu chí

**Nhận xét**: Thứ hạng tương đối giữa datasets không thay đổi giữa S1 và S3.

## 6. KẾT LUẬN VÀ KHUYẾN NGHỊ

### 6.1 Ảnh hưởng của Ngôn ngữ

1. **Bản dịch có tác động tiêu cực**: S1 (dịch) kém hơn S3 (gốc) trên tất cả tiêu chí
2. **Ngôn ngữ judge có ảnh hưởng hỗn hợp**: Không có xu hướng rõ ràng S2 vs S3
3. **Ranking tương đối ổn định**: Thứ hạng giữa datasets không đổi giữa S1 và S3

### 6.2 Lựa chọn Trục Ranking

Theo Section 3.3 trong PLAN, chỉ S1 và S3 hợp lệ cho ranking chéo datasets:

**Khuyến nghị: Chọn S3** vì:
- ✅ Tránh artifact bản dịch (S3 > S1 trên KMI)
- ✅ Tiết kiệm chi phí (không cần dịch)
- ✅ Giữ nguyên ngữ nghĩa gốc
- ✅ Thứ hạng tương đối ổn định với S1

### 6.3 Bước tiếp theo

1. **Ưu tiên cao**:
   - Chạy đánh giá cho 3 datasets tiếng Trung (simpsydial, PsyDial, SoulChat)
   - Kiểm tra và sửa lỗi dữ liệu Psy-Insight

2. **Phân tích bổ sung**:
   - So sánh với kết quả WAI (Dim-B)
   - Tính reliability (multiple runs)
   - Phân tích theo length buckets

3. **Báo cáo cuối**:
   - Strength profile từng dataset
   - Chuẩn hóa z-score cross-dataset
   - Caveat về provenance differences

## 7. HẠN CHẾ VÀ LƯU Ý

- **Dữ liệu hạn chế**: Chỉ có 2-3 datasets với 3 samples mỗi setting
- **Provenance khác biệt**: human vs simulated vs single-turn không được chuẩn hóa
- **Sample size nhỏ**: Cần tăng N cho độ tin cậy thống kê
- **Missing datasets**: 50% datasets chưa có kết quả

---

*Báo cáo được tạo tự động từ analyze_evaluation_results.py*