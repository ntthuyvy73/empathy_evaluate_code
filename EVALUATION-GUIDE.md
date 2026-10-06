# Hướng Dẫn Chi Tiết Từng Loại Đánh Giá

---

## Phần 1: Mind-Eval (5-Metric Evaluation)

### 1.1. Bước 1 — Convert Dataset sang Mind-Eval Format

Mỗi dataset có conversion script riêng:

| Dataset | Script | Input |
|---------|--------|-------|
| SimPsyDial | `mindeval/scripts/convert_simpsydial.py` | `data/simpsydial/raw/*.json` |
| KMI | `mindeval/scripts/convert_kmi.py` | `data/KMI/raw/kmi.json` |
| SoulChat | `mindeval/scripts/convert_soulchat.py` | `data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json` |

**Option A** (translate → English):
```bash
python mindeval/scripts/convert_simpsydial.py \
    --input_dir data/simpsydial/raw \
    --output_path data/simpsydial/test/option_a_interactions_en.jsonl \
    --translate --translation_method llm \
    --config_path config.json \
    --max_files 10
```

**Option B / C** (giữ nguyên ngôn ngữ gốc):
```bash
python mindeval/scripts/convert_simpsydial.py \
    --input_dir data/simpsydial/raw \
    --output_path data/simpsydial/test/option_b_interactions_zh.jsonl \
    --max_files 10
```

**Tham số quan trọng:**
- `--translate`: bật dịch thuật
- `--extract_profile`: dùng LLM để trích xuất profile từ dialogue (chỉ với Option A, tốn thêm token)
- `--max_files` / `--max_dialogues`: giới hạn số lượng để test
- `--skip_existing`: mặc định `True`, bỏ qua file đã convert

**Caching**: Lần chạy tiếp theo với cùng `--output_path` sẽ tự động bỏ qua các dialogue đã convert, chỉ xử lý các dialogue mới.

---

### 1.2. Bước 2 — Generate Judgments

```bash
python mindeval/scripts/generate_judgments.py \
    --interactions_path <interactions.jsonl> \
    --judge_template_version v0_1 \
    --judge_model_api_params "{'model':'claude-sonnet-4','api_key':'...'}" \
    --max_workers 10 \
    --output_path <judgments.jsonl>
```

**Cho Option B (Chinese/Korean judge):**
```bash
python mindeval/scripts/generate_judgments.py \
    --interactions_path data/simpsydial/test/option_b_interactions_zh.jsonl \
    --judge_template_path mindeval/judge_prompts_zh.py \
    --judge_model_api_params "{'model':'claude-sonnet-4','api_key':'...'}" \
    --max_workers 10 \
    --output_path data/simpsydial/test/option_b_judgments.jsonl
```

**Judge template versions:**
- `v0_1`: Đánh giá thuần nội dung (mặc định)
- `v0_1_w_length_guidelines`: Penalize responses dài >4 câu trong >10% turns

**Caching**: `skip_existing=True` mặc định — nếu output file đã tồn tại, script chỉ generate các judgments chưa có. An toàn khi chạy lại sau khi bị gián đoạn.

---

### 1.3. Bước 3 — Phân Tích Kết Quả

```python
import pandas as pd
from mindeval.utils import load_jsonl

judgments = load_jsonl("data/simpsydial/test/option_a_judgments.jsonl")
df = pd.DataFrame([j["parsed_judgment"] for j in judgments])

print(df.mean())       # Điểm trung bình từng tiêu chí
print(df.describe())   # Thống kê đầy đủ
```

**So sánh nhiều hệ thống:**
```python
from mindeval.significance_testing import rank_systems

scores_data = {
    "SimPsyDial": [j["parsed_judgment"]["Overall score"] for j in load_jsonl("data/simpsydial/test/option_a_judgments.jsonl")],
    "KMI":        [j["parsed_judgment"]["Overall score"] for j in load_jsonl("data/KMI/test/option_a_judgments.jsonl")],
}
seg_scores = pd.DataFrame(scores_data)
rankings = rank_systems(seg_scores, bootstrap_resampling=True)
print(rankings)
```

---

### 1.4. Đặc Điểm Ngôn Ngữ Không Phải Tiếng Anh

#### Chinese (SimPsyDial, SoulChat) — Option B

**Judge prompt tiếng Trung** nằm ở `mindeval/judge_prompts_zh.py`. Có thể chỉnh sửa trực tiếp.

Quy tắc khi chỉnh sửa:
- **Giữ nguyên** tất cả `${variable_names}` (template variables)
- **Giữ nguyên** tất cả XML tags (`<criterion_1>`, `<member_details>`, v.v.)
- **Giữ format output**: prompt phải yêu cầu model output theo `推理：` / `评分：` hoặc `REASONING:` / `RATINGS:`

**Nếu `thinking_trace` rỗng sau Option B**: Model output Chinese nhưng extraction function không nhận ra.
```bash
python reprocess_judgments_thinking.py data/simpsydial/test/option_b_judgments.jsonl
```

