# Psy-Insight Test Dataset

## Overview

| Item | Value |
|---|---|
| Source file | `data/Psy-Insight/raw/en_data_version7.json` |
| Conversion script | `mindeval/scripts/sample_psyinsight.py` |
| Total raw records | 520 |
| **Sample file** | `interactions_200.jsonl` |
| **Sample size** | **200** |
| Sampling method | Psychotherapy-stratified (proportional) with topic-balanced sub-sampling |
| Random seed | 42 |
| Language | English (en) |

---

## Dataset Description

Psy-Insight is an English psychotherapy dialogue corpus with **520 annotated sessions**
covering **13 psychotherapy modalities** and **12 clinical topics**.

### Record-level fields

| Field | Type | Description |
|-------|------|-------------|
| `dialog_id` | str | Unique session identifier |
| `psychotherapy` | str | Psychotherapy approach (13 types) |
| `topic` | str | Clinical topic / presenting concern (12 types) |
| `background` | str | Brief case scenario description |
| `theme` | str | Specific therapeutic theme addressed |
| `reasoning` | str | Explanation of the therapeutic rationale |
| `dialog` | list | Annotated dialogue turns (see below) |
| `summary` | str | Session summary and clinical insights |
| `is_same_session` | 0/1 | Whether Q&A pairs come from the same session |
| `is_same_qa` | 0/1 | Whether Q&A comes from the same Q&A pair |

### Dialog turn fields

Each turn has role-specific annotation fields:

