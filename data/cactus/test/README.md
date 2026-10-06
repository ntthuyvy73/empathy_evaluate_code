# CACTUS Test Dataset

## Overview

| Item | Value |
|---|---|
| Source file | `data/cactus/raw/cactus.json` |
| Conversion script | `mindeval/scripts/convert_cactus.py` |
| Total raw records | 31,577 |
| Unique clients (deduplicated) | 4,057 |
| **Sample file** | `interactions_200_unique.jsonl` |
| **Sample size** | **200** |
| Sampling method | Multi-dimensional stratified (attitude × technique × gender) |
| Random seed | 42 |

---

## How Sampling Was Done

1. **Load** all 31,577 raw records from `cactus.json`.
2. **Build client index** `{intake_form → {technique → {attitude → [records]}}}`
   (4,057 unique clients; 98.7% have all three attitudes available).
3. **Attitude quotas** — equal thirds: 67 negative + 67 neutral + 66 positive = **200**.
4. **Technique quotas** — within each attitude group, proportional to client
   availability for the **8 canonical techniques** (largest-remainder method).
5. **Cell filling** — for each (technique, attitude) cell, eligible (not-yet-used)
   clients are randomly shuffled then interleaved male/female for gender balance.
   Rare cells are filled first to guarantee coverage of every technique.
6. **Record selection** — for each picked (client, technique, attitude) triple,
   one raw record is chosen at random.
7. Result: **200 unique clients**, balanced across attitude, technique and gender.

> All statistics below are computed directly from the 200 sampled records.

---

## Record Format

```json
{
  "thought":       "<negative automatic thought>",
  "patterns":      ["<cognitive distortion>", ...],
  "client_info": {
      "name":                  "...",
      "age":                   "...",
      "gender":                "...",
      "occupation":            "...",
      "education":             "...",
      "marital_status":        "...",
      "family_details":        "...",
      "presenting_problem":    "...",
      "reason_for_counseling": "...",
      "past_history":          "...",
      "functioning":           "...",
      "social_support":        "..."
  },
  "cbt_technique": "...",
  "cbt_plan":      "...",
  "attitude":      "negative | neutral | positive",
  "dialogue": [
      {"role": "counselor", "content": "..."},
      {"role": "client",    "content": "..."}
  ]
}
```

---

## Client Demographics (sample)

### Unique clients
| Metric | Value |
|---|---|
| Total records | 200 |
| Unique names | 199 |
| Records with numeric age | 200 |
| Age range (numeric) | 10 – 79 |
| Mean age | 34.6 |
| Median age | 33.0 |

### Gender distribution

| Gender | Count | Share | Distribution |
|--------|-------|-------|-------------|
| male         |   106 |  53.0% | ███████████░░░░░░░░░ |
| female       |    94 |  47.0% | █████████░░░░░░░░░░░ |

### Age-group distribution

| Age Group           | Count | Share | Distribution |
|---------------------|-------|-------|-------------|
| Adult (25-44)        |    99 |  49.5% | ██████████░░░░░░░░░░ |
| Young (<25)          |    55 |  27.5% | ██████░░░░░░░░░░░░░░ |
| Middle (45-64)       |    37 |  18.5% | ████░░░░░░░░░░░░░░░░ |
| Senior (65+)         |     9 |   4.5% | █░░░░░░░░░░░░░░░░░░░ |

---

## Dialogue Statistics

| Metric | Value |
|---|---|
| Total turns across all dialogues | 6103 |
| Turns per dialogue — min=24, max=35, mean=30.5, median=31.0 | |
| Counselor turns per dialogue — min=12, max=18, mean=15.6, median=16.0 | |
| Client turns per dialogue — min=12, max=17, mean=15.0, median=15.0 | |

---

## Attitude Distribution

| Attitude | Count | Share | Distribution |
|----------|-------|-------|-------------|
| positive   |    68 |  34.0% | ███████░░░░░░░░░░░░░ |
| neutral    |    66 |  33.0% | ███████░░░░░░░░░░░░░ |
| negative   |    66 |  33.0% | ███████░░░░░░░░░░░░░ |

### Attitude × Top-3 CBT Technique

| Attitude | Count | Share | Top-3 Techniques (count) |
|----------|-------|-------|--------------------------|
| negative |    66 |  33.0% | Alternative Perspective (19) / Reality Testing (17) / Behavior Experiment (10) |
| neutral  |    66 |  33.0% | Alternative Perspective (19) / Reality Testing (17) / Behavior Experiment (10) |
| positive |    68 |  34.0% | Alternative Perspective (20) / Reality Testing (17) / Behavior Experiment (11) |

