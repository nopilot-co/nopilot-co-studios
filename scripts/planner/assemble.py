"""Deterministically merge approved sections into one ``source.md``.

This is the handoff boundary: the planner merges the composed section markdown
(in order) into ``<root>/<session>/inputs/source.md`` — exactly where the design
studio's ``studio session init --source`` expects to read it — then bumps the
composition version. The planner never renders; the creative-director chains the
merged source to the design studio's ``render-asset`` capability.

The *synthesis* judgment (de-duplication, connective prose, an intro) is a skill
step that edits section ``content.md`` / adds a synthesis section **before**
assemble runs, so ``source.md`` stays a pure build artifact (never hand-edited).
"""

from __future__ import annotations

from pathlib import Path

from . import composition as comp


class AssembleError(RuntimeError):
    pass


def _section_body(root: Path, sec: dict) -> str:
    content_path = root / sec["content"]
    text = content_path.read_text().strip() if content_path.is_file() else ""
    # Drop the empty-stub comment so blank sections don't pollute the merge.
    if text.startswith("<!--") and text.endswith("-->") and "\n" not in text:
        text = ""
    return text


def assemble(
    root: Path, *, bump_kind: str = "minor", allow_partial: bool = False
) -> dict:
    """Merge approved sections → ``<session>/inputs/source.md``; bump + log.

    Returns ``{"source": <path>, "version": <str>, "sections": [...], "render_hint": <str>}``.
    Raises :class:`AssembleError` when nothing is ready (or sections are missing
    and ``allow_partial`` is False).
    """
    data = comp.read(root)
    sections = data["sections"]
    if not sections:
        raise AssembleError("composition has no sections — add some first")

    approved = [s for s in sections if s["status"] == "approved"]
    not_approved = [s for s in sections if s["status"] != "approved"]

    if not approved:
        raise AssembleError(
            "no approved sections to assemble — approve at least one "
            "(`planner section set --id <id> --status approved`)"
        )
    if not_approved and not allow_partial:
        ids = ", ".join(f"{s['id']}({s['status']})" for s in not_approved)
        raise AssembleError(
            f"{len(not_approved)} section(s) not approved: {ids}. "
            "Approve them, or pass --allow-partial to assemble approved sections only."
        )

    bodies: list[str] = []
    used: list[str] = []
    empty: list[str] = []
    for sec in approved:
        body = _section_body(root, sec)
        if not body:
            empty.append(sec["id"])
            continue
        bodies.append(body)
        used.append(sec["id"])

    if not bodies:
        raise AssembleError(
            "every approved section has empty content — nothing to merge "
            f"(empty: {', '.join(empty)})"
        )

    # Output lands where `studio session init --source` reads it.
    session_dir = root / data["session"]
    inputs_dir = session_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    source_path = inputs_dir / "source.md"
    source_path.write_text("\n\n".join(bodies) + "\n")

    version = comp.bump(data["current"], bump_kind)
    comp.record_assemble(
        root, version=version, source_path=str(source_path), sections=used
    )

    render_hint = (
        f"design · render-asset · brand={data['brand']} · "
        f"format={data['format']} · source={source_path}"
    )
    return {
        "source": source_path,
        "version": version,
        "sections": used,
        "skipped_empty": empty,
        "render_hint": render_hint,
    }
