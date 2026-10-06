# PsyDial Test Dataset

## Overview

| Item | Value |
|---|---|
| Source file | `data/PsyDial/raw/PsyDial-D4.json` |
| Conversion script | `mindeval/scripts/convert_psydial.py` |
| Total raw records | 2,382 |
| **Sample file** | `interactions_200.jsonl` |
| **Sample size** | **200** |
| Sampling method | Length-stratified (proportional by dialogue-turn bucket) |
| Random seed | 42 |
| Language | Chinese (zh) |

---

## Dataset Description

PsyDial-D4 is a Chinese psychological counselling dialogue corpus.  Every record
contains a `messages` list with roles **system / user / assistant**:

| Role | Meaning | Included in output? |
|------|---------|-------------------|
| `system` | Counsellor persona prompt (小天, identical in all records) | **No** (excluded) |
| `user` | Client (来访者) utterances | **Yes** |
| `assistant` | Virtual counsellor 小天 utterances | **Yes** |

### Counsellor Persona (小天)

The single shared system prompt describes the virtual counsellor:

- **Name / Gender**: 小天 (Xiaotian) · Female
- **Approach**: Humanistic, Psychoanalytic, Cognitive-Behavioural Therapy (CBT)
- **Skills**: Identify and challenge unhealthy thinking; empathic support
- **Three counselling stages**:
  1. **Early stage** – build rapport, collect background information, clarify goals
  2. **Middle stage** – guide self-awareness and growth; explore emotions, cognitions, and coping
  3. **Late stage** – summarise changes and achievements; plan next steps

---

## How Sampling Was Done

PsyDial carries no topic or category labels, so stratification is based on
**dialogue length** (number of user + assistant turns):

| Bucket | Range | Full dataset | Target quota |
|--------|-------|-------------|-------------|
| short | < 30 turns | 62 (2.6%) | 5 |
| medium | 30-59 turns | 778 (32.7%) | 65 |
| long | 60-99 turns | 1044 (43.8%) | 88 |
| very_long | >= 100 turns | 498 (20.9%) | 42 |

Quotas are computed via the **largest-remainder (Hamilton) method** to ensure
the sample proportions mirror the full dataset.

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "dialogue": [
      {"role": "user",      "content": "<Chinese text>"},
      {"role": "assistant", "content": "<Chinese text>"},
      ...
  ],
  "metadata": {
      "source":         "PsyDial",
      "original_index": <int>,
      "language":       "zh",
      "turn_count":     <int>,
      "length_bucket":  "short|medium|long|very_long"
  }
}
```

---

## Full Dataset Statistics

### Dialogue length distribution (full dataset, N=2,382)

| Bucket | Count | Share |
|--------|-------|-------|
| Short  (<30 turns)    |    62 |   2.6% |
| Medium (30-59 turns)  |   778 |  32.7% |
| Long   (60-99 turns)  |  1044 |  43.8% |
| Very Long (>=100 turns)|   498 |  20.9% |

Full dataset turn-count: min=18, max=240, mean=75.6, median=70.0

---

## Sample Statistics (N=200)

### Dialogue length bucket — full vs sample

| Bucket                   | Full dataset       | Sample (200)       | Deviation | Distribution |
|--------------------------|--------------------|--------------------|-----------|-------------|
| Short  (<30 turns)       |    62 (  2.6%) |     5 (  2.5%) | -0.1pp | ░░░░░░░░░░░░░░░░░░░░ |
| Medium (30-59 turns)     |   778 ( 32.7%) |    65 ( 32.5%) | -0.2pp | ██████░░░░░░░░░░░░░░ |
| Long   (60-99 turns)     |  1044 ( 43.8%) |    88 ( 44.0%) | +0.2pp | █████████░░░░░░░░░░░ |
| Very Long (>=100 turns)  |   498 ( 20.9%) |    42 ( 21.0%) | +0.1pp | ████░░░░░░░░░░░░░░░░ |

### Turns per dialogue (sample)

| Metric | Value |
|---|---|
| Total turns across all dialogues | 14952 |
| Turns per dialogue | min=18, max=198, mean=74.8, median=70.0 |
| User turns per dialogue | min=9, max=99, mean=37.4, median=35.0 |
| Counsellor turns per dialogue | min=9, max=99, mean=37.4, median=35.0 |
| Total content (chars) per dialogue | min=784, max=5209, mean=2399.2, median=2255.5 |

### Turn-count percentiles (sample)

| Percentile | Turns |
|-----------|-------|
| P10 | 40 |
| P25 | 50 |
| P50 (median) | 70 |
| P75 | 94 |
| P90 | 116 |

---

## Reproduction

```bash
python mindeval/scripts/convert_psydial.py --n 200 --seed 42
```

To disable stratification (simple random sample):
```bash
python mindeval/scripts/convert_psydial.py --n 200 --seed 42 --no_stratified
```
