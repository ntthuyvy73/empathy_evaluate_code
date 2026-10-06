# Mind-Eval: Tổng Quan Quy Trình Đánh Giá

## Mục Đích

Mind-Eval đánh giá chất lượng các hội thoại tư vấn tâm lý bằng cách dùng một LLM làm "judge". Áp dụng cho các dataset:

| Dataset | Ngôn ngữ | Số lượng | Loại |
|---------|----------|----------|------|
| SimPsyDial | Tiếng Trung | 10 mẫu (raw) | Counseling dialogues |
| KMI | Tiếng Hàn + Anh (bilingual) | 1000 | Mental health interviews |
| SoulChat | Tiếng Trung | 258K | Empathy conversations |

---

## Pipeline Tổng Quan

```
Dataset gốc
    ↓  convert_*.py
interactions.jsonl   (Mind-Eval format)
    ↓  generate_judgments.py
judgments.jsonl      (5 điểm số + thinking trace)
    ↓  pandas / significance_testing.py
Kết quả phân tích
```

---

## Hai Loại Đánh Giá

### 1. Mind-Eval (5 Metrics)

LLM judge đánh giá mỗi hội thoại theo **5 tiêu chí, thang điểm 1–6**:

| # | Tiêu chí | Đánh giá gì |
|---|----------|-------------|
| 1 | **Clinical Accuracy & Competence** | Can thiệp phù hợp, psychoeducation chính xác, lý luận lâm sàng |
| 2 | **Ethical & Professional Conduct** | Ranh giới vai trò AI, không vượt phạm vi, ngôn ngữ không kỳ thị |
| 3 | **Assessment & Response** | Hiểu đúng input, empathic attunement, tích hợp nội dung trước |
| 4 | **Therapeutic Relationship & Alliance** | Cộng tác, tôn trọng quyền tự chủ, sửa chữa đứt gãy mối quan hệ |
| 5 | **AI-Specific Communication Quality** | Giọng tự nhiên, không lặp, không xin lỗi quá mức, tracking ngữ cảnh |

**Thang điểm:**

| Điểm | Ý nghĩa |
|------|---------|
| 1–2 | Vấn đề nghiêm trọng |
| 3–4 | Chấp nhận được đến tốt |
| 5–6 | Xuất sắc (hiếm) |

**Output mỗi dialogue:**
```json
{
  "parsed_judgment": {
    "Clinical Accuracy & Competence": 3.5,
    "Ethical & Professional Conduct": 4.5,
    "Assessment & Response": 3.0,
    "Therapeutic Relationship & Alliance": 3.5,
    "AI-Specific Communication Quality": 3.5,
    "Overall score": 3.6
  },
  "unparsed_judgment": "RATINGS:\nClinical Accuracy...",
  "thinking_trace": "REASONING:\nThis conversation..."
}
```

### 2. WAI (Working Alliance Inventory)

Đánh giá **liên minh trị liệu** dựa theo Li et al. (EMNLP 2024), **12 câu hỏi, thang điểm 1–5**:

| Chiều | Câu hỏi | Đánh giá |
|-------|---------|----------|
| **Goal** | Q1–Q4 | Đồng thuận về mục tiêu trị liệu |
| **Approach** | Q5–Q8 | Đồng thuận về phương pháp |
| **Affective Bond** | Q9–Q12 | Kết nối cảm xúc counselor–client |

**Lưu ý**: 36 LLM calls per dialogue (12 câu × 3 lần) → chậm hơn và tốn token hơn nhiều so với Mind-Eval.

---

## Ba Options Đánh Giá (Cho Dataset Không Phải Tiếng Anh)

| Option | Dialogue | Judge Prompt | Dùng khi |
|--------|----------|--------------|----------|
| **A** | Dịch sang English | English | Cross-dataset comparison, publication |
| **B** | Giữ nguyên | Dịch sang ngôn ngữ gốc | Đánh giá bản ngữ, tránh bias dịch |
| **C** | Giữ nguyên | English | Cross-lingual test, output tiếng Anh |

**So sánh chi phí (ước tính/dialogue):**

| | Option A | Option B | Option C |
|--|----------|----------|----------|
| Dịch dialogue | ~1000 tokens | 0 | 0 |
| Profile extraction | ~1200 tokens | 0 | 0 |
| Judgment | ~2300 tokens | ~2300 tokens | ~2300 tokens |
| **Tổng** | **~4500** | **~2300** | **~2300** |

---

## Format Dữ Liệu

### Input (interactions.jsonl)

```json
{
  "member_profile": {
    "name": "Anonymous",
    "sex": "Unknown",
    "age": 30,
    "race": "Asian",
    "region": "urban",
    "depressive_symptoms": "Unknown",
    "anxious_symptoms": "Unknown"
  },
  "interaction": [
    {"role": "assistant", "content": "Therapist message"},
    {"role": "user", "content": "Client message"}
  ],
  "metadata": {"source": "SimPsyDial", "language": "zh"}
}
```

Role convention: `assistant` = therapist/counselor, `user` = client.

### Caching

Cả conversion và judgment đều hỗ trợ `skip_existing=True` (mặc định). Có thể chạy lại hoặc tăng dần `--max_dialogues` mà không tốn token cho dialogues đã xử lý.

---

## Tài Liệu Liên Quan

| File | Nội dung |
|------|----------|
| `EVALUATION-GUIDE.md` | Chi tiết từng bước của Mind-Eval và WAI |
| `RUN-COMMANDS.md` | Lệnh cụ thể cho từng dataset |
| `CONFIGURATION-SETUP.md` | Thiết lập API keys và config |
| `CHANGES-SUMMARY.md` | Changelog các thay đổi |
| `data/KMI/README.md` | Format và đặc điểm dataset KMI |
| `data/SoulChat/README.md` | Format và đặc điểm dataset SoulChat |
