# SoulChat Dataset — Mind-Eval Integration

## Dataset Overview

SoulChat là corpus đa lượt Chinese empathy conversations với 258K hội thoại tư vấn tâm lý (Apache 2.0 license).

- **Source**: [SoulChat GitHub](https://github.com/scutcyr/SoulChat) / HuggingFace
- **Paper**: EMNLP 2023
- **Language**: Chinese (Simplified)
- **Size**: ~258K multi-turn conversations
- **Data location**: `data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json`

## SoulChat Data Format

```json
{
  "topic": "情感问题",
  "messages": [
    {"role": "用户", "content": "我最近很难过..."},
    {"role": "心理咨询师", "content": "听起来你正在经历一段很艰难的时期..."},
    {"role": "用户", "content": "是的，我不知道该怎么办"},
    {"role": "心理咨询师", "content": "能告诉我更多关于你的感受吗？"}
  ]
}
```

**Role mapping:**
- `用户` (user) → client
- `心理咨询师` (psychologist) → counselor

## Directory Structure

```
data/SoulChat/
├── README.md                           ← this file (Mind-Eval specific)
└── SoulChatCorpus/                     ← upstream git LFS clone
    ├── README.md                       ← upstream dataset card
    ├── dataset_infos.json
    └── SoulChatCorpus-sft-multi-Turn.json   ← main data (~258K conversations)
```

## Evaluation Pipeline

SoulChat là Chinese dataset → dùng **cùng pipeline 3 options** như SimPsyDial:

| Option | Description | Best for |
|--------|-------------|----------|
| A | Translate to English → English judge | Cross-dataset comparison |
| B | Keep Chinese → Chinese judge | Native cultural evaluation |
| C | Keep Chinese → English judge | Cross-lingual, English output |

## Step-by-Step Evaluation

### Step 0: Prepare data directory

```bash
mkdir data\SoulChat\test
```

### Step 1: Convert SoulChat to Mind-Eval format

```bash
# Option A: Translate to English (for English judge)
python mindeval/scripts/convert_soulchat.py \
    --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
    --output_path data/SoulChat/test/option_a_interactions_en.jsonl \
    --translate \
    --translation_method llm \
    --config_path config.json \
    --max_dialogues 50

# Option B/C: Keep Chinese (no translation)
python mindeval/scripts/convert_soulchat.py \
    --input_path data/SoulChat/SoulChatCorpus/SoulChatCorpus-sft-multi-Turn.json \
    --output_path data/SoulChat/test/option_b_interactions_zh.jsonl \
    --max_dialogues 50
```

### Step 2: Generate Mind-Eval Judgments

```bash
# Option A: English judge
python mindeval/scripts/generate_judgments.py \
    --interactions_path data/SoulChat/test/option_a_interactions_en.jsonl \
    --judge_template_version v0_1 \
    --judge_model_api_params "{'model':'claude-sonnet-4','api_key':'...'}" \
    --max_workers 10 \
    --output_path data/SoulChat/test/option_a_judgments.jsonl

# Option B: Chinese judge
python mindeval/scripts/generate_judgments.py \
    --interactions_path data/SoulChat/test/option_b_interactions_zh.jsonl \
    --judge_template_path mindeval/judge_prompts_zh.py \
    --judge_model_api_params "{'model':'claude-sonnet-4','api_key':'...'}" \
    --max_workers 10 \
    --output_path data/SoulChat/test/option_b_judgments.jsonl

# Option C: Chinese dialogue + English judge
python mindeval/scripts/generate_judgments.py \
    --interactions_path data/SoulChat/test/option_b_interactions_zh.jsonl \
    --judge_template_version v0_1 \
    --judge_model_api_params "{'model':'claude-sonnet-4','api_key':'...'}" \
    --max_workers 10 \
    --output_path data/SoulChat/test/option_c_judgments.jsonl
```

### Step 3: Analyze Results

```python
import pandas as pd
from mindeval.utils import load_jsonl

judgments = load_jsonl("data/SoulChat/test/option_a_judgments.jsonl")
df = pd.DataFrame([j["parsed_judgment"] for j in judgments])
print("=== Average Scores (SoulChat) ===")
print(df.mean())
print(f"\nN dialogues: {len(df)}")
```

### Step 4: Optional WAI Evaluation

```bash
python mindeval/scripts/generate_wai_judgments.py \
    --interactions_path data/SoulChat/test/option_a_interactions_en.jsonl \
    --output_path data/SoulChat/test/option_a_wai_judgments.jsonl \
    --config_path config.json \
    --n_runs 3
```

## Sampling Strategy

Dataset có 258K conversations — không cần đánh giá tất cả.

| Scale | N dialogues | Estimated cost (Option A) | Purpose |
|-------|-------------|--------------------------|---------|
| Pilot | 10 | ~$0.20 | Verify pipeline |
| Small | 100 | ~$1.50 | Initial results |
| Medium | 500 | ~$7.50 | Research use |
| Full sample | 1000 | ~$15 | Publication |

**Gợi ý**: Sample random từ dataset để đảm bảo diversity về topic.

## Notes

- SoulChat không có structured profile → script dùng default profile (`DEFAULT_PROFILE`)
- Nếu muốn extract profile từ dialogue → dùng `--extract_profile` (tốn thêm token)
- Caching tự động được bật (`skip_existing=True`) — an toàn khi chạy lại

## Related Documentation

- `THREE-WAY-EVALUATION-GUIDE.md` — Options A/B/C
- `CACHING-GUIDE.md` — Caching mechanism
- `CHINESE-PROMPT-GUIDE.md` — Option B Chinese prompt
- `CONFIGURATION-SETUP.md` — Config setup
