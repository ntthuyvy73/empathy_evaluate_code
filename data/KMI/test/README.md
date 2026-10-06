# KMI Test Dataset

## Overview

| Item | Value |
|---|---|
| Source file | `data/KMI/raw/kmi.json` |
| Conversion script | `mindeval/scripts/convert_kmi.py` |
| Total raw dialogues | 1,000 |
| Unique categories | 7 |
| **Sample file** | `interactions_200.jsonl` |
| **Sample size** | **200** |
| Sampling method | Stratified random by `category_en` (proportional to full dataset) |
| Random seed | 42 |

---

## How Sampling Was Done

1. **Load** all 1000 dialogues from `kmi.json`.
2. **Group** by `category_en` — 7 categories with unequal sizes.
3. **Compute quota** per category using the largest-remainder method so
   the 200 sampled records match the full-dataset proportions exactly.
4. **Sample randomly** within each category (seed=42) up to its quota.
5. **Shuffle** the combined result.

Quotas: proportional allocation → Mental Health **40**, Interpersonal
Relationships **40**, Ego·Personality **40**, Career·Employment **40**,
Academic·Examination **20**, Addiction·Obsession **10**, Family **10**.

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "id":          123,
  "category_en": "<category>",
  "dialogue": [
      {"role": "Therapist", "content": "...", "label": "<MI technique>"},
      {"role": "Client",    "content": "..."},
      ...
  ]
}
```

`label` is present only on **Therapist** turns and represents the
Motivational Interviewing (MI) technique used.

---

## Category Distribution

| Category | Full dataset | Sample | Deviation | Top MI label (sample) |
|---|---|---|---|---|
| Mental Health                  |          200 ( 20.0%) |     40 ( 20.0%) |  +0.0pp | Open Question (128) |
| Interpersonal Relationships    |          200 ( 20.0%) |     40 ( 20.0%) |  +0.0pp | Complex Reflection (135) |
| Ego·Personality                |          200 ( 20.0%) |     40 ( 20.0%) |  +0.0pp | Open Question (132) |
| Career·Employment              |          200 ( 20.0%) |     40 ( 20.0%) |  +0.0pp | Complex Reflection (126) |
| Academic·Examination           |          100 ( 10.0%) |     20 ( 10.0%) |  +0.0pp | Complex Reflection (59) |
| Addiction·Obsession            |           50 (  5.0%) |     10 (  5.0%) |  +0.0pp | Open Question (35) |
| Family                         |           50 (  5.0%) |     10 (  5.0%) |  +0.0pp | Open Question (39) |
| **Total** | **1000 (100.0%)** | **200 (100.0%)** | **—** | |

> **Deviation** = sample% − full-dataset%.  Values near 0 confirm the
> stratified sampling preserved original proportions.

---

## Dialogue Statistics

| Metric | Value |
|---|---|
| Total turns across all dialogues | 3592 |
| Turns per dialogue — min=15, max=31, mean=18.0, median=17.0 | |
| Therapist turns per dialogue — min=8, max=16, mean=9.5, median=9.0 | |
| Client turns per dialogue — min=7, max=15, mean=8.5, median=8.0 | |

---

## Therapist MI Label Distribution (all turns in sample)

Total labelled Therapist turns: **1896**

| MI Technique | Turns | Share | Distribution |
|---|---|---|---|
| Open Question             |    645 |  34.0% | ███████░░░░░░░░░░░░░ |
| Complex Reflection        |    618 |  32.6% | ███████░░░░░░░░░░░░░ |
| Simple Reflection         |    256 |  13.5% | ███░░░░░░░░░░░░░░░░░ |
| Affirm                    |    188 |   9.9% | ██░░░░░░░░░░░░░░░░░░ |
| General                   |    144 |   7.6% | ██░░░░░░░░░░░░░░░░░░ |
| Closed Question           |     27 |   1.4% | ░░░░░░░░░░░░░░░░░░░░ |
| Give Information          |     11 |   0.6% | ░░░░░░░░░░░░░░░░░░░░ |
| Advise                    |      7 |   0.4% | ░░░░░░░░░░░░░░░░░░░░ |
| **Total** | **1896** | **100%** | |

---

## MI Label Breakdown per Category

### Mental Health

| MI Label | Turns | Share (in category) |
|---|---|---|
| Open Question             |   128 |  34.9% |
| Complex Reflection        |   117 |  31.9% |
| Simple Reflection         |    48 |  13.1% |
| General                   |    34 |   9.3% |
| Affirm                    |    29 |   7.9% |
| Closed Question           |     8 |   2.2% |
| Give Information          |     2 |   0.5% |
| Advise                    |     1 |   0.3% |

### Interpersonal Relationships

| MI Label | Turns | Share (in category) |
|---|---|---|
| Complex Reflection        |   135 |  36.0% |
| Open Question             |   128 |  34.1% |
| Simple Reflection         |    41 |  10.9% |
| Affirm                    |    36 |   9.6% |
| General                   |    27 |   7.2% |
| Closed Question           |     6 |   1.6% |
| Give Information          |     2 |   0.5% |

### Ego·Personality

| MI Label | Turns | Share (in category) |
|---|---|---|
| Open Question             |   132 |  33.8% |
| Complex Reflection        |   120 |  30.8% |
| Simple Reflection         |    62 |  15.9% |
| Affirm                    |    37 |   9.5% |
| General                   |    29 |   7.4% |
| Closed Question           |     5 |   1.3% |
| Advise                    |     3 |   0.8% |
| Give Information          |     2 |   0.5% |

### Career·Employment

| MI Label | Turns | Share (in category) |
|---|---|---|
| Complex Reflection        |   126 |  33.2% |
| Open Question             |   125 |  32.9% |
| Affirm                    |    47 |  12.4% |
| Simple Reflection         |    46 |  12.1% |
| General                   |    29 |   7.6% |
| Closed Question           |     3 |   0.8% |
| Advise                    |     2 |   0.5% |
| Give Information          |     2 |   0.5% |

### Academic·Examination

| MI Label | Turns | Share (in category) |
|---|---|---|
| Complex Reflection        |    59 |  32.6% |
| Open Question             |    58 |  32.0% |
| Simple Reflection         |    36 |  19.9% |
| Affirm                    |    16 |   8.8% |
| General                   |     9 |   5.0% |
| Give Information          |     2 |   1.1% |
| Closed Question           |     1 |   0.6% |

### Addiction·Obsession

| MI Label | Turns | Share (in category) |
|---|---|---|
| Open Question             |    35 |  35.7% |
| Complex Reflection        |    27 |  27.6% |
| Simple Reflection         |    11 |  11.2% |
| Affirm                    |    11 |  11.2% |
| General                   |    10 |  10.2% |
| Closed Question           |     2 |   2.0% |
| Give Information          |     1 |   1.0% |
| Advise                    |     1 |   1.0% |

### Family

| MI Label | Turns | Share (in category) |
|---|---|---|
| Open Question             |    39 |  37.1% |
| Complex Reflection        |    34 |  32.4% |
| Simple Reflection         |    12 |  11.4% |
| Affirm                    |    12 |  11.4% |
| General                   |     6 |   5.7% |
| Closed Question           |     2 |   1.9% |

---

## Reproduction

```bash
# Stratified sample (default)
python mindeval/scripts/convert_kmi.py --n 200 --seed 42

# Simple random sample (no stratification)
python mindeval/scripts/convert_kmi.py --n 200 --no_stratified --seed 42

# All 1000 records
python mindeval/scripts/convert_kmi.py --n 0
```
