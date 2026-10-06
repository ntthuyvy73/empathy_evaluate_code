"""
Convert CACTUS raw data to a structured Mind-Eval format.

Input  : data/cactus/raw/cactus.json
Output : data/cactus/test/interactions_<N>.jsonl

Each output record has the following shape:

{
  "thought":       "<negative automatic thought>",
  "patterns":      ["<cognitive distortion>", ...],
  "client_info": {
      "name":                 "...",
      "age":                  "...",
      "gender":               "...",
      "occupation":           "...",
      "education":            "...",
      "marital_status":       "...",
      "family_details":       "...",
      "presenting_problem":   "...",
      "reason_for_counseling":"...",
      "past_history":         "...",
      "functioning":          "...",
      "social_support":       "..."
  },
  "cbt_technique": "...",
  "cbt_plan":      "...",
  "attitude":      "negative" | "neutral" | "positive",
  "dialogue": [
      {"role": "counselor", "content": "..."},
      {"role": "client",    "content": "..."},
      ...
  ]
}

Usage:
    # Simple random 10 records
    python mindeval/scripts/convert_cactus.py

    # 200 records – multi-dimensional stratified (default for --unique_client)
    python mindeval/scripts/convert_cactus.py --n 200 --unique_client --seed 42

    # Force stratified sampling explicitly
    python mindeval/scripts/convert_cactus.py --n 200 --stratified --seed 42
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Technique normalization
# ---------------------------------------------------------------------------

# Maps raw technique strings (including common typos) to canonical names.
TECH_CANONICAL: Dict[str, str] = {
    # Alternative Perspective
    "Alternative Perspective":          "Alternative Perspective",
    "Alternative perspective":          "Alternative Perspective",
    "Alternaitve Perspective":          "Alternative Perspective",
    "Alternate Perspective":            "Alternative Perspective",
    "Alternative Perspective.":         "Alternative Perspective",
    "Reframes: Alternative Perspective":"Alternative Perspective",
    # Reality Testing
    "Reality Testing":  "Reality Testing",
    "Reality testing":  "Reality Testing",
    # Behavior Experiment
    "Behavior Experiment":   "Behavior Experiment",
    "Behavioral Experiment": "Behavior Experiment",
    # Decatastrophizing
    "Decatastrophizing": "Decatastrophizing",
    # Efficiency Evaluation
    "Efficiency Evaluation": "Efficiency Evaluation",
    "Effciency Evaluation":  "Efficiency Evaluation",
    "Efficieny Evaluation":  "Efficiency Evaluation",
    # Changing Rules to Wishes
    "Changing Rules to Wishes":  "Changing Rules to Wishes",
    "Changing Rules to Wishes.": "Changing Rules to Wishes",
    "Chaging Rule to Wishes":    "Changing Rules to Wishes",
    # Problem-Solving Skills Training
    "Problem-Solving Skills Training": "Problem-Solving Skills Training",
    "Problem-solving Skills Training": "Problem-Solving Skills Training",
    # Evidence-Based Questioning
    "Evidence-Based Questioning": "Evidence-Based Questioning",
    # Pros and Cons Analysis
    "Pros and Cons Analysis": "Pros and Cons Analysis",
    # Activity Scheduling
    "Activity Scheduling": "Activity Scheduling",
    # Self-Assertiveness Training
    "Self-Assertiveness Training":              "Self-Assertiveness Training",
    "Practice of Assertive Conversation Skills":"Self-Assertiveness Training",
    # Thought Experiment
    "Thought Experiment": "Thought Experiment",
    # Continuum Technique
    "Continuum Technique": "Continuum Technique",
}

# Ordered techniques used for stratification (top-8 by unique-client count).
# Rare techniques (< 30 unique clients) are excluded from strata but still
# included in records when they appear naturally.
STRAT_TECHNIQUES: List[str] = [
    "Alternative Perspective",
    "Reality Testing",
    "Behavior Experiment",
    "Decatastrophizing",
    "Efficiency Evaluation",
    "Changing Rules to Wishes",
    "Problem-Solving Skills Training",
    "Evidence-Based Questioning",
]


def canonical_technique(raw: str) -> str:
    """Return the canonical technique name, or the raw string if unknown."""
    return TECH_CANONICAL.get(raw, raw)


# ---------------------------------------------------------------------------
# intake_form parser
# ---------------------------------------------------------------------------

# Fields that appear as "Label:\n<value on next line>"
_NEWLINE_FIELDS = {"Name", "Age", "Gender"}

# Fields that appear as "Label: <value on same line>"
_INLINE_FIELDS = {
    "Occupation",
    "Education",
    "Marital Status",
    "Family Details",
}

# Section headers (numbered sections in the intake form).
# The regex only anchors on the section number so it works regardless of the
# exact wording that follows (which varies slightly across records).
_SECTIONS = [
    (r"^2\.\s+", "presenting_problem"),
    (r"^3\.\s+", "reason_for_counseling"),
    (r"^4\.\s+", "past_history"),
    (r"^5\.\s+", "functioning"),
    (r"^6\.\s+", "social_support"),
]


def _normalise(text: str) -> str:
    """Collapse internal whitespace into single spaces."""
    return " ".join(text.split())


def parse_intake_form(raw: str) -> Dict[str, str]:
    """
    Parse a CACTUS intake_form string into a flat dict.

    Returns keys: name, age, gender, occupation, education, marital_status,
                  family_details, presenting_problem, reason_for_counseling,
                  past_history, functioning, social_support.
    Missing keys are set to "Unknown".
    """
    result: Dict[str, str] = {}
    lines = raw.strip().split("\n")
    n = len(lines)
    i = 0

    # --- Phase 1: parse demographic header lines ---
    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()

        # Check if we've hit a numbered section
        if re.match(r"^\d+\.", stripped):
            break

        # Pattern 1: Label on its own line, value on the next line
        if stripped.rstrip(":") in _NEWLINE_FIELDS and stripped.endswith(":"):
            key = stripped.rstrip(":").lower()
            if i + 1 < n:
                result[key] = lines[i + 1].strip()
                i += 2
            else:
                i += 1
            continue

        # Pattern 2: "Label: value" on the same line
        matched_inline = False
        for field in _INLINE_FIELDS:
            if stripped.startswith(field + ":"):
                key = field.lower().replace(" ", "_")
                result[key] = stripped[len(field) + 1:].strip()
                matched_inline = True
                break
        if matched_inline:
            i += 1
            continue

        i += 1

    # --- Phase 2: parse numbered sections ---
    current_key: Optional[str] = None
    current_lines: List[str] = []

    def _flush():
        if current_key and current_lines:
            result[current_key] = _normalise(" ".join(current_lines))

    for j in range(i, n):
        line = lines[j].strip()

        # Detect a new section header
        new_key = None
        for pattern, key in _SECTIONS:
            if re.match(pattern, line):
                new_key = key
                break

        if new_key is not None:
            _flush()
            current_key = new_key
            # The header line itself may carry inline content after the colon
            # e.g. "5. Academic/occupational functioning level: My job..."
            if ":" in line:
                after_colon = line.split(":", 1)[1].strip()
                current_lines = [after_colon] if after_colon else []
            else:
                current_lines = []
            continue

        if current_key is not None and line:
            current_lines.append(line)

    _flush()

    # Fill missing keys with "Unknown"
    for key in (
        "name", "age", "gender", "occupation", "education",
        "marital_status", "family_details",
        "presenting_problem", "reason_for_counseling",
        "past_history", "functioning", "social_support",
    ):
        result.setdefault(key, "Unknown")

    return result


# ---------------------------------------------------------------------------
# Dialogue parser
# ---------------------------------------------------------------------------

def parse_dialogue(raw: str) -> List[Dict[str, str]]:
    """
    Convert a CACTUS dialogue string into a list of turn dicts.

    Each turn starts with 'Counselor: ' or 'Client: '.
    A turn may span multiple lines (continuation lines have no role prefix).

    Returns:
        List of {"role": "counselor"|"client", "content": "<text>"}
    """
    turns: List[Dict[str, str]] = []
    current_role: Optional[str] = None
    current_lines: List[str] = []

    for line in raw.splitlines():
        if line.startswith("Counselor: "):
            if current_role is not None:
                content = _normalise(" ".join(current_lines))
                if content:
                    turns.append({"role": current_role, "content": content})
            current_role = "counselor"
            current_lines = [line[len("Counselor: "):]]

        elif line.startswith("Client: "):
            if current_role is not None:
                content = _normalise(" ".join(current_lines))
                if content:
                    turns.append({"role": current_role, "content": content})
            current_role = "client"
            current_lines = [line[len("Client: "):]]

        else:
            # Continuation of the current turn
            current_lines.append(line)

    # Flush last turn
    if current_role is not None:
        content = _normalise(" ".join(current_lines))
        if content:
            turns.append({"role": current_role, "content": content})

    return turns


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert one raw CACTUS item into the target structured format.

    Returns None if the item is missing required fields.
    """
    # Required fields
    for field in ("thought", "dialogue"):
        if not item.get(field):
            return None

    dialogue = parse_dialogue(item["dialogue"])
    if not dialogue:
        return None

    client_info = parse_intake_form(item.get("intake_form", ""))

    return {
        "thought":       item["thought"],
        "patterns":      item.get("patterns", []),
        "client_info":   client_info,
        "cbt_technique": canonical_technique(item.get("cbt_technique", "Unknown")),
        "cbt_plan":      item.get("cbt_plan", ""),
        "attitude":      item.get("attitude", "Unknown"),
        "dialogue":      dialogue,
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------

def _client_key(item: Dict[str, Any]) -> str:
    """Stable deduplication key: full intake_form text (falls back to thought)."""
    return item.get("intake_form") or item.get("thought", "")


def deduplicate_by_client(
    data: List[Dict[str, Any]],
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Group raw records by client identity and keep exactly one record per
    unique client (chosen randomly within each group).
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in data:
        key = _client_key(item)
        groups.setdefault(key, []).append(item)

    representatives = [rng.choice(group) for group in groups.values()]
    rng.shuffle(representatives)
    return representatives


def _compute_quotas(weights: Dict[str, int], total: int) -> Dict[str, int]:
    """
    Proportional allocation using the largest-remainder (Hamilton) method.

    weights : dict of {key: weight}  (counts or any positive integers)
    total   : desired total to distribute
    Returns dict of {key: integer_quota} that sums exactly to total.
    """
    grand = sum(weights.values())
    if grand == 0:
        return {k: 0 for k in weights}

    exact  = {k: total * v / grand for k, v in weights.items()}
    floors = {k: int(v) for k, v in exact.items()}
    deficit = total - sum(floors.values())

    by_rem = sorted(weights.keys(), key=lambda k: exact[k] - floors[k], reverse=True)
    for i in range(deficit):
        floors[by_rem[i % len(by_rem)]] += 1

    return floors


def multidim_stratified_sample(
    data: List[Dict[str, Any]],
    n: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Sample n records with balanced distribution across four dimensions:

    1. Attitude   – equal thirds (~n/3 each: negative, neutral, positive).
    2. CBT Tech   – proportional to client availability for STRAT_TECHNIQUES.
    3. Gender     – interleaved male/female within each (technique, attitude)
                    cell; age is varied within each gender bucket.
    4. Unique     – each record comes from a different client (intake_form).

    ~98.7% of CACTUS clients have all three attitudes available, so the equal
    attitude split is achieved without overlap between attitude groups.

    Algorithm
    ---------
    a) Build a nested lookup:
       {intake_form: {canonical_tech: {attitude: [raw items]}}}
    b) Compute per-attitude technique quotas via largest-remainder.
    c) Sort cells from smallest to largest quota so rare (technique, attitude)
       cells get first pick of the candidate pool.
    d) For each cell, collect eligible (not yet used) clients, interleave
       male/female candidates (sorted by age within each gender for diversity),
       and pick the first `quota` clients.
    e) For each picked client, choose one raw item at random, build a record.
    """
    # ── Step a: build client lookup ──────────────────────────────────────────
    # {form: {tech: {att: [raw_items]}}}
    client_data: Dict[str, Dict[str, Dict[str, List]]] = {}

    for item in data:
        form = _client_key(item)
        att  = item.get("attitude", "Unknown")
        tech = canonical_technique(item.get("cbt_technique", "Unknown"))
        if tech not in STRAT_TECHNIQUES:
            continue
        if form not in client_data:
            client_data[form] = {}
        if tech not in client_data[form]:
            client_data[form][tech] = {}
        client_data[form][tech].setdefault(att, []).append(item)

    # ── Step b: compute quotas ───────────────────────────────────────────────
    # Count unique clients that have each strat technique available
    tech_clients: Dict[str, int] = Counter(
        tech
        for fd in client_data.values()
        for tech in fd
    )

    # Attitude quotas: equal thirds
    n_neg = n // 3
    n_neu = n // 3
    n_pos = n - n_neg - n_neu   # gets the remainder when n % 3 != 0

    att_tech_quotas: Dict[str, Dict[str, int]] = {
        att: _compute_quotas(
            {t: tech_clients.get(t, 0) for t in STRAT_TECHNIQUES},
            quota,
        )
        for att, quota in [("negative", n_neg), ("neutral", n_neu), ("positive", n_pos)]
    }

    # ── Step c: build cells ordered rare-first ───────────────────────────────
    cells: List[tuple] = []
    for att, tq in att_tech_quotas.items():
        for tech, quota in tq.items():
            if quota > 0:
                cells.append((quota, att, tech))
    cells.sort(key=lambda x: x[0])   # rarest cells first → fills guaranteed

    # ── Steps d–e: fill cells ────────────────────────────────────────────────
    used_clients: set = set()
    result_records: List[Dict[str, Any]] = []

    for quota, att, tech in cells:
        # Eligible clients: have this (tech, att) and not already picked
        eligible_meta = []
        for form, fd in client_data.items():
            if tech in fd and att in fd[tech] and form not in used_clients:
                items_list = fd[tech][att]
                ci = parse_intake_form(items_list[0].get("intake_form", ""))
                gender = ci.get("gender", "").lower()
                try:
                    age = int(ci.get("age", 35))
                except (ValueError, TypeError):
                    age = 35
                eligible_meta.append((form, gender, age))

        if not eligible_meta:
            print(f"  Warning: no candidates for cell ({tech!r}, {att!r}).")
            continue

        # Shuffle first (preserves random age distribution), then separate by gender
        rng.shuffle(eligible_meta)
        males   = [x for x in eligible_meta if x[1] == "male"]
        females = [x for x in eligible_meta if x[1] == "female"]
        others  = [x for x in eligible_meta if x[1] not in ("male", "female")]

        # Interleave male / female for gender balance (age stays random from shuffle)
        interleaved: List[tuple] = []
        mi = fi = 0
        while mi < len(males) or fi < len(females):
            if mi < len(males) and (fi >= len(females) or mi <= fi):
                interleaved.append(males[mi]);   mi += 1
            else:
                interleaved.append(females[fi]); fi += 1
        interleaved.extend(others)

        picked = interleaved[:quota]
        if len(picked) < quota:
            print(
                f"  Warning: cell ({tech!r}, {att!r}): "
                f"need {quota}, only {len(picked)} available."
            )

        for form, gender, age in picked:
            used_clients.add(form)
            item = rng.choice(client_data[form][tech][att])
            rec  = build_record(item)
            if rec:
                result_records.append(rec)

    rng.shuffle(result_records)
    return result_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert CACTUS raw data to structured Mind-Eval JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input_path",
        default="data/cactus/raw/cactus.json",
        help="Path to cactus.json (default: data/cactus/raw/cactus.json).",
    )
    parser.add_argument(
        "--output_path",
        default=None,
        help=(
            "Output JSONL file. "
            "Auto-named data/cactus/test/interactions_<N>[_unique].jsonl "
            "unless overridden."
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of records to sample (default: 10). Use 0 for all records.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42).",
    )
    parser.add_argument(
        "--unique_client",
        action="store_true",
        default=False,
        help=(
            "Ensure every output record belongs to a different client. "
            "When used together with --stratified (the default for this flag), "
            "applies multi-dimensional stratified sampling."
        ),
    )
    parser.add_argument(
        "--stratified",
        action="store_true",
        default=False,
        help=(
            "Apply multi-dimensional stratified sampling: balanced attitude "
            "(neg/neu/pos), proportional CBT technique, gender-interleaved "
            "within each cell. Implies --unique_client."
        ),
    )
    args = parser.parse_args()

    # --stratified implies --unique_client
    if args.stratified:
        args.unique_client = True

    input_path = Path(args.input_path)
    n = args.n
    rng = random.Random(args.seed)

    # Determine default output path
    if args.output_path:
        output_path = Path(args.output_path)
    elif args.unique_client:
        label = n if n > 0 else "all"
        output_path = Path(f"data/cactus/test/interactions_{label}_unique.jsonl")
    else:
        label = n if n > 0 else "all"
        output_path = Path(f"data/cactus/test/interactions_{label}.jsonl")

    # Load raw data
    print(f"Loading {input_path} ...")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data)} raw records loaded.")

    # ── Sampling path ────────────────────────────────────────────────────────
    if args.stratified and n > 0:
        print(
            f"  Multi-dimensional stratified sampling: n={n}, seed={args.seed}\n"
            f"  Strata: attitude (equal thirds) x technique (proportional) x gender"
        )
        records = multidim_stratified_sample(data, n, rng)
        print(f"  Sampled {len(records)} records.")

    else:
        # Simple path: optionally deduplicate, then random sample
        if args.unique_client:
            data = deduplicate_by_client(data, rng)
            print(f"  After deduplication: {len(data)} unique clients.")

        if n > 0 and n < len(data):
            data = rng.sample(data, n)
            print(f"  Sampled {len(data)} records (seed={args.seed}).")
        else:
            print(f"  Using all {len(data)} records.")

        records = []
        skipped = 0
        for item in data:
            rec = build_record(item)
            if rec is None:
                skipped += 1
            else:
                records.append(rec)
        print(f"  Converted: {len(records)}  Skipped (missing fields): {skipped}")

    # Save
    save_jsonl(records, output_path)
    print(f"Saved {len(records)} records -> {output_path}")


if __name__ == "__main__":
    main()