| Field | Seeker (Client) | Supporter (Therapist) |
|-------|----------------|----------------------|
| `speaker` | `"Seeker"` | `"Supporter"` |
| `participant` | `"Client"` | `"Therapist"` |
| `content` | ✓ | ✓ |
| `id` | ✓ | ✓ |
| `observation` | ✓ (therapist's observation of client state) | — |
| `emotional label` | ✓ (list of emotion labels) | — |
| `reasoning` | — | ✓ (rationale for therapist's response) |
| `strategy` | — | ✓ (list of therapy strategies used) |
| `reference_labels` | sometimes | sometimes |

---

## How Sampling Was Done

1. **Primary stratification by `psychotherapy`** (proportional, largest-remainder method):
   each therapy type is represented in proportion to its share in the full dataset.
2. **Secondary balancing by `topic`** within each psychotherapy bucket:
   topics within a bucket are sub-sampled proportionally.
3. Empty `topic` values are treated as `"Unspecified"`.

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "dialog_id":     "...",
  "psychotherapy": "...",
  "topic":         "...",
  "background":    "...",
  "theme":         "...",
  "reasoning":     "...",
  "dialog": [
    {
      "speaker":        "Seeker",
      "participant":    "Client",
      "content":        "...",
      "id":             "0-0",
      "observation":    "...",
      "emotional label": ["Anxiety", "Sadness"]
    },
    {
      "speaker":     "Supporter",
      "participant": "Therapist",
      "content":     "...",
      "id":          "0-1",
      "reasoning":   "...",
      "strategy":    ["Question"]
    }
  ],
  "summary":  "...",
  "metadata": {
      "source":          "Psy-Insight",
      "language":        "en",
      "turn_count":      <int>,
      "is_same_session": 0 | 1,
      "is_same_qa":      0 | 1
  }
}
```

---

## Full Dataset Statistics

### Psychotherapy distribution (full dataset, N=520)

| Psychotherapy | Count | Share |
|---------------|-------|-------|
| Solution-Focused Brief Therapy                | 350 |  67.3% |
| Psychoanalytic Therapy                        |  44 |   8.5% |
| Cognitive Behaviour Therapy                   |  40 |   7.7% |
| Client-Centered Therapy                       |  22 |   4.2% |
| Adlerian Therapy                              |  16 |   3.1% |
| Family Therapy                                |  10 |   1.9% |
| Acceptance Commitment Therapy                 |   8 |   1.5% |
| Marriage and Family Systems Therapy           |   8 |   1.5% |
| Rational Emotive Behavior Therapy             |   8 |   1.5% |
| Gestalt Therapy                               |   5 |   1.0% |
| Reality Therapy                               |   4 |   0.8% |
| Postmodern Therapy                            |   3 |   0.6% |
| Existential Therapy                           |   2 |   0.4% |

### Topic distribution (full dataset)

| Topic | Count | Share |
|-------|-------|-------|
| Ongoing Depression                  | 102 |  19.6% |
| Partner Relationship Issues         |  96 |  18.5% |
| Child-Parent Relationship Issues    |  96 |  18.5% |
| Appearance Anxiety                  |  59 |  11.3% |
| Academic Pressure                   |  49 |   9.4% |
| Job Crisis                          |  37 |   7.1% |
| Substance Abuse                     |  20 |   3.8% |
| Unspecified                         |  19 |   3.7% |
| School Bullying                     |  18 |   3.5% |
| Friend Problems                     |  15 |   2.9% |
| Sleep Problems                      |   5 |   1.0% |
| Procrastination                     |   4 |   0.8% |

Full dataset dialog-turn count: min=2, max=194, mean=11.9, median=8.0

---

## Sample Statistics (N=200)

### Psychotherapy distribution — full vs sample

| Psychotherapy                                 | Full dataset    | Sample (200)    | Deviation | Distribution |
|-----------------------------------------------|-----------------|-----------------|-----------|-------------|
| Solution-Focused Brief Therapy                | 350 ( 67.3%) | 135 ( 67.5%) | +0.2pp | ██████████████░░░░░░ |
| Psychoanalytic Therapy                        |  44 (  8.5%) |  17 (  8.5%) | +0.0pp | ██░░░░░░░░░░░░░░░░░░ |
| Cognitive Behaviour Therapy                   |  40 (  7.7%) |  15 (  7.5%) | -0.2pp | ██░░░░░░░░░░░░░░░░░░ |
| Client-Centered Therapy                       |  22 (  4.2%) |   8 (  4.0%) | -0.2pp | █░░░░░░░░░░░░░░░░░░░ |
| Adlerian Therapy                              |  16 (  3.1%) |   6 (  3.0%) | -0.1pp | █░░░░░░░░░░░░░░░░░░░ |
| Family Therapy                                |  10 (  1.9%) |   4 (  2.0%) | +0.1pp | ░░░░░░░░░░░░░░░░░░░░ |
| Acceptance Commitment Therapy                 |   8 (  1.5%) |   3 (  1.5%) | -0.0pp | ░░░░░░░░░░░░░░░░░░░░ |
| Marriage and Family Systems Therapy           |   8 (  1.5%) |   3 (  1.5%) | -0.0pp | ░░░░░░░░░░░░░░░░░░░░ |
| Rational Emotive Behavior Therapy             |   8 (  1.5%) |   3 (  1.5%) | -0.0pp | ░░░░░░░░░░░░░░░░░░░░ |
| Gestalt Therapy                               |   5 (  1.0%) |   2 (  1.0%) | +0.0pp | ░░░░░░░░░░░░░░░░░░░░ |
| Reality Therapy                               |   4 (  0.8%) |   2 (  1.0%) | +0.2pp | ░░░░░░░░░░░░░░░░░░░░ |
| Postmodern Therapy                            |   3 (  0.6%) |   1 (  0.5%) | -0.1pp | ░░░░░░░░░░░░░░░░░░░░ |
| Existential Therapy                           |   2 (  0.4%) |   1 (  0.5%) | +0.1pp | ░░░░░░░░░░░░░░░░░░░░ |

### Topic distribution — full vs sample

| Topic                               | Full dataset    | Sample (200)    | Deviation | Distribution |
|-------------------------------------|-----------------|-----------------|-----------|-------------|
| Ongoing Depression                  | 102 ( 19.6%) |  39 ( 19.5%) | -0.1pp | ████░░░░░░░░░░░░░░░░ |
| Partner Relationship Issues         |  96 ( 18.5%) |  39 ( 19.5%) | +1.0pp | ████░░░░░░░░░░░░░░░░ |
| Child-Parent Relationship Issues    |  96 ( 18.5%) |  36 ( 18.0%) | -0.5pp | ████░░░░░░░░░░░░░░░░ |
| Appearance Anxiety                  |  59 ( 11.3%) |  23 ( 11.5%) | +0.2pp | ██░░░░░░░░░░░░░░░░░░ |
| Academic Pressure                   |  49 (  9.4%) |  18 (  9.0%) | -0.4pp | ██░░░░░░░░░░░░░░░░░░ |
| Job Crisis                          |  37 (  7.1%) |  15 (  7.5%) | +0.4pp | ██░░░░░░░░░░░░░░░░░░ |
| Substance Abuse                     |  20 (  3.8%) |   6 (  3.0%) | -0.8pp | █░░░░░░░░░░░░░░░░░░░ |
| Unspecified                         |  19 (  3.7%) |   8 (  4.0%) | +0.3pp | █░░░░░░░░░░░░░░░░░░░ |
| School Bullying                     |  18 (  3.5%) |   7 (  3.5%) | +0.0pp | █░░░░░░░░░░░░░░░░░░░ |
| Friend Problems                     |  15 (  2.9%) |   6 (  3.0%) | +0.1pp | █░░░░░░░░░░░░░░░░░░░ |
| Sleep Problems                      |   5 (  1.0%) |   2 (  1.0%) | +0.0pp | ░░░░░░░░░░░░░░░░░░░░ |
| Procrastination                     |   4 (  0.8%) |   1 (  0.5%) | -0.3pp | ░░░░░░░░░░░░░░░░░░░░ |

### Dialog length bucket — full vs sample

| Bucket                 | Full dataset    | Sample (200)    | Deviation | Distribution |
|------------------------|-----------------|-----------------|-----------|-------------|
| Micro  (<=4 turns)     | 152 ( 29.2%) |  64 ( 32.0%) | +2.8pp | ██████░░░░░░░░░░░░░░ |
| Short  (5-10 turns)    | 183 ( 35.2%) |  72 ( 36.0%) | +0.8pp | ███████░░░░░░░░░░░░░ |
| Medium (11-20 turns)   | 114 ( 21.9%) |  42 ( 21.0%) | -0.9pp | ████░░░░░░░░░░░░░░░░ |
| Long   (>20 turns)     |  71 ( 13.7%) |  22 ( 11.0%) | -2.7pp | ██░░░░░░░░░░░░░░░░░░ |

### Turns per dialogue (sample)

| Metric | Value |
|---|---|
| Total turns across all dialogues | 2045 |
| Turns per dialogue | min=2, max=79, mean=10.2, median=7.0 |
| is_same_session = 1 | 103 (51.5%) |
| is_same_session = 0 | 97 (48.5%) |
| is_same_qa = 1 | 43 (21.5%) |

### Turn-count percentiles (sample)

| Percentile | Turns |
|-----------|-------|
| P10 | 2 |
| P25 | 4 |
| P50 (median) | 7 |
| P75 | 13 |
| P90 | 22 |

### Therapist strategy distribution (sample)

| Strategy | Count | Share (of therapist turns) |
|----------|-------|---------------------------|
| Question                                 |   660 |  63.5% |
| Reflection of Feelings                   |   147 |  14.1% |
| Others                                   |   130 |  12.5% |
| Affirmation and Reassurance              |    31 |   3.0% |
| Restatement or Paraphrasing              |    24 |   2.3% |
| Information                              |    18 |   1.7% |
| Providing Suggestions                    |     9 |   0.9% |
| Role-play                                |     9 |   0.9% |
| Self-disclosure                          |     7 |   0.7% |
| Unknown                                  |     4 |   0.4% |

### Client emotional label distribution (sample, top 15)

| Emotion | Count | Share (of client turns) |
|---------|-------|------------------------|
| Neutral                                  |   336 |  28.2% |
| Anxiety                                  |   149 |  12.5% |
| Happiness                                |   142 |  11.9% |
| Unknown                                  |   129 |  10.8% |
| Anger                                    |   101 |   8.5% |
| Others                                   |    94 |   7.9% |
| Sadness                                  |    71 |   6.0% |
| Depression                               |    56 |   4.7% |
| Fear                                     |    50 |   4.2% |
| Guilty                                   |    39 |   3.3% |
| Shame                                    |    23 |   1.9% |

---

## Reproduction

```bash
python mindeval/scripts/sample_psyinsight.py --n 200 --seed 42
```

To disable stratification (simple random sample):
```bash
python mindeval/scripts/sample_psyinsight.py --n 200 --seed 42 --no_stratified
```
