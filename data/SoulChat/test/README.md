# SoulChat Test Dataset

## Overview

| Item | Value |
|---|---|
| Source file | `data/SoulChat/raw/SoulChatCorpus-sft-multi-Turn.json` |
| Conversion script | `mindeval/scripts/sample_soulchat.py` |
| Total raw records | 258,353 |
| Valid records (non-empty dialogue) | 258,342 |
| Empty records excluded | 11 |
| **Sample file** | `interactions_200.jsonl` |
| **Sample size** | **200** |
| Sampling method | Topic-stratified (proportional to full-dataset topic distribution) |
| Random seed | 42 |
| Language | Chinese (zh) |

---

## Dataset Description

SoulChat is a large-scale Chinese mental health counselling corpus with **258,353 records**.
Each record has three fields:

| Field | Description |
|-------|-------------|
| `id` | Unique record identifier |
| `topic` | Counselling topic (one of 13 categories) |
| `messages` | List of `{"role": "user"/"assistant", "content": "..."}` turns |

### Topic Categories (13)

| Topic (Chinese) | Topic (English) | Full count | Share |
|-----------------|-----------------|------------|-------|
| 婚恋           | Romantic relationships / marriage        |   55105 |  21.3% |
| 情绪           | Emotions / mood                          |   31796 |  12.3% |
| 人际           | Interpersonal relationships              |   29887 |  11.6% |
| 家庭           | Family                                   |   25609 |   9.9% |
| 治疗           | Treatment / therapy                      |   24620 |   9.5% |
| 成长           | Personal growth                          |   24190 |   9.4% |
| 行为           | Behavioral issues                        |   20960 |   8.1% |
| 自我           | Self / identity                          |   20017 |   7.7% |
| 社会           | Society / social issues                  |    9757 |   3.8% |
| 职场           | Workplace                                |    9173 |   3.6% |
| 心理学知识        | Psychology knowledge                     |    6063 |   2.3% |
| 未明确          | Unspecified                              |     993 |   0.4% |
| 性心理          | Sexual psychology                        |     172 |   0.1% |

---

## How Sampling Was Done

Stratification is by **topic** (proportional to each topic's share in the full dataset).
Quotas are computed via the **largest-remainder (Hamilton) method**.
Empty dialogues (0 valid turns) are excluded before sampling.

| Topic | Full valid | Quota |
|-------|-----------|-------|
| 婚恋           |   55105 ( 21.3%) |  43 |
| 情绪           |   31796 ( 12.3%) |  25 |
| 人际           |   29887 ( 11.6%) |  23 |
| 家庭           |   25609 (  9.9%) |  20 |
| 治疗           |   24620 (  9.5%) |  19 |
| 成长           |   24190 (  9.4%) |  19 |
| 行为           |   20960 (  8.1%) |  16 |
| 自我           |   20017 (  7.7%) |  15 |
| 社会           |    9757 (  3.8%) |   7 |
| 职场           |    9173 (  3.6%) |   7 |
| 心理学知识        |    6063 (  2.3%) |   5 |
| 未明确          |     993 (  0.4%) |   1 |
| 性心理          |     172 (  0.1%) |   0 |

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "id":    "<original record id>",
  "topic": "<topic category>",
  "dialogue": [
      {"role": "user",      "content": "<Chinese text>"},
      {"role": "assistant", "content": "<Chinese text>"},
      ...
  ],
  "metadata": {
      "source":     "SoulChat",
      "language":   "zh",
      "turn_count": <int>
  }
}
```

---

## Sample Statistics (N=200)

### Topic distribution — full vs sample

| Topic        | Full dataset           | Sample (200)       | Deviation | Distribution |
|--------------|------------------------|--------------------|-----------|-------------|
| 婚恋           |   55105 ( 21.3%) |    43 ( 21.5%) | +0.2pp | ████░░░░░░░░░░░░░░░░ |
| 情绪           |   31796 ( 12.3%) |    25 ( 12.5%) | +0.2pp | ██░░░░░░░░░░░░░░░░░░ |
| 人际           |   29887 ( 11.6%) |    23 ( 11.5%) | -0.1pp | ██░░░░░░░░░░░░░░░░░░ |
| 家庭           |   25609 (  9.9%) |    20 ( 10.0%) | +0.1pp | ██░░░░░░░░░░░░░░░░░░ |
| 治疗           |   24620 (  9.5%) |    19 (  9.5%) | -0.0pp | ██░░░░░░░░░░░░░░░░░░ |
| 成长           |   24190 (  9.4%) |    19 (  9.5%) | +0.1pp | ██░░░░░░░░░░░░░░░░░░ |
| 行为           |   20960 (  8.1%) |    16 (  8.0%) | -0.1pp | ██░░░░░░░░░░░░░░░░░░ |
| 自我           |   20017 (  7.7%) |    15 (  7.5%) | -0.2pp | ██░░░░░░░░░░░░░░░░░░ |
| 社会           |    9757 (  3.8%) |     7 (  3.5%) | -0.3pp | █░░░░░░░░░░░░░░░░░░░ |
| 职场           |    9173 (  3.6%) |     7 (  3.5%) | -0.1pp | █░░░░░░░░░░░░░░░░░░░ |
| 心理学知识        |    6063 (  2.3%) |     5 (  2.5%) | +0.2pp | ░░░░░░░░░░░░░░░░░░░░ |
| 未明确          |     993 (  0.4%) |     1 (  0.5%) | +0.1pp | ░░░░░░░░░░░░░░░░░░░░ |
| 性心理          |     172 (  0.1%) |     0 (  0.0%) | -0.1pp | ░░░░░░░░░░░░░░░░░░░░ |

### Turns per dialogue (sample)

| Metric | Value |
|---|---|
| Total turns across all dialogues | 2358 |
| Turns per dialogue | min=2, max=20, mean=11.8, median=12.0 |
| User turns per dialogue | min=1, max=10, mean=5.9, median=6.0 |
| Counsellor turns per dialogue | min=1, max=10, mean=5.9, median=6.0 |
| Total content (chars) per dialogue | min=178, max=1725, mean=746.7, median=692.5 |

### Turn-count percentiles (sample)

| Percentile | Turns |
|-----------|-------|
| P10 | 10 |
| P25 | 10 |
| P50 (median) | 12 |
| P75 | 13 |
| P90 | 14 |

### Full-dataset turn-count (for reference)

min=1, max=46, mean=11.8, median=12.0

---

## Reproduction

```bash
python mindeval/scripts/sample_soulchat.py --n 200 --seed 42
```

To disable stratification (simple random sample):
```bash
python mindeval/scripts/sample_soulchat.py --n 200 --seed 42 --no_stratified
```
