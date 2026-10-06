# Hướng Dẫn Chạy — Tham Chiếu Lệnh

## 0. Thiết Lập

```bash
copy config.example.json config.json
# Mở config.json, điền API keys cho từng judge
```

```json
{
  "translation": {
    "model": "gpt-5.1",
    "api_key": "sk-...",
    "api_base": "https://api.openai.com/v1",
    "temperature": 0.3
  },
  "judges": {
    "gpt":    { "model": "gpt-5.1",                  "api_key": "sk-...",        "api_base": "https://api.openai.com/v1" },
    "claude": { "model": "anthropic/claude-sonnet-4-6", "api_key": "sk-ant-..." },
    "qwen":   { "model": "qwen3-235b-a22b",           "api_key": "sk-...",        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1" }
  }
}
```

> **Qwen3 API key**: Đăng ký tại [dashscope.aliyuncs.com](https://dashscope.aliyuncs.com) → API-KEY management → tạo key mới.

```bash
python check_config.py   # kiểm tra API keys
```

---

## 1. Pipeline tổng quan

Mỗi dataset đi qua 2 bước:

```
raw data  →  [convert script]  →  interactions.jsonl  →  [evaluate.py]  →  judgments.jsonl
```

- **Bước 1 (Convert)**: chỉ chạy 1 lần — chuyển format thô sang `interactions.jsonl`
- **Bước 2 (Evaluate)**: chạy mỗi khi cần đánh giá — dùng `evaluate.py`

> **Không cần tạo profile**: Các convert script tự dùng `DEFAULT_PROFILE` (tất cả field là "Unknown").
> Không cần flag `--extract_profile`.

---

## 2. Lựa chọn ngôn ngữ (Option A / B / C)

| Option | Dialogue | Judge prompt | Dùng khi |
|--------|----------|--------------|----------|
| A | English (đã dịch) | English | So sánh chuẩn, dễ đọc kết quả |
| B | Ngôn ngữ gốc | Ngôn ngữ gốc | Đánh giá thuần ngữ cảnh bản địa |
| C | Ngôn ngữ gốc | English | **Khuyến nghị**: tiết kiệm token dịch, judge mạnh |

---

## 3. SimPsyDial (Chinese)

### Bước 1: Convert (chạy 1 lần)

```bash
# Option A — dịch sang English
python mindeval/scripts/convert_simpsydial.py \
    --input_dir data/simpsydial/raw \
    --output_path data/simpsydial/test/option_a_interactions_en.jsonl \
    --translate --translation_method llm \
    --config_path config.json \
    --max_files 10

# Option B hoặc C — giữ nguyên tiếng Trung (dùng chung 1 file)
python mindeval/scripts/convert_simpsydial.py \
    --input_dir data/simpsydial/raw \
    --output_path data/simpsydial/test/option_c_interactions_zh.jsonl \
    --max_files 10

# Option B dùng cùng file (chỉ khác judge prompt ở bước evaluate)
copy data\simpsydial\test\option_c_interactions_zh.jsonl \
     data\simpsydial\test\option_b_interactions_zh.jsonl
```

### Bước 2: Evaluate

```bash
# Option C — Chinese dialogue + English judge (khuyến nghị)
python evaluate.py --dataset simpsydial --option c --eval both

# Option A — English dialogue + English judge
python evaluate.py --dataset simpsydial --option a --eval both

# Option B — Chinese dialogue + Chinese judge
python evaluate.py --dataset simpsydial --option b --eval both

# Chỉ 5-metric, giới hạn 50 dialogues
python evaluate.py --dataset simpsydial --option c --eval mind-eval --max_dialogues 50

# Chỉ WAI
python evaluate.py --dataset simpsydial --option c --eval wai --max_dialogues 50
```

---

## 4. KMI (Korean)

### Bước 1: Convert (chạy 1 lần)

```bash
# Tất cả options — KMI đã có sẵn cả EN và KO
python mindeval/scripts/convert_kmi.py \
    --input_path data/KMI/raw/kmi.json \
    --output_dir data/KMI/test \
    --max_dialogues 100
```

### Bước 2: Evaluate

```bash
# Option C — Korean dialogue + English judge (khuyến nghị)
python evaluate.py --dataset kmi --option c --eval both

# Option A — English dialogue + English judge
python evaluate.py --dataset kmi --option a --eval both

# Option B — Korean dialogue + Korean judge
python evaluate.py --dataset kmi --option b --eval both
```

---

## 5. SoulChat (Chinese)

### Bước 1: Convert (chạy 1 lần)

```bash
# Option B / C — giữ nguyên tiếng Trung
python mindeval/scripts/convert_soulchat.py \
    --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
    --output_path data/SoulChat/test/option_c_interactions_zh.jsonl \
    --max_dialogues 100

copy data\SoulChat\test\option_c_interactions_zh.jsonl \
     data\SoulChat\test\option_b_interactions_zh.jsonl

# Option A — dịch sang English
python mindeval/scripts/convert_soulchat.py \
    --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
    --output_path data/SoulChat/test/option_a_interactions_en.jsonl \
    --translate --translation_method llm \
    --config_path config.json \
    --max_dialogues 100
```

### Bước 2: Evaluate

```bash
# Option C — Chinese dialogue + English judge (khuyến nghị)
python evaluate.py --dataset soulchat --option c --eval both

# Option A — English dialogue + English judge
python evaluate.py --dataset soulchat --option a --eval both
```

---

## 6. Thêm dataset mới

1. Viết `mindeval/scripts/convert_<dataset>.py` theo mẫu `convert_soulchat.py`:
   - Dùng `DEFAULT_PROFILE` (không cần `--extract_profile`)
   - Roles: `"user"` (client) và `"assistant"` (counselor)
   - Output: `interactions.jsonl` chuẩn Mind-Eval

2. Đăng ký trong `evaluate.py` ở dict `DATASETS`:
   ```python
   "newdataset": {
       "display": "My New Dataset",
       "options": {
           "c": {
               "interactions": "data/NewDataset/test/option_c_interactions.jsonl",
               "judge_template_version": "v0_1",
               "wai_language": "en",
               "description": "Original dialogue + English judge",
           },
       },
   },
   ```

3. Chạy:
   ```bash
   python evaluate.py --dataset newdataset --option c --eval both
   ```

---

## 7. Cấu trúc thư mục chuẩn

Mỗi dataset tuân theo cấu trúc:

```
data/<dataset>/
├── raw/                          # dataset gốc (không chỉnh sửa)
├── test/                         # interactions.jsonl sau khi convert
│   ├── option_a_interactions_en.jsonl
│   ├── option_b_interactions_<lang>.jsonl
│   └── option_c_interactions_<lang>.jsonl
└── results/                      # kết quả đánh giá
    ├── mind_eval/                # 5-metric judgments
    │   ├── option_a_judgments.jsonl
    │   ├── option_b_judgments.jsonl
    │   └── option_c_judgments.jsonl
    └── wai/                      # WAI judgments
        ├── option_a_wai_judgments.jsonl
        ├── option_b_wai_judgments.jsonl
        └── option_c_wai_judgments.jsonl
```

`evaluate.py` tự động tạo thư mục `results/mind_eval/` và `results/wai/` khi chạy.

---

## 8. Xem danh sách dataset và trạng thái

```bash
python evaluate.py --list
```

---

## 9. Chạy với nhiều judge (GPT / Claude / Qwen)

Chọn judge bằng `--judge_name`. Mỗi judge tạo file riêng biệt (e.g. `S1_qwen_judgments.jsonl`, `S3_qwen_judgments.jsonl`).

### Settings S1 vs S3

| Setting | File input | Mô tả |
|---------|-----------|-------|
| **S1** | `*_S1_en.jsonl` (đã dịch EN) | Dialogue tiếng Anh + judge EN |
| **S3** | `*_canonical*.jsonl` (bản ngữ) | Dialogue ngôn ngữ gốc + judge EN |

> **EN datasets** (cactus, psy_insight, annomi, esconv, esconv): S1 = S3 (cùng file canonical).
> Chỉ chạy S1, `copy_en_results()` tự động copy `S1_*.jsonl` → `S3_*.jsonl` sau khi xong.

### Câu lệnh chạy S1 + S3 (bỏ S2)

```bash
# Pilot — kiểm tra trước khi chạy full
python -m mindeval.scripts.run_eval_matrix --pilot --eval mind-eval --judge_name qwen --settings S1 S3 --max_workers 2 --batch_delay 2

# Full run
python -m mindeval.scripts.run_eval_matrix --full --eval mind-eval --judge_name qwen --settings S1 S3 --max_workers 2 --batch_delay 2
```

### Câu lệnh theo từng judge

```bash
# Judge 1: GPT
python -m mindeval.scripts.run_eval_matrix --full --eval mind-eval --judge_name gpt --settings S1 S3 --max_workers 3

# Judge 2: Claude (giới hạn workers do rate-limit Anthropic)
python -m mindeval.scripts.run_eval_matrix --full --eval mind-eval --judge_name claude --settings S1 S3 --max_workers 1 --batch_delay 5

# Judge 3: Qwen3 (thinking tắt, tiết kiệm token)
python -m mindeval.scripts.run_eval_matrix --full --eval mind-eval --judge_name qwen --settings S1 S3 --max_workers 2 --batch_delay 2
```

Chạy 1 dataset cụ thể với Qwen3:
```bash
python evaluate.py --dataset simpsydial --option S1 --eval mind-eval --judge_name qwen
python evaluate.py --dataset simpsydial --option S3 --eval mind-eval --judge_name qwen
```

So sánh kết quả giữa các judge:
```bash
python -m mindeval.scripts.analyze_results --judge_name qwen
```

---

## 10. Phân tích kết quả

```python
import json
import pandas as pd

# Đọc Mind-Eval 5-metric judgments
judgments = [json.loads(l) for l in open("data/simpsydial/results/mind_eval/option_c_judgments.jsonl")]
scores_df = pd.DataFrame([j["parsed_judgment"] for j in judgments])

# Điểm trung bình 5 metric (thang 1-6)
print(scores_df.mean().round(3))

# Đọc WAI judgments
wai = [json.loads(l) for l in open("data/simpsydial/results/wai/option_c_wai_judgments.jsonl")]
wai_df = pd.DataFrame([w["dimensions"] for w in wai])

# Điểm trung bình 3 dimension WAI (thang 1-5)
print(wai_df.mean().round(3))
```

---

## 10. Xử lý sự cố

```bash
# Kiểm tra config
python check_config.py

# Xem cấu hình hiện tại
python view_config.py

# Reparse scores từ judgments đã có (không tốn API)
python reparse_judgment_scores.py \
    --input_path data/simpsydial/results/mind_eval/option_c_judgments.jsonl \
    --output_path data/simpsydial/results/mind_eval/option_c_judgments.jsonl

# Buộc đánh giá lại từ đầu (bỏ qua cache)
python evaluate.py --dataset simpsydial --option c --eval mind-eval --no_skip
```
