"""
The LTL law sets live in JSON files under laws/ instead of being hard-coded in
LTL_implementer.py. Each file is a list of {"law_id": ..., "law": ...,
"explanation": ...}:

[
    {"law_id": "law-001",
     "law": "G(obs_has_log & !obs_has_plank -> X(action_craft_planks))",
   "explanation": "If you have logs but no planks, craft planks"}
]

LTL_implementer loads them at import time, so the module-level names
(SOFT_LTL_RULES_SAYCAN, SOFT_LTL_RULES_INNER_MONOLOGUE, ...) keep working. The
critic writes to the same files, so its laws are picked up by the actor on its
next start. File order is preserved, while law_id keeps edits stable.
"""

import json
import os
import re

import spot

LAWS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "laws")

SAYCAN_SOFT_LAWS_PATH = os.path.join(LAWS_DIR, "saycan_soft_laws.json")
INNER_MONOLOGUE_SOFT_LAWS_PATH = os.path.join(LAWS_DIR, "inner_monologue_soft_laws.json")

# What the critic and the SayCan actor use unless told otherwise.
DEFAULT_LAWS_PATH = SAYCAN_SOFT_LAWS_PATH


def load(path=DEFAULT_LAWS_PATH):
    """Load and validate law entries in file order."""
    with open(path, "r") as f:
        entries = json.load(f)

    ids = [entry.get("law_id") for entry in entries]
    if any(not law_id for law_id in ids):
        raise ValueError(f"Every law entry in {path} must define law_id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Law IDs must be unique in {path}")
    return entries


def save(entries, path=DEFAULT_LAWS_PATH):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)
    return path


def load_rules(path=DEFAULT_LAWS_PATH):
    """(laws, explanations), index-aligned -- what LTL_implementer and the servers want."""
    entries = load(path)
    return [e["law"] for e in entries], [e.get("explanation", "") for e in entries]


# ---------------------------------------------------------------- validation


def _atomic_props(parsed):
    """Atomic propositions of a parsed formula. spot's atomic_prop_set is not
    safely iterable in every spot build, so walk the syntax tree instead."""
    props = set()

    def walk(node):
        if node.kind() == spot.op_ap:
            props.add(node.ap_name())
        for child in node:
            walk(child)

    walk(parsed)
    return props


def validate(law):
    """
    (ok, message). A law is usable only if spot can parse it AND every atomic
    proposition it mentions is one the observation/action extractors produce --
    an unknown proposition is left unconstrained by the word automaton, so the
    law would silently never fire.
    """
    from LTL_implementer import ACTION_VARIABLES_LIST, OBS_VARIABLES_LIST

    try:
        parsed = spot.formula(law)
    except BaseException as e:
        first_line = str(e).strip().splitlines()[0] if str(e).strip() else e
        return False, f"could not parse: {first_line}"

    known = OBS_VARIABLES_LIST + ACTION_VARIABLES_LIST
    unknown = sorted(ap for ap in _atomic_props(parsed) if ap not in known)
    if unknown:
        return False, "unknown atomic propositions: " + ", ".join(unknown)

    return True, "ok"


# ------------------------------------------------------------------- editing


def _canonical(law):
    """Comparison form used for duplicate detection."""
    try:
        return str(spot.formula(law))
    except BaseException:
        return "".join(law.split())


def add(entries, law, explanation=""):
    """
    Append a law. Returns (index, status) with status one of
    "added", "duplicate", or a validation error message.
    """
    law = law.strip()

    ok, message = validate(law)
    if not ok:
        return None, message

    if _canonical(law) in {_canonical(e["law"]) for e in entries}:
        return None, "duplicate"

    used_ids = {entry.get("law_id") for entry in entries}
    numeric_ids = [
        int(match.group(1))
        for law_id in used_ids
        if (match := re.fullmatch(r"law-(\d+)", law_id or ""))
    ]
    next_id = max(numeric_ids, default=0) + 1
    while f"law-{next_id:03d}" in used_ids:
        next_id += 1
    entries.append({"law_id": f"law-{next_id:03d}", "law": law, "explanation": explanation})
    return len(entries) - 1, "added"


def replace(entries, law_id, law, explanation=None):
    """Replace the law identified by `law_id`. Returns (index, status)."""
    index = next((i for i, entry in enumerate(entries) if entry["law_id"] == law_id), -1)
    if index < 0 or index >= len(entries):
        return None, "no such law"

    law = law.strip()
    ok, message = validate(law)
    if not ok:
        return index, message

    entries[index]["law"] = law
    if explanation is not None:
        entries[index]["explanation"] = explanation
    return index, "replaced"


def remove(entries, law_id):
    """Delete the law identified by `law_id`. Returns (entry, status)."""
    index = next((i for i, entry in enumerate(entries) if entry["law_id"] == law_id), -1)
    if index < 0 or index >= len(entries):
        return None, "no such law"
    return entries.pop(index), "deleted"


# -------------------------------------------------------------------- prompts


def format_for_prompt(entries):
    """List laws with stable IDs and their current positions."""
    if not entries:
        return "(no laws yet)"

    lines = []
    for i, entry in enumerate(entries):
        lines.append(f"{i + 1}. [{entry['law_id']}] {entry['law']}")
        if entry.get("explanation"):
            lines.append(f"   {entry['explanation']}")
    return "\n".join(lines)


def extract_json_block(text):
    """Pull a JSON object out of an LLM response that may be fenced or padded with prose."""
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in response")
    return json.loads(text[start:end + 1])
