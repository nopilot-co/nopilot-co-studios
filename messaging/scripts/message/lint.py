"""Deterministic ruleset enforcement for a composed message.

Checks the machine-verifiable rules (subject length, body budget, link count,
forbidden phrases). Subjective rules (required sections present, CTA strength,
voice) are the `message-qa` skill's job.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from . import formats as formats_mod
from . import session as session_mod
from . import voice as voice_mod


def parse_message(path: Path) -> tuple[dict[str, Any], str]:
    """Split a message file into (front-matter dict, body str)."""
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return (yaml.safe_load(parts[1]) or {}), parts[2]
    return {}, text


def _word_count(s: str) -> int:
    # ignore HTML comment scaffolding like <!-- hook -->
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return len(re.findall(r"\b[\w'-]+\b", s))


def _char_count(s: str) -> int:
    return len(re.sub(r"<!--.*?-->", "", s, flags=re.S).strip())


def _link_count(s: str) -> int:
    return len(re.findall(r"https?://\S+", s)) + len(re.findall(r"\]\(", s))


def lint(session_path: Path) -> list[str]:
    state = session_mod.read_state(session_path)
    resolved = formats_mod.resolve(state["format"])
    ruleset = resolved.get("ruleset") or {}

    msg_path = session_path / "inputs" / "message.md"
    if not msg_path.exists():
        return [f"no message at {msg_path}"]
    fm, body = parse_message(msg_path)
    subject = str(fm.get("subject") or "").strip()
    violations: list[str] = []

    if ruleset.get("subject_required") and not subject:
        violations.append("subject required but empty")
    if "max_subject_chars" in ruleset and len(subject) > ruleset["max_subject_chars"]:
        violations.append(
            f"subject {len(subject)} chars exceeds max_subject_chars={ruleset['max_subject_chars']}"
        )
    if "max_body_words" in ruleset:
        bw = _word_count(body)
        if bw > ruleset["max_body_words"]:
            violations.append(
                f"body {bw} words exceeds max_body_words={ruleset['max_body_words']}"
            )
    if "max_body_chars" in ruleset:
        bc = _char_count(body)
        if bc > ruleset["max_body_chars"]:
            violations.append(
                f"body {bc} chars exceeds max_body_chars={ruleset['max_body_chars']}"
            )
    if "max_links" in ruleset:
        lc = _link_count(body)
        if lc > ruleset["max_links"]:
            violations.append(f"{lc} links exceeds max_links={ruleset['max_links']}")

    forbidden = list(ruleset.get("forbidden", [])) + voice_mod.forbidden_words(
        state.get("brand")
    )
    haystack = f"{subject} {body}".lower()
    for term in forbidden:
        if term and term.lower() in haystack:
            violations.append(f"contains forbidden phrase: '{term}'")
    return violations
