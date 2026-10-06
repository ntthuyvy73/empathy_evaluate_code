"""
Pretty viewer for JSONL files.

This script formats JSONL files for easy reading, showing dialogues
in a clean, readable format.

Usage:
    # View a JSONL file
    python view_jsonl.py data/simpsydial/test/option_a_interactions_en.jsonl
    
    # View specific dialogue by index
    python view_jsonl.py data/simpsydial/test/option_a_interactions_en.jsonl --index 0
    
    # Save formatted output to file
    python view_jsonl.py data/simpsydial/test/option_a_interactions_en.jsonl --output formatted.txt
"""

import json
from pathlib import Path
from typing import Optional


def format_dialogue(dialogue: dict, index: int) -> str:
    """Format a single dialogue for display."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"DIALOGUE #{index}")
    lines.append("=" * 80)
    
    # Metadata
    if 'metadata' in dialogue:
        lines.append("\n📋 METADATA:")
        for key, value in dialogue['metadata'].items():
            lines.append(f"  {key}: {value}")
    
    # Profile (if exists)
    if 'member_profile' in dialogue:
        profile = dialogue['member_profile']
        lines.append("\n👤 PROFILE:")
        lines.append(f"  Name: {profile.get('name', 'N/A')}")
        lines.append(f"  Age: {profile.get('age', 'N/A')}")
        lines.append(f"  Gender: {profile.get('gender_identity', 'N/A')}")
    
    # Interaction
    if 'interaction' in dialogue:
        lines.append("\n💬 CONVERSATION:")
        lines.append("-" * 80)
        
        for i, turn in enumerate(dialogue['interaction'], 1):
            role = turn.get('role', 'unknown')
            content = turn.get('content', '')
            
            # Format role
            if role == 'user':
                role_display = "👤 USER"
            elif role == 'assistant':
                role_display = "🤖 ASSISTANT"
            else:
                role_display = f"❓ {role.upper()}"
            
            lines.append(f"\n[Turn {i}] {role_display}:")
            lines.append(f"{content}")
            lines.append("-" * 80)
    
    return "\n".join(lines)


def view_jsonl(
    file_path: str,
    index: Optional[int] = None,
    output: Optional[str] = None
):
    """
    View JSONL file in formatted way.
    
    Args:
        file_path: Path to JSONL file
        index: View specific dialogue by index (0-based)
        output: Save formatted output to file
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    # Read all dialogues
    dialogues = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                dialogues.append(json.loads(line))
    
    if not dialogues:
        print(f"❌ No dialogues found in {file_path}")
        return
    
    print(f"\n📁 File: {file_path}")
    print(f"📊 Total dialogues: {len(dialogues)}\n")
    
    # Format dialogues
    formatted_lines = []
    
    if index is not None:
        # View specific dialogue
        if 0 <= index < len(dialogues):
            formatted = format_dialogue(dialogues[index], index)
            formatted_lines.append(formatted)
        else:
            print(f"❌ Index {index} out of range (0-{len(dialogues)-1})")
            return
    else:
        # View all dialogues
        for i, dialogue in enumerate(dialogues):
            formatted = format_dialogue(dialogue, i)
            formatted_lines.append(formatted)
            formatted_lines.append("\n")
    
    formatted_text = "\n".join(formatted_lines)
    
    # Output
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
        print(f"✅ Formatted output saved to: {output}")
    else:
        print(formatted_text)


def compare_dialogues(file1: str, file2: str, index: int = 0):
    """
    Compare two dialogues side by side.
    
    Args:
        file1: First JSONL file
        file2: Second JSONL file
        index: Dialogue index to compare
    """
    # Read dialogues
    with open(file1, 'r', encoding='utf-8') as f:
        dialogue1 = json.loads(f.readline())
    
    with open(file2, 'r', encoding='utf-8') as f:
        dialogue2 = json.loads(f.readline())
    
    print("=" * 80)
    print("DIALOGUE COMPARISON")
    print("=" * 80)
    
    print(f"\n📁 File 1: {file1}")
    print(f"📁 File 2: {file2}")
    
    # Compare interactions
    interaction1 = dialogue1.get('interaction', [])
    interaction2 = dialogue2.get('interaction', [])
    
    print(f"\n💬 CONVERSATION COMPARISON:")
    print("-" * 80)
    
    max_turns = max(len(interaction1), len(interaction2))
    
    for i in range(max_turns):
        print(f"\n[Turn {i+1}]")
        
        if i < len(interaction1):
            turn1 = interaction1[i]
            print(f"\n📄 File 1 ({turn1.get('role', 'unknown')}):")
            print(f"{turn1.get('content', 'N/A')}")
        else:
            print(f"\n📄 File 1: (no turn)")
        
        if i < len(interaction2):
            turn2 = interaction2[i]
            print(f"\n📄 File 2 ({turn2.get('role', 'unknown')}):")
            print(f"{turn2.get('content', 'N/A')}")
        else:
            print(f"\n📄 File 2: (no turn)")
        
        print("-" * 80)


def main():
    """Main CLI interface."""
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    file_path = sys.argv[1]
    
    # Parse arguments
    index = None
    output = None
    compare_file = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--index' and i + 1 < len(sys.argv):
            index = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--compare' and i + 1 < len(sys.argv):
            compare_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Execute
    if compare_file:
        compare_dialogues(file_path, compare_file, index or 0)
    else:
        view_jsonl(file_path, index, output)


if __name__ == "__main__":
    main()
