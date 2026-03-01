#!/usr/bin/env python3
"""
RPD SWMS Vocabulary Management Tool

Commands:
  python src/vocab_tool.py list hazards     — all hazard keys + canonical
  python src/vocab_tool.py list controls    — all control keys + canonical
  python src/vocab_tool.py list ppe         — all PPE keys + items
  python src/vocab_tool.py list stopwork    — all STOP WORK keys + conditions
  python src/vocab_tool.py add hazard       — interactive: add new hazard
  python src/vocab_tool.py add control      — interactive: add new control
  python src/vocab_tool.py add ppe          — interactive: add new PPE item
  python src/vocab_tool.py add stopwork     — interactive: add new STOP WORK
  python src/vocab_tool.py check "text"     — scan text for variant phrases
  python src/vocab_tool.py scan             — scan swms_generator.py for raw strings
"""

import sys
import os
import re

# Ensure src/ is on path
_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)

from swms_vocabulary import HAZARDS, CONTROLS, PPE_ITEMS, STOP_WORK


# ============================================================
# LIST COMMANDS
# ============================================================

def list_hazards():
    """Print all hazard keys and canonical phrases."""
    print(f"\nHAZARDS ({len(HAZARDS)} entries)")
    print("=" * 70)
    for key in sorted(HAZARDS.keys()):
        canonical = HAZARDS[key]["canonical"]
        print(f"  {key:<40s} {canonical}")


def list_controls():
    """Print all control keys and canonical phrases."""
    print(f"\nCONTROLS ({len(CONTROLS)} entries)")
    print("=" * 70)
    for key in sorted(CONTROLS.keys()):
        canonical = CONTROLS[key]["canonical"]
        # Truncate long phrases for display
        display = canonical[:80] + "..." if len(canonical) > 80 else canonical
        print(f"  {key:<35s} {display}")


def list_ppe():
    """Print all PPE keys and items."""
    print(f"\nPPE ITEMS ({len(PPE_ITEMS)} entries)")
    print("=" * 70)
    for key in sorted(PPE_ITEMS.keys()):
        print(f"  {key:<30s} {PPE_ITEMS[key]}")


def list_stopwork():
    """Print all STOP WORK keys and conditions."""
    print(f"\nSTOP WORK ({len(STOP_WORK)} entries)")
    print("=" * 70)
    for key in sorted(STOP_WORK.keys()):
        condition = STOP_WORK[key]
        display = condition[:80] + "..." if len(condition) > 80 else condition
        print(f"  {key:<35s} {display}")


# ============================================================
# ADD COMMANDS
# ============================================================