---

## CBT Technique Distribution

| Technique | Count | Share | Gender (M/F) | Distribution |
|-----------|-------|-------|--------------|-------------|
| Alternative Perspective                       |    58 |  29.0% |  30M /  28F | ██████░░░░░░░░░░░░░░ |
| Reality Testing                               |    51 |  25.5% |  27M /  24F | █████░░░░░░░░░░░░░░░ |
| Behavior Experiment                           |    31 |  15.5% |  16M /  15F | ███░░░░░░░░░░░░░░░░░ |
| Decatastrophizing                             |    30 |  15.0% |  15M /  15F | ███░░░░░░░░░░░░░░░░░ |
| Efficiency Evaluation                         |    12 |   6.0% |   6M /   6F | █░░░░░░░░░░░░░░░░░░░ |
| Changing Rules to Wishes                      |     9 |   4.5% |   6M /   3F | █░░░░░░░░░░░░░░░░░░░ |
| Problem-Solving Skills Training               |     6 |   3.0% |   3M /   3F | █░░░░░░░░░░░░░░░░░░░ |
| Evidence-Based Questioning                    |     3 |   1.5% |   3M /   0F | ░░░░░░░░░░░░░░░░░░░░ |

### Attitude × Technique (full cross-tab — strat techniques)

| Attitude   | Technique                                     | Count |
|------------|-----------------------------------------------|-------|
| negative   | Alternative Perspective                       |    19 |
| negative   | Reality Testing                               |    17 |
| negative   | Behavior Experiment                           |    10 |
| negative   | Decatastrophizing                             |    10 |
| negative   | Efficiency Evaluation                         |     4 |
| negative   | Changing Rules to Wishes                      |     3 |
| negative   | Problem-Solving Skills Training               |     2 |
| negative   | Evidence-Based Questioning                    |     1 |
|            | (other)                                       |     0 |
| | | |
| neutral    | Alternative Perspective                       |    19 |
| neutral    | Reality Testing                               |    17 |
| neutral    | Behavior Experiment                           |    10 |
| neutral    | Decatastrophizing                             |    10 |
| neutral    | Efficiency Evaluation                         |     4 |
| neutral    | Changing Rules to Wishes                      |     3 |
| neutral    | Problem-Solving Skills Training               |     2 |
| neutral    | Evidence-Based Questioning                    |     1 |
|            | (other)                                       |     0 |
| | | |
| positive   | Alternative Perspective                       |    20 |
| positive   | Reality Testing                               |    17 |
| positive   | Behavior Experiment                           |    11 |
| positive   | Decatastrophizing                             |    10 |
| positive   | Efficiency Evaluation                         |     4 |
| positive   | Changing Rules to Wishes                      |     3 |
| positive   | Problem-Solving Skills Training               |     2 |
| positive   | Evidence-Based Questioning                    |     1 |
|            | (other)                                       |     0 |
| | | |

---

## Cognitive Distortion Patterns (top 15)

Each record can have multiple patterns.  Total pattern occurrences: **754**
across 200 records (avg 3.8 patterns/record).

| Pattern | Count | Share (of records) | Distribution |
|---------|-------|--------------------|-------------|
| overgeneralization                            |   114 |  57.0% | ███████████░░░░░░░░░ |
| jumping to conclusions: fortune-telling       |    87 |  43.5% | █████████░░░░░░░░░░░ |
| labeling and mislabeling                      |    86 |  43.0% | █████████░░░░░░░░░░░ |
| catastrophizing                               |    84 |  42.0% | ████████░░░░░░░░░░░░ |
| mental filtering                              |    83 |  41.5% | ████████░░░░░░░░░░░░ |
| personalization                               |    80 |  40.0% | ████████░░░░░░░░░░░░ |
| black-and-white or polarized thinking / all or nothing thinking |    77 |  38.5% | ████████░░░░░░░░░░░░ |
| discounting the positive                      |    65 |  32.5% | ██████░░░░░░░░░░░░░░ |
| jumping to conclusions: mind reading          |    48 |  24.0% | █████░░░░░░░░░░░░░░░ |
| should statements                             |    17 |   8.5% | ██░░░░░░░░░░░░░░░░░░ |
| none                                          |    13 |   6.5% | █░░░░░░░░░░░░░░░░░░░ |

---

## Reproduction

```bash
python mindeval/scripts/convert_cactus.py --n 200 --stratified --seed 42
```
