"""Explore PsyDial-D4 structure and compute statistics."""
import json, sys, statistics
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

with open("data/PsyDial/raw/PsyDial-D4.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total records: {len(data)}")
print(f"Type: {type(data)}")
print()

# ── First record ─────────────────────────────────────────────────────────────
r0 = data[0]
print("Keys:", list(r0.keys()))
print()
print("=== FIRST RECORD ===")
for k, v in r0.items():
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
        for i, item in enumerate(v[:3]):
            print(f"    [{i}] {repr(str(item)[:300])}")
    elif isinstance(v, str):
        print(f"  {k}: {repr(v[:400])}")
    else:
        print(f"  {k}: {repr(v)}")

print()
print("=== SECOND RECORD ===")
r1 = data[1]
for k, v in r1.items():
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
        for i, item in enumerate(v[:2]):
            print(f"    [{i}] {repr(str(item)[:300])}")
    elif isinstance(v, str):
        print(f"  {k}: {repr(v[:300])}")
    else:
        print(f"  {k}: {repr(v)}")

print()
# ── Understand 'messages' structure ─────────────────────────────────────────
print("=== messages[0] structure ===")
msg0 = data[0]["messages"][0]
print(f"Type: {type(msg0)}")
if isinstance(msg0, dict):
    print("Keys:", list(msg0.keys()))
    for k, v in msg0.items():
        print(f"  {k}: {repr(str(v)[:300])}")
elif isinstance(msg0, list):
    print(f"  Inner list[{len(msg0)}]")
    for item in msg0[:3]:
        print(f"    {repr(str(item)[:300])}")

print()
# ── Gather stats across all records ─────────────────────────────────────────
turn_counts   = []
role_counter  = Counter()
field_keys    = Counter()

for rec in data:
    msgs = rec.get("messages", [])
    turn_counts.append(len(msgs))
    for msg in msgs:
        if isinstance(msg, dict):
            for k in msg.keys():
                field_keys[k] += 1
            role = msg.get("role") or msg.get("speaker") or msg.get("from") or "?"
            role_counter[str(role)] += 1
        elif isinstance(msg, list):
            # might be [role, content] pairs
            for item in msg:
                if isinstance(item, dict):
                    for k in item.keys():
                        field_keys[k] += 1

print("=== Turns per record ===")
print(f"  range: {min(turn_counts)}-{max(turn_counts)}")
print(f"  mean: {statistics.mean(turn_counts):.1f}, median: {statistics.median(turn_counts):.1f}")

print("\n=== Message field keys ===")
for k, v in field_keys.most_common():
    print(f"  {v:5d}  {k}")

print("\n=== Role values ===")
for k, v in role_counter.most_common():
    print(f"  {v:5d}  {repr(k)}")

# ── Check existing interactions_10.jsonl for reference format ────────────────
print("\n=== interactions_10.jsonl sample ===")
existing = Path("data/PsyDial/test/interactions_10.jsonl")
if existing.exists():
    lines = existing.read_text(encoding="utf-8").splitlines()
    r = json.loads(lines[0])
    print("Keys:", list(r.keys()))
    for k, v in r.items():
        if isinstance(v, dict):
            print(f"  {k}: {list(v.keys())}")
            for ik, iv in v.items():
                print(f"    {ik}: {repr(str(iv)[:100])}")
        elif isinstance(v, list):
            print(f"  {k}: list[{len(v)}] first turn = {v[0]}")
        else:
            print(f"  {k}: {repr(str(v)[:100])}")
