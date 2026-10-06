"""
Prepare standardised test samples from raw counselling datasets.

Reads raw data from each dataset's raw/ folder, samples N dialogues, normalises
them to the shared Mind-Eval JSONL format, and writes the result to the
dataset's test/ folder.

Supported datasets: cactus, kmi, psydial, simpsydial, soulchat

Output format (one JSON object per line):
{
  "member_profile": { <18-field schema, mostly "Unknown"> },
  "interaction":    [ {"role": "user"|"assistant", "content": "..."}, ... ],
  "metadata":       { "source": "<DATASET>", "original_id": ...,
                      "language": "en"|"zh"|"ko", ... }
}

Usage examples:
    # Sample 10 from every dataset (default)
    python mindeval/scripts/prepare_test_data.py

    # Sample 100 from every dataset
    python mindeval/scripts/prepare_test_data.py --n 100

    # Sample 200 only from cactus and kmi
    python mindeval/scripts/prepare_test_data.py --n 200 --datasets cactus kmi

    # Custom data root and output filename
    python mindeval/scripts/prepare_test_data.py --n 50 --data_dir data --output_name interactions.jsonl

    # Reproducible random sampling
    python mindeval/scripts/prepare_test_data.py --n 100 --seed 123
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Shared default profile template
# ---------------------------------------------------------------------------
DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Anonymous",
    "sex": "Unknown",
    "gender_identity": "Unknown",
    "sexual_orientation": "Unknown",
    "age": "Unknown",
    "race": "Unknown",
    "education": "Unknown",
    "profession": "Unknown",
    "employment_status": "Unknown",
    "siblings": "Unknown",
    "relationship_status": "Unknown",
    "living_situation": "Unknown",
    "exercise": "Unknown",
    "sleep_quality": "Unknown",
    "attitude_towards_mindfulness": "Unknown",
    "region": "Unknown",
    "depressive_symptoms": "Unknown",
    "anxious_symptoms": "Unknown",
}


def _make_record(
    interaction: List[Dict[str, str]],
    metadata: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Wrap an interaction list into the standard Mind-Eval record."""
    return {
        "member_profile": (profile or DEFAULT_PROFILE).copy(),
        "interaction": interaction,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# CACTUS
# ---------------------------------------------------------------------------

def _parse_cactus_dialogue(dialogue_str: str) -> List[Dict[str, str]]:
    """
    Parse a CACTUS dialogue string into a list of turn dicts.

    The raw format is a single string where each turn begins on a new line
    with 'Counselor: ' or 'Client: '.  A turn can span multiple lines.
    """
    turns: List[Dict[str, str]] = []
    current_role: Optional[str] = None
    current_lines: List[str] = []

    for line in dialogue_str.splitlines():
        if line.startswith("Counselor: "):
            if current_role is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    turns.append({"role": current_role, "content": content})
            current_role = "assistant"
            current_lines = [line[len("Counselor: "):]]
        elif line.startswith("Client: "):
            if current_role is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    turns.append({"role": current_role, "content": content})
            current_role = "user"
            current_lines = [line[len("Client: "):]]
        else:
            # Continuation of the previous turn
            current_lines.append(line)

    if current_role is not None:
        content = "\n".join(current_lines).strip()
        if content:
            turns.append({"role": current_role, "content": content})

    return turns


def convert_cactus(raw_path: Path, n: int, seed: int) -> List[Dict[str, Any]]:
    """Load and sample from cactus.json."""
    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)

    rng = random.Random(seed)
    sample = rng.sample(data, min(n, len(data)))

    records = []
    for idx, item in enumerate(sample):
        dialogue_str = item.get("dialogue", "")
        turns = _parse_cactus_dialogue(dialogue_str)
        if not turns:
            continue

        # Build a minimal profile from available intake fields
        profile = DEFAULT_PROFILE.copy()

        metadata = {
            "source": "CACTUS",
            "original_index": data.index(item),
            "cbt_technique": item.get("cbt_technique", "Unknown"),
            "attitude": item.get("attitude", "Unknown"),
            "language": "en",
            "profile_extracted": False,
        }

        records.append(_make_record(turns, metadata, profile))

    return records


# ---------------------------------------------------------------------------
# KMI
# ---------------------------------------------------------------------------

def convert_kmi(raw_path: Path, n: int, seed: int) -> List[Dict[str, Any]]:
    """Load and sample from kmi.json (English utterances only)."""
    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)

    rng = random.Random(seed)
    sample = rng.sample(data, min(n, len(data)))

    records = []
    for item in sample:
        turns = []
        for turn in item.get("dialogue", []):
            role = "assistant" if turn["role"] == "Therapist" else "user"
            content = turn.get("utterance_en", "")
            if content:
                turns.append({"role": role, "content": content})

        if not turns:
            continue

        profile = DEFAULT_PROFILE.copy()
        profile["race"] = "Asian"
        profile["region"] = "urban"

        metadata = {
            "source": "KMI",
            "original_id": item.get("id"),
            "category": item.get("category_en", "Unknown"),
            "language": "en",
            "profile_extracted": False,
        }

        records.append(_make_record(turns, metadata, profile))

    return records


# ---------------------------------------------------------------------------
# PsyDial
# ---------------------------------------------------------------------------

def convert_psydial(raw_path: Path, n: int, seed: int) -> List[Dict[str, Any]]:
    """Load and sample from PsyDial-D4.json (Chinese, skip system prompt)."""
    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)

    rng = random.Random(seed)
    sample = rng.sample(data, min(n, len(data)))

    records = []
    for idx, item in enumerate(sample):
        messages = item.get("messages", [])
        turns = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
        ]

        if not turns:
            continue

        profile = DEFAULT_PROFILE.copy()
        profile["race"] = "Asian"
        profile["region"] = "urban"

        metadata = {
            "source": "PsyDial",
            "original_index": data.index(item),
            "language": "zh",
            "profile_extracted": False,
        }

        records.append(_make_record(turns, metadata, profile))

    return records


