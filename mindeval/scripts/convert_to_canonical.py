"""
Convert all 6 datasets to the canonical Mind-Eval schema.

Output per dataset: data/<dataset>/test/interactions_200_canonical.jsonl

Canonical schema
----------------
{
  "interaction_id": "<source>_<original_id>",
  "interaction": [
    {"role": "client",    "content": "..."},
    {"role": "counselor", "content": "..."}
  ],
  "metadata": {
    "source":       "<dataset name>",
    "language":     "en | zh | ko",
    "turn_count":   <int>,
    "origin_type":  "human | simulated",
    "original_id":  "<str>",
    "length_bucket":"short | medium | long | very_long"
  },
  "extra": { ... dataset-specific annotations, never sent to judge ... }
}

Role mapping
------------
  Psy-Insight : Supporter -> counselor  |  Seeker -> client
  cactus      : counselor (ok)          |  client (ok)
  simpsydial  : counselor (ok)          |  client (ok)
  PsyDial     : assistant -> counselor  |  user   -> client
  SoulChat    : assistant -> counselor  |  user   -> client
  KMI         : Therapist -> counselor  |  Client -> client

Length buckets (by turn_count)
-------------------------------
  short     :  <= 10
  medium    :  <= 30
  long      :  <= 70
  very_long :   > 70

Usage
-----
    # Convert all datasets (default)
    python mindeval/scripts/convert_to_canonical.py

    # Convert specific dataset(s)
    python mindeval/scripts/convert_to_canonical.py --datasets cactus psy_insight

    # Dry-run (print stats without writing)
    python mindeval/scripts/convert_to_canonical.py --dry_run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
from typing import Any

# Sentinel used by kmi_ko to signal it needs two source paths
_KMI_KO_SENTINEL = "__kmi_ko__"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIENT_ROLES = {"client", "user", "Seeker", "Client", "seeker"}
_COUNSELOR_ROLES = {"counselor", "assistant", "Supporter", "Therapist", "supporter"}


def _map_role(raw: str) -> str:
    if raw in _CLIENT_ROLES:
        return "client"
    if raw in _COUNSELOR_ROLES:
        return "counselor"
    raise ValueError(f"Unknown role: {raw!r}")


def _length_bucket(turn_count: int) -> str:
    if turn_count <= 10:
        return "short"
    if turn_count <= 30:
        return "medium"
    if turn_count <= 70:
        return "long"
    return "very_long"


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _save_jsonl(records: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Per-dataset converters
# ---------------------------------------------------------------------------

def _convert_psy_insight(src: pathlib.Path) -> list[dict]:
    """
    Source: data/Psy-Insight/test/interactions_200.jsonl
    Dialog key : "dialog"  (list of speaker-dicts)
    Speaker    : "Supporter" | "Seeker"
    Extra      : psychotherapy_type, topic, background, theme, summary,
                 emotional_label (collected across turns), strategy (collected)
    Origin     : human
    """
    records = []
    for idx, raw in enumerate(_load_jsonl(src)):
        dialog_id = str(raw.get("dialog_id", idx))

        turns = []
        all_emotional_labels: list[str] = []
        all_strategies: list[str] = []

        for turn in raw.get("dialog", []):
            role = _map_role(turn["speaker"])
            turns.append({"role": role, "content": turn["content"]})
            # Collect utterance-level annotations into extra
            for lbl in turn.get("emotional label", []):
                if lbl and lbl not in all_emotional_labels:
                    all_emotional_labels.append(lbl)
            for strat in turn.get("strategy", []):
                if strat and strat not in all_strategies:
                    all_strategies.append(strat)

        turn_count = len(turns)

        extra: dict[str, Any] = {}
        if raw.get("psychotherapy"):
            extra["psychotherapy_type"] = raw["psychotherapy"]
        if raw.get("topic"):
            extra["topic"] = raw["topic"]
        if raw.get("background"):
            extra["background"] = raw["background"]
        if raw.get("theme"):
            extra["theme"] = raw["theme"]
        if raw.get("summary"):
            extra["summary"] = raw["summary"]
        if all_emotional_labels:
            extra["emotional_label"] = all_emotional_labels
        if all_strategies:
            extra["strategy"] = all_strategies

        records.append({
            "interaction_id": f"psyinsight_{dialog_id}",
            "interaction": turns,
            "metadata": {
                "source": "Psy-Insight",
                "language": "en",
                "turn_count": turn_count,
                "origin_type": "human",
                "original_id": dialog_id,
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


def _convert_cactus(src: pathlib.Path) -> list[dict]:
    """
    Source: data/cactus/test/interactions_200_unique.jsonl
    Dialog key : "dialogue"
    Speaker    : "counselor" | "client"  (already canonical)
    Extra      : thought, cbt_patterns, client_info, cbt_technique, cbt_plan, attitude
    Origin     : simulated
    """
    records = []
    for idx, raw in enumerate(_load_jsonl(src)):
        turns = [
            {"role": _map_role(t["role"]), "content": t["content"]}
            for t in raw.get("dialogue", [])
        ]
        turn_count = len(turns)

        extra: dict[str, Any] = {}
        if raw.get("thought"):
            extra["thought"] = raw["thought"]
        if raw.get("patterns"):
            extra["cbt_patterns"] = raw["patterns"]
        if raw.get("client_info"):
            extra["client_info"] = raw["client_info"]
        if raw.get("cbt_technique"):
            extra["cbt_technique"] = raw["cbt_technique"]
        if raw.get("cbt_plan"):
            extra["cbt_plan"] = raw["cbt_plan"]
        if raw.get("attitude"):
            extra["attitude"] = raw["attitude"]

        records.append({
            "interaction_id": f"cactus_{idx}",
            "interaction": turns,
            "metadata": {
                "source": "cactus",
                "language": "en",
                "turn_count": turn_count,
                "origin_type": "simulated",
                "original_id": str(idx),
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


def _convert_simpsydial(src: pathlib.Path) -> list[dict]:
    """
    Source: data/simpsydial/test/interactions_200.jsonl
    Dialog key : "dialogue"
    Speaker    : "client" | "counselor"  (already canonical)
    Extra      : (none)
    Origin     : simulated
    """
    records = []
    for idx, raw in enumerate(_load_jsonl(src)):
        meta = raw.get("metadata", {})
        turns = [
            {"role": _map_role(t["role"]), "content": t["content"]}
            for t in raw.get("dialogue", [])
        ]
        turn_count = meta.get("turn_count", len(turns))
        original_id = meta.get("original_file", str(idx))
        # Strip ".json" suffix if present
        if original_id.endswith(".json"):
            original_id = original_id[:-5]

        records.append({
            "interaction_id": f"simpsydial_{original_id}",
            "interaction": turns,
            "metadata": {
                "source": "simpsydial",
                "language": meta.get("language", "zh"),
                "turn_count": turn_count,
                "origin_type": "simulated",
                "original_id": original_id,
                "length_bucket": meta.get("length_bucket", _length_bucket(turn_count)),
            },
            "extra": {},
        })
    return records


def _convert_psydial(src: pathlib.Path) -> list[dict]:
    """
    Source: data/PsyDial/test/interactions_200.jsonl
    Dialog key : "dialogue"
    Speaker    : "user" -> client | "assistant" -> counselor
    Extra      : (none)
    Origin     : simulated
    """
    records = []
    for idx, raw in enumerate(_load_jsonl(src)):
        meta = raw.get("metadata", {})
        turns = [
            {"role": _map_role(t["role"]), "content": t["content"]}
            for t in raw.get("dialogue", [])
        ]
        turn_count = meta.get("turn_count", len(turns))
        original_id = str(meta.get("original_index", idx))

        records.append({
            "interaction_id": f"psydial_{original_id}",
            "interaction": turns,
            "metadata": {
                "source": "PsyDial",
                "language": meta.get("language", "zh"),
                "turn_count": turn_count,
                "origin_type": "simulated",
                "original_id": original_id,
                "length_bucket": meta.get("length_bucket", _length_bucket(turn_count)),
            },
            "extra": {},
        })
    return records


def _convert_soulchat(src: pathlib.Path) -> list[dict]:
    """
    Source: data/SoulChat/test/interactions_200.jsonl
    Dialog key : "dialogue"
    Speaker    : "user" -> client | "assistant" -> counselor
    Extra      : topic
    Origin     : simulated  (GPT-generated empathetic responses)
    """
    records = []
    for raw in _load_jsonl(src):
        meta = raw.get("metadata", {})
        turns = [
            {"role": _map_role(t["role"]), "content": t["content"]}
            for t in raw.get("dialogue", [])
        ]
        turn_count = meta.get("turn_count", len(turns))
        original_id = str(raw.get("id", ""))

        extra: dict[str, Any] = {}
        if raw.get("topic"):
            extra["topic"] = raw["topic"]

        records.append({
            "interaction_id": f"soulchat_{original_id}",
            "interaction": turns,
            "metadata": {
                "source": "SoulChat",
                "language": meta.get("language", "zh"),
                "turn_count": turn_count,
                "origin_type": "simulated",
                "original_id": original_id,
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


def _convert_kmi(src: pathlib.Path) -> list[dict]:
    """
    Source: data/KMI/test/interactions_200.jsonl  (already uses utterance_en)
    Dialog key : "dialogue" with content = utterance_en
    Speaker    : "Therapist" -> counselor | "Client" -> client
    Extra      : category (from category_en), mi_label (per-turn labels collected)
    Origin     : human
    Language   : "en"
    """
    records = []
    for raw in _load_jsonl(src):
        original_id = str(raw.get("id", ""))
        turns = []
        mi_labels: list[str] = []

        for turn in raw.get("dialogue", []):
            role = _map_role(turn["role"])
            turns.append({"role": role, "content": turn["content"]})
            lbl = turn.get("label")
            if lbl:
                mi_labels.append(lbl)

        turn_count = len(turns)

        extra: dict[str, Any] = {}
        if raw.get("category_en"):
            extra["category"] = raw["category_en"]
        if mi_labels:
            extra["mi_label"] = mi_labels

        records.append({
            "interaction_id": f"kmi_{original_id}",
            "interaction": turns,
            "metadata": {
                "source": "KMI",
                "language": "en",  # test file already uses utterance_en
                "turn_count": turn_count,
                "origin_type": "human",
                "original_id": original_id,
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


def _convert_kmi_ko(en_src: pathlib.Path, raw_src: pathlib.Path) -> list[dict]:
    """
    Build KMI canonical using Korean utterances (utterance_ko) from raw data.

    Uses the same 200 interaction IDs already sampled in interactions_200.jsonl,
    but replaces 'content' with utterance_ko for each turn.

    Source    : data/KMI/raw/kmi.json
    ID list   : data/KMI/test/interactions_200.jsonl  (EN version, for IDs only)
    Language  : "ko"
    """
    # Load raw lookup by id
    with open(raw_src, encoding="utf-8") as f:
        raw_list = json.load(f)
    raw_by_id: dict[int, dict] = {r["id"]: r for r in raw_list}

    # Load EN test file for the ordered ID list and extra metadata
    en_records = _load_jsonl(en_src)

    records = []
    for en_rec in en_records:
        original_id_str = str(en_rec.get("id", ""))
        original_id_int = en_rec.get("id")
        raw = raw_by_id.get(original_id_int)
        if raw is None:
            print(f"  [warn] KMI id={original_id_str} not found in raw — skipping")
            continue

        turns = []
        mi_labels: list[str] = []

        for turn in raw.get("dialogue", []):
            role = _map_role(turn["role"])
            ko_content = turn.get("utterance_ko", "").strip()
            if not ko_content:
                continue
            turns.append({"role": role, "content": ko_content})
            lbl = turn.get("label")
            if lbl:
                mi_labels.append(lbl)

        if not turns:
            continue

        turn_count = len(turns)

        extra: dict[str, Any] = {}
        if raw.get("category_en"):
            extra["category"] = raw["category_en"]
        if raw.get("category_ko"):
            extra["category_ko"] = raw["category_ko"]
        if mi_labels:
            extra["mi_label"] = mi_labels

        records.append({
            "interaction_id": f"kmi_{original_id_str}",
            "interaction": turns,
            "metadata": {
                "source": "KMI",
                "language": "ko",
                "turn_count": turn_count,
                "origin_type": "human",
                "original_id": original_id_str,
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


def _convert_esconv(src: pathlib.Path, n: int = 200, seed: int = 42) -> list[dict]:
    """
    Source: data/ESConv/raw/ESConv.json  (list of 1300 dialogues)
    Dialog key : "dialog"
    Speaker    : "seeker" -> client | "supporter" -> counselor
    Extra      : emotion_type, problem_type, situation, experience_type,
                 strategies (collected across turns), survey_score
    Origin     : human  (crowdsourced via MTurk)
    Language   : en
    Sampling   : random {n} records, fixed seed for reproducibility
    """
    with open(src, encoding="utf-8") as f:
        all_records = json.load(f)

    rng = random.Random(seed)
    sampled = rng.sample(all_records, min(n, len(all_records)))

    records = []
    for idx, raw in enumerate(sampled):
        original_id = str(idx)

        turns = []
        strategies: list[str] = []

        for turn in raw.get("dialog", []):
            role = _map_role(turn["speaker"])
            content = turn["content"].strip()
            if not content:
                continue
            turns.append({"role": role, "content": content})
            strat = turn.get("annotation", {}).get("strategy")
            if strat and strat not in strategies:
                strategies.append(strat)

        turn_count = len(turns)

        extra: dict[str, Any] = {}
        if raw.get("emotion_type"):
            extra["emotion_type"] = raw["emotion_type"]
        if raw.get("problem_type"):
            extra["problem_type"] = raw["problem_type"]
        if raw.get("situation"):
            extra["situation"] = raw["situation"]
        if raw.get("experience_type"):
            extra["experience_type"] = raw["experience_type"]
        if strategies:
            extra["strategies"] = strategies
        if raw.get("survey_score"):
            extra["survey_score"] = raw["survey_score"]

        records.append({
            "interaction_id": f"esconv_{original_id}",
            "interaction": turns,
            "metadata": {
                "source": "ESConv",
                "language": "en",
                "turn_count": turn_count,
                "origin_type": "human",
                "original_id": original_id,
                "length_bucket": _length_bucket(turn_count),
            },
            "extra": extra,
        })
    return records


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DATASET_CONFIGS: dict[str, dict] = {
    "psy_insight": {
        "display": "Psy-Insight",
        "src": pathlib.Path("data/Psy-Insight/test/interactions_200.jsonl"),
        "dst": pathlib.Path("data/Psy-Insight/test/interactions_200_canonical.jsonl"),
        "converter": _convert_psy_insight,
    },
    "cactus": {
        "display": "cactus",
        "src": pathlib.Path("data/cactus/test/interactions_200_unique.jsonl"),
        "dst": pathlib.Path("data/cactus/test/interactions_200_canonical.jsonl"),
        "converter": _convert_cactus,
    },
    "simpsydial": {
        "display": "simpsydial",
        "src": pathlib.Path("data/simpsydial/test/interactions_200.jsonl"),
        "dst": pathlib.Path("data/simpsydial/test/interactions_200_canonical.jsonl"),
        "converter": _convert_simpsydial,
    },
    "psydial": {
        "display": "PsyDial",
        "src": pathlib.Path("data/PsyDial/test/interactions_200.jsonl"),
        "dst": pathlib.Path("data/PsyDial/test/interactions_200_canonical.jsonl"),
        "converter": _convert_psydial,
    },
    "soulchat": {
        "display": "SoulChat",
        "src": pathlib.Path("data/SoulChat/test/interactions_200.jsonl"),
        "dst": pathlib.Path("data/SoulChat/test/interactions_200_canonical.jsonl"),
        "converter": _convert_soulchat,
    },
    "kmi": {
        "display": "KMI (EN)",
        "src": pathlib.Path("data/KMI/test/interactions_200.jsonl"),
        "dst": pathlib.Path("data/KMI/test/interactions_200_canonical.jsonl"),
        "converter": _convert_kmi,
    },
    "kmi_ko": {
        "display": "KMI (KO)",
        # src is the EN test file (for IDs) — raw JSON is loaded separately inside _convert_kmi_ko
        "src": pathlib.Path("data/KMI/test/interactions_200.jsonl"),
        "src_raw": pathlib.Path("data/KMI/raw/kmi.json"),
        "dst": pathlib.Path("data/KMI/test/interactions_200_canonical_ko.jsonl"),
        "converter": _KMI_KO_SENTINEL,  # handled specially in main()
    },
    "esconv": {
        "display": "ESConv",
        "src": pathlib.Path("data/ESConv/raw/ESConv.json"),
        "dst": pathlib.Path("data/ESConv/test/interactions_200_canonical.jsonl"),
        "converter": _convert_esconv,
    },
}


# ---------------------------------------------------------------------------
# Spot-check helper
# ---------------------------------------------------------------------------

def _safe_print(text: str) -> None:
    """Print with fallback for terminals that cannot handle all Unicode."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _spot_check(records: list[dict], n: int = 2) -> None:
    """Print first n records for manual inspection."""
    for i, r in enumerate(records[:n]):
        roles = [t["role"] for t in r["interaction"]]
        first_client = next((t["content"][:60] for t in r["interaction"] if t["role"] == "client"), "-")
        first_counselor = next((t["content"][:60] for t in r["interaction"] if t["role"] == "counselor"), "-")
        _safe_print(f"  [{i}] id={r['interaction_id']}  turns={r['metadata']['turn_count']}"
                    f"  bucket={r['metadata']['length_bucket']}")
        _safe_print(f"       roles (first 6): {roles[:6]}")
        _safe_print(f"       client   : {first_client!r}")
        _safe_print(f"       counselor: {first_counselor!r}")
        if r.get("extra"):
            keys = list(r["extra"].keys())
            _safe_print(f"       extra keys: {keys}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert datasets to canonical schema.")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASET_CONFIGS.keys()),
        default=list(DATASET_CONFIGS.keys()),
        help="Datasets to convert (default: all)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print stats without writing output files",
    )
    parser.add_argument(
        "--spot_check",
        action="store_true",
        help="Print first 2 records of each dataset for manual verification",
    )
    args = parser.parse_args()

    print(f"{'='*60}")
    print("Canonical converter — Mind-Eval")
    print(f"{'='*60}")

    for key in args.datasets:
        cfg = DATASET_CONFIGS[key]
        src: pathlib.Path = cfg["src"]
        dst: pathlib.Path = cfg["dst"]
        converter = cfg["converter"]

        print(f"\n[{cfg['display']}]")
        print(f"  src: {src}")

        if not src.exists():
            print(f"  SKIP — source file not found: {src}")
            continue

        # Special case: kmi_ko needs raw JSON + EN ID list
        if converter is _KMI_KO_SENTINEL:
            raw_src: pathlib.Path = cfg["src_raw"]
            print(f"  raw: {raw_src}")
            if not raw_src.exists():
                print(f"  SKIP — raw file not found: {raw_src}")
                continue
            records = _convert_kmi_ko(en_src=src, raw_src=raw_src)
        else:
            records = converter(src)
        print(f"  records   : {len(records)}")

        # Sanity check: all roles are canonical
        bad = []
        for r in records:
            for t in r["interaction"]:
                if t["role"] not in ("client", "counselor"):
                    bad.append((r["interaction_id"], t["role"]))
        if bad:
            print(f"  WARNING: non-canonical roles found: {bad[:5]}")
        else:
            print(f"  roles     : OK (all 'client' / 'counselor')")

        # Length bucket distribution
        buckets: dict[str, int] = {}
        for r in records:
            b = r["metadata"]["length_bucket"]
            buckets[b] = buckets.get(b, 0) + 1
        print(f"  buckets   : {dict(sorted(buckets.items()))}")

        if args.spot_check:
            _spot_check(records)

        if args.dry_run:
            print(f"  dst: {dst}  [DRY RUN — not written]")
        else:
            _save_jsonl(records, dst)
            print(f"  dst: {dst}  [written]")

    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    main()
