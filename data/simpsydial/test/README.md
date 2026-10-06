# SimPsyDial Test Dataset

## Overview

| Item | Value |
|---|---|
| Source directory | `data/simpsydial/raw/` |
| Conversion script | `mindeval/scripts/sample_simpsydial.py` |
| Total raw files (dialogues) | 1,000 |
| **Sample file** | `interactions_200.jsonl` |
| **Sample size** | **200** |
| Sampling method | Length-stratified (proportional by dialogue-turn bucket) |
| Random seed | 42 |
| Language | Chinese (zh) |

---

## Dataset Description

SimPsyDial contains **1,000 individual JSON files** (one per dialogue).
Each file is a list of turns:

```json
[
  {"role": "client",    "content": "..."},
  {"role": "counselor", "content": "..."},
  ...
]
```

| Raw role | Output role |
|----------|------------|
| `client` | `user` |
| `counselor` | `assistant` |

No topic or category labels are present.
Stratification is based on **dialogue length** (number of turns per file).

---

## How Sampling Was Done

| Bucket | Range | Full dataset | Target quota |
|--------|-------|-------------|-------------|
| short | < 25 turns | 361 (36.1%) | 72 |
| medium | 25-34 turns | 483 (48.3%) | 97 |
| long | >= 35 turns | 156 (15.6%) | 31 |

Quotas are computed via the **largest-remainder (Hamilton) method** so that
the sample proportions mirror the full dataset.

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "dialogue": [
      {"role": "client",    "content": "<Chinese text>"},
      {"role": "counselor", "content": "<Chinese text>"},
      ...
  ],
  "metadata": {
      "source":         "SimPsyDial",
      "original_file":  "<id>.json",
      "language":       "zh",
      "turn_count":     <int>,
      "length_bucket":  "short|medium|long"
  }
}
```

---

## Full Dataset Statistics

### Dialogue length distribution (full dataset, N=1,000)

| Bucket | Count | Share |
|--------|-------|-------|
| Short  (<25 turns)   |   361 |  36.1% |
| Medium (25-34 turns) |   483 |  48.3% |
| Long   (>=35 turns)  |   156 |  15.6% |

Full dataset turn-count: min=20, max=68, mean=28.7, median=28.0

---

## Sample Statistics (N=200)

### Dialogue length bucket — full vs sample

| Bucket                 | Full dataset       | Sample (200)       | Deviation | Distribution |
|------------------------|--------------------|--------------------|-----------|-------------|
| Short  (<25 turns)     |   361 ( 36.1%) |    72 ( 36.0%) | -0.1pp | ███████░░░░░░░░░░░░░ |
| Medium (25-34 turns)   |   483 ( 48.3%) |    97 ( 48.5%) | +0.2pp | ██████████░░░░░░░░░░ |
| Long   (>=35 turns)    |   156 ( 15.6%) |    31 ( 15.5%) | -0.1pp | ███░░░░░░░░░░░░░░░░░ |

### Turns per dialogue (sample)

| Metric | Value |
|---|---|
| Total turns across all dialogues | 5746 |
| Turns per dialogue | min=20, max=58, mean=28.7, median=28.0 |
| Client (user) turns per dialogue | min=10, max=29, mean=14.4, median=14.0 |
| Counselor turns per dialogue | min=10, max=29, mean=14.4, median=14.0 |
| Total content (chars) per dialogue | min=520, max=4333, mean=1462.1, median=1367.0 |

### Turn-count percentiles (sample)

| Percentile | Turns |
|-----------|-------|
| P10 | 22 |
| P25 | 24 |
| P50 (median) | 28 |
| P75 | 32 |
| P90 | 38 |

---

## Reproduction

```bash
python mindeval/scripts/sample_simpsydial.py --n 200 --seed 42
```

To disable stratification (simple random sample):
```bash
python mindeval/scripts/sample_simpsydial.py --n 200 --seed 42 --no_stratified
```