# ---------------------------------------------------------------------------
# SimPsyDial
# ---------------------------------------------------------------------------

def convert_simpsydial(raw_dir: Path, n: int, seed: int) -> List[Dict[str, Any]]:
    """Load and sample from SimPsyDial individual JSON files."""
    json_files = sorted(raw_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)

    rng = random.Random(seed)
    sampled_files = rng.sample(json_files, min(n, len(json_files)))

    records = []
    for fpath in sampled_files:
        with open(fpath, encoding="utf-8") as f:
            dialogue = json.load(f)

        turns = [
            {"role": t["role"], "content": t["content"]}
            for t in dialogue
            if t.get("content", "").strip()
        ]

        if not turns:
            continue

        profile = DEFAULT_PROFILE.copy()
        profile["race"] = "Asian"
        profile["region"] = "urban"

        metadata = {
            "source": "SimPsyDial",
            "original_file": fpath.name,
            "language": "zh",
            "profile_extracted": False,
        }

        records.append(_make_record(turns, metadata, profile))

    return records


# ---------------------------------------------------------------------------
# SoulChat
# ---------------------------------------------------------------------------

def convert_soulchat(raw_path: Path, n: int, seed: int) -> List[Dict[str, Any]]:
    """Load and sample from SoulChatCorpus-sft-multi-Turn.json (Chinese)."""
    print(f"  Loading SoulChat (large file, may take a moment)…")
    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)

    # SoulChat may use 用户/心理咨询师 or user/assistant depending on version
    role_map = {
        "用户": "user",
        "心理咨询师": "assistant",
        "user": "user",
        "assistant": "assistant",
    }

    rng = random.Random(seed)
    sample = rng.sample(data, min(n, len(data)))

    records = []
    for item in sample:
        messages = item.get("messages", [])
        turns = []
        for m in messages:
            role = role_map.get(m.get("role", ""), m.get("role", ""))
            content = m.get("content", "").strip()
            if content and role in ("user", "assistant"):
                turns.append({"role": role, "content": content})

        if not turns:
            continue

        profile = DEFAULT_PROFILE.copy()
        profile["race"] = "Asian"
        profile["region"] = "urban"

        metadata = {
            "source": "SoulChat",
            "original_id": item.get("id"),
            "topic": item.get("topic", "Unknown"),
            "language": "zh",
            "profile_extracted": False,
        }

        records.append(_make_record(turns, metadata, profile))

    return records


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------

DATASET_CONFIGS = {
    "cactus": {
        "raw_file": "cactus/raw/cactus.json",
        "converter": convert_cactus,
        "raw_is_file": True,
    },
    "kmi": {
        "raw_file": "KMI/raw/kmi.json",
        "converter": convert_kmi,
        "raw_is_file": True,
    },
    "psydial": {
        "raw_file": "PsyDial/raw/PsyDial-D4.json",
        "converter": convert_psydial,
        "raw_is_file": True,
    },
    "simpsydial": {
        "raw_file": "SimPsyDial/raw",
        "converter": convert_simpsydial,
        "raw_is_file": False,
    },
    "soulchat": {
        "raw_file": "SoulChat/raw/SoulChatCorpus-sft-multi-Turn.json",
        "converter": convert_soulchat,
        "raw_is_file": True,
    },
}

# Output directory for each dataset (relative to data_dir)
DATASET_OUTPUT_DIRS = {
    "cactus": "cactus/test",
    "kmi": "KMI/test",
    "psydial": "PsyDial/test",
    "simpsydial": "SimPsyDial/test",
    "soulchat": "SoulChat/test",
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare standardised test samples from raw counselling datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of dialogues to sample per dataset (default: 10).",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASET_CONFIGS.keys()),
        default=list(DATASET_CONFIGS.keys()),
        help="Datasets to process (default: all).",
    )
    parser.add_argument(
        "--data_dir",
        default="data",
        help="Base data directory relative to the project root (default: data).",
    )
    parser.add_argument(
        "--output_name",
        default=None,
        help=(
            "Output JSONL filename (default: interactions_<N>.jsonl). "
            "Written inside each dataset's test/ folder."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42).",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_name = args.output_name or f"interactions_{args.n}.jsonl"

    print(f"Settings: n={args.n}  seed={args.seed}  output={output_name}")
    print(f"Data dir : {data_dir.resolve()}")
    print(f"Datasets : {', '.join(args.datasets)}")
    print()

    for ds_name in args.datasets:
        cfg = DATASET_CONFIGS[ds_name]
        raw_path = data_dir / cfg["raw_file"]

        # Existence check
        if cfg["raw_is_file"]:
            if not raw_path.is_file():
                print(f"[{ds_name.upper()}] SKIP – raw file not found: {raw_path}")
                continue
        else:
            if not raw_path.is_dir():
                print(f"[{ds_name.upper()}] SKIP – raw directory not found: {raw_path}")
                continue

        print(f"[{ds_name.upper()}] Converting…")
        try:
            converter = cfg["converter"]
            if cfg["raw_is_file"]:
                records = converter(raw_path, args.n, args.seed)
            else:
                records = converter(raw_path, args.n, args.seed)
        except Exception as exc:
            print(f"[{ds_name.upper()}] ERROR during conversion: {exc}")
            import traceback
            traceback.print_exc()
            continue

        out_dir = data_dir / DATASET_OUTPUT_DIRS[ds_name]
        out_path = out_dir / output_name
        save_jsonl(records, out_path)
        print(f"[{ds_name.upper()}] Saved {len(records)} records -> {out_path}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