**Nếu `parsed_judgment` tất cả là 3.0 sau Option B**: Score parsing không nhận format Chinese.
```bash
python reparse_judgment_scores.py data/simpsydial/test/option_b_judgments.jsonl
```

Format được support trong `separate_thinking_from_response()` và `parse_judge_scores()`:
- English: `REASONING: ... RATINGS: ...`
- Chinese (standard): `推理：... 评分：...`
- Chinese (alternative): `分析理由：... 评分：...`
- Legacy: `<think>...</think>`
- Score format: `临床准确性（Clinical Accuracy & Competence）: 3.5`

#### Korean (KMI) — Option B

Judge prompt tiếng Hàn: `mindeval/judge_prompts_ko.py`

```bash
python mindeval/scripts/generate_judgments.py \
    --interactions_path data/KMI/test/option_b_interactions_ko.jsonl \
    --judge_template_path mindeval/judge_prompts_ko.py \
    --output_path data/KMI/test/option_b_judgments.jsonl
```

---

### 1.5. Output Fields

| Field | Dùng khi |
|-------|----------|
| `parsed_judgment` | Tính toán, so sánh, vẽ biểu đồ |
| `unparsed_judgment` | Debug format, re-parse với logic mới |
| `thinking_trace` | Explainability, error analysis |

---

## Phần 2: WAI Evaluation

### 2.1. Tổng Quan

WAI (Working Alliance Inventory) đánh giá liên minh trị liệu qua 12 câu hỏi × 3 runs = **36 LLM calls/dialogue**.

**Input**: Cùng file `interactions.jsonl` đã tạo cho Mind-Eval — không cần convert lại.

**So sánh chi phí:**

| | Mind-Eval | WAI |
|--|-----------|-----|
| LLM calls/dialogue | 1 | 36 |
| Tokens/dialogue | ~3,000 | ~108,000 |
| Thời gian/dialogue | ~2–3 giây | ~2–3 phút |

### 2.2. Chạy WAI

```bash
python mindeval/scripts/generate_wai_judgments.py \
    --interactions_path data/simpsydial/test/option_a_interactions_en.jsonl \
    --output_path data/simpsydial/test/option_a_wai_judgments.jsonl \
    --config_path config.json \
    --n_runs 3
```

**Giảm chi phí** (ít chính xác hơn):
```bash
python mindeval/scripts/generate_wai_judgments.py ... --n_runs 1
```

**Lưu ý config**: WAI dùng `temperature=1.0` (theo paper), khác với Mind-Eval (`temperature=0.3`).

### 2.3. Ba Options cho WAI

| Option | Input file | `--language` | Output |
|--------|-----------|--------------|--------|
| A | `option_a_interactions_en.jsonl` | `en` | WAI English |
| B | `option_b_interactions_zh.jsonl` | `zh` | WAI Chinese (cần `wai_prompts_zh.py`) |
| C | `option_c_interactions_zh.jsonl` | `en` | WAI English trên dialogue Chinese |

```bash
# Option A
python run_wai_single_option.py --option A --max_dialogues 10

# Option B (cần dịch wai_prompts_zh.py trước)
python run_wai_single_option.py --option B --max_dialogues 10

# Option C
python run_wai_single_option.py --option C --max_dialogues 10
```

### 2.4. Output Format

```json
{
  "n_runs": 3,
  "questions": {
    "Q1": {"score": 4.33, "individual_scores": [4, 5, 4], ...}
  },
  "dimensions": {"Goal": 4.25, "Approach": 4.0, "Affective Bond": 4.5},
  "total": 4.25
}
```

### 2.5. Phân Tích WAI

```python
import json
import numpy as np

with open("data/simpsydial/test/option_a_wai_judgments.jsonl") as f:
    wai = [json.loads(l) for l in f]

totals = [w["total"] for w in wai]
goals  = [w["dimensions"]["Goal"] for w in wai]
bonds  = [w["dimensions"]["Affective Bond"] for w in wai]

print(f"WAI Total: {np.mean(totals):.2f} ± {np.std(totals):.2f}")
print(f"Goal:      {np.mean(goals):.2f}")
print(f"Bond:      {np.mean(bonds):.2f}")
```

### 2.6. Caching WAI

WAI dùng cùng cơ chế caching như Mind-Eval. Chạy lại sẽ skip dialogues đã có WAI judgment.

---

## Tóm Tắt So Sánh

| Tiêu chí | Mind-Eval | WAI |
|----------|-----------|-----|
| Số metrics | 5 | 12 (3 dimensions) |
| Thang điểm | 1–6 | 1–5 |
| Calls/dialogue | 1 | 36 |
| Tốc độ | Nhanh | Chậm |
| Tập trung | Chất lượng lâm sàng + AI | Liên minh trị liệu |
| Ba options | Có (A/B/C) | Có (A/B/C) |
| Caching | Có | Có |