def add_entry(dict_name, dict_obj):
    """Interactive prompt to add a new entry to vocabulary."""
    print(f"\nAdd new {dict_name} entry")
    print("=" * 40)

    key = input("Key (snake_case): ").strip()
    if not key:
        print("Aborted — no key entered.")
        return
    if not re.match(r'^[a-z][a-z0-9_]*$', key):
        print(f"Invalid key format: '{key}' — use snake_case (a-z, 0-9, _)")
        return
    if key in dict_obj:
        print(f"Key '{key}' already exists: {dict_obj[key]}")
        return

    if dict_name == 'PPE_ITEMS':
        value = input("Canonical PPE item: ").strip()
        if not value:
            print("Aborted — no value entered.")
            return
        snippet = f'    "{key}": "{value}",'
    elif dict_name == 'STOP_WORK':
        value = input("Canonical STOP WORK condition: ").strip()
        if not value:
            print("Aborted — no value entered.")
            return
        snippet = f'    "{key}": "{value}",'
    else:
        value = input("Canonical phrase: ").strip()
        if not value:
            print("Aborted — no value entered.")
            return
        snippet = (
            f'    "{key}": {{\n'
            f'        "canonical": "{value}",\n'
            f'    }},'
        )

    print(f"\nAdd this to swms_vocabulary.py in the {dict_name} dict:\n")
    print(snippet)
    print()

    # Attempt to write directly to file
    vocab_path = os.path.join(_script_dir, 'swms_vocabulary.py')
    if not os.path.exists(vocab_path):
        print("Cannot find swms_vocabulary.py — add manually.")
        return

    confirm = input("Write to file? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Not written — copy the snippet above manually.")
        return

    with open(vocab_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the closing brace of the target dict
    # Strategy: find 'DICT_NAME = {' then find its matching '}'
    pattern = rf'^{dict_name}\s*=\s*\{{'
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(f"Could not find {dict_name} dict in swms_vocabulary.py — add manually.")
        return

    # Find the next line that is just '}' (end of dict)
    start = match.end()
    # Walk through to find the closing brace at the correct nesting level
    depth = 1
    pos = start
    while pos < len(content) and depth > 0:
        if content[pos] == '{':
            depth += 1
        elif content[pos] == '}':
            depth -= 1
        pos += 1

    if depth != 0:
        print(f"Could not find end of {dict_name} dict — add manually.")
        return

    # pos is now just past the closing }
    # Insert before the closing }
    insert_pos = pos - 1
    # Find the last newline before the closing brace
    last_nl = content.rfind('\n', start, insert_pos)
    if last_nl == -1:
        print("Could not determine insertion point — add manually.")
        return

    # Insert after the last entry
    new_content = content[:last_nl] + '\n' + snippet + content[last_nl:]

    with open(vocab_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Written to swms_vocabulary.py — key '{key}' added to {dict_name}.")


# ============================================================
# CHECK COMMAND
# ============================================================

# Common variant phrases that should use canonical forms
VARIANT_MAP = {
    # PPE variants
    'safety boots': 'steel_cap → "Steel-capped footwear"',
    'safety footwear': 'steel_cap → "Steel-capped footwear"',
    'steel toe': 'steel_cap → "Steel-capped footwear"',
    'steel cap boots': 'steel_cap → "Steel-capped footwear"',
    'hi-viz': 'hi_vis → "High-vis vest or shirt"',
    'high-viz': 'hi_vis → "High-vis vest or shirt"',
    'high-vis vest': 'hi_vis → "High-vis vest or shirt" (add "or shirt")',
    'safety glasses': 'eye_protection → "Eye protection"',
    'safety goggles': 'eye_protection_goggles → "Eye protection or goggles"',
    'dust mask': 'p2_dust_mask → "P2 dust mask" (ensure P2 rating specified)',
    'hard hat': 'hard_hat → "Hard hat"',
    'gloves': 'Specify type: cut_resistant_gloves, nitrile_gloves, etc.',
    # Hazard variants
    'manual handling': 'Use specific key: manual_handling_membrane, manual_handling_heavy_bags, etc.',
    'working at height': 'working_at_height → "Working at height"',
    'working at heights': 'working_at_height → "Working at height" (no plural)',
    'noise': 'Use noise_cutting or noise_general',
    'silica': 'Use silica_dust_cutting or silica_dust_concrete',
}


def check_text(text):
    """Scan text for variant phrases and suggest canonical replacements."""
    print(f"\nChecking text ({len(text)} chars)...")
    print("=" * 70)
    found = 0
    text_lower = text.lower()

    for variant, suggestion in VARIANT_MAP.items():
        if variant.lower() in text_lower:
            print(f"  FOUND: '{variant}'")
            print(f"    USE:  {suggestion}")
            found += 1

    # Also check against all canonical phrases for near-matches
    all_canonicals = {}
    for key, val in HAZARDS.items():
        all_canonicals[val["canonical"].lower()] = f"HAZARDS['{key}']"
    for key, val in CONTROLS.items():
        all_canonicals[val["canonical"].lower()] = f"CONTROLS['{key}']"
    for key, val in PPE_ITEMS.items():
        all_canonicals[val.lower()] = f"PPE_ITEMS['{key}']"
    for key, val in STOP_WORK.items():
        all_canonicals[val.lower()] = f"STOP_WORK['{key}']"

    # Check if text contains any canonical phrases (good sign)
    matches = 0
    for canonical, source in all_canonicals.items():
        if canonical in text_lower:
            matches += 1

    if found == 0:
        print("  No variant phrases detected.")
    print(f"\n  {matches} canonical phrase(s) already present in text.")
    print(f"  {found} variant(s) found — consider replacing with canonical forms.")


# ============================================================
# SCAN COMMAND
# ============================================================

def scan_generator():
    """Scan swms_generator.py for raw strings not in vocabulary."""
    gen_path = os.path.join(_script_dir, 'swms_generator.py')
    if not os.path.exists(gen_path):
        print("Cannot find swms_generator.py")
        return

    with open(gen_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("\nScanning swms_generator.py for raw strings...")
    print("=" * 70)

    # Build sets of all canonical phrases
    all_canonical = set()
    for val in HAZARDS.values():
        all_canonical.add(val["canonical"])
    for val in CONTROLS.values():
        all_canonical.add(val["canonical"])
    for val in PPE_ITEMS.values():
        all_canonical.add(val)
    for val in STOP_WORK.values():
        all_canonical.add(val)

    # Find all string literals in task dicts that look like control text
    # Pattern: 'key': 'long text string' (longer than 30 chars = likely control text)
    raw_strings = []
    in_dict = False
    for line_no, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()

        # Track when we're inside a *_NEW dict
        if re.match(r'^[A-Z_]+_NEW\s*=\s*\{', stripped):
            in_dict = True
        if in_dict and stripped == '}':
            in_dict = False

        if not in_dict:
            continue

        # Skip new_task() calls — those use vocabulary
        if 'new_task(' in stripped:
            continue

        # Find string values in tuples like ('Engineering:', 'text...')
        tuple_match = re.search(r"\('(?:Engineering|Admin|PPE|STOP WORK)[^']*',\s*'([^']{30,})'", line)
        if tuple_match:
            text = tuple_match.group(1)
            # Check if it's a known canonical
            if text not in all_canonical:
                raw_strings.append((line_no, 'control', text[:80]))
                continue

        # Find 'hazard': 'text...' patterns
        hazard_match = re.search(r"'hazard':\s*'([^']{30,})'", line)
        if hazard_match:
            text = hazard_match.group(1)
            raw_strings.append((line_no, 'hazard', text[:80]))

    if raw_strings:
        print(f"\n  {len(raw_strings)} raw string(s) found (not using vocabulary):\n")
        for line_no, stype, text in raw_strings:
            print(f"  Line {line_no:4d} [{stype:8s}] {text}...")
        print(f"\n  Consider converting these to use new_task() with vocabulary keys.")
    else:
        print("  All task definitions use vocabulary — no raw strings found.")

    # Count vocab vs raw tasks
    # Simple heuristic: count new_task() calls vs raw dict definitions
    new_task_count = content.count('new_task(')
    raw_dict_count = content.count("'type': 'STD'") + content.count("'type': 'CCVS'")
    total = new_task_count + raw_dict_count

    print(f"\n  Task definitions: {new_task_count} vocabulary-based, "
          f"{raw_dict_count} raw dicts ({total} total)")
    if raw_dict_count > 0:
        pct = (new_task_count / total * 100) if total > 0 else 0
        print(f"  Vocabulary coverage: {pct:.0f}%")


# ============================================================
# MAIN
# ============================================================

def usage():
    print(__doc__)
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1].lower()

    if cmd == 'list':
        if len(sys.argv) < 3:
            print("Usage: vocab_tool.py list [hazards|controls|ppe|stopwork]")
            sys.exit(1)
        target = sys.argv[2].lower()
        if target == 'hazards':
            list_hazards()
        elif target == 'controls':
            list_controls()
        elif target == 'ppe':
            list_ppe()
        elif target == 'stopwork':
            list_stopwork()
        else:
            print(f"Unknown list target: {target}")
            print("Options: hazards, controls, ppe, stopwork")
            sys.exit(1)

    elif cmd == 'add':
        if len(sys.argv) < 3:
            print("Usage: vocab_tool.py add [hazard|control|ppe|stopwork]")
            sys.exit(1)
        target = sys.argv[2].lower()
        if target == 'hazard':
            add_entry('HAZARDS', HAZARDS)
        elif target == 'control':
            add_entry('CONTROLS', CONTROLS)
        elif target == 'ppe':
            add_entry('PPE_ITEMS', PPE_ITEMS)
        elif target == 'stopwork':
            add_entry('STOP_WORK', STOP_WORK)
        else:
            print(f"Unknown add target: {target}")
            sys.exit(1)

    elif cmd == 'check':
        if len(sys.argv) < 3:
            print("Usage: vocab_tool.py check \"some text to check\"")
            sys.exit(1)
        text = ' '.join(sys.argv[2:])
        check_text(text)

    elif cmd == 'scan':
        scan_generator()

    else:
        print(f"Unknown command: {cmd}")
        usage()
