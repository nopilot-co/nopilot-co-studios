"""Render the composed message to its channel target(s).

Text targets (`.txt`/`.md`) are pure-Python. HTML email (`.html`/`.eml`) is
compiled with MJML (a Node CLI, declared as the email channel's `requires`);
when MJML is absent those targets are skipped and the CLI prints an install
hint. Deterministic only — no judgment.
"""

from __future__ import annotations

import html as _html
import subprocess
import tempfile
from email.message import EmailMessage
from pathlib import Path

from . import deps as deps_mod
from . import formats as formats_mod
from . import lint as lint_mod
from . import session as session_mod

_MJML_TARGETS = {"html", "eml"}


def _md_to_html(body: str) -> str:
    """Convert the markdown body to an HTML fragment (best-effort).

    Uses the `markdown` package when available; otherwise falls back to simple
    blank-line-separated, escaped paragraphs so render never hard-depends on it.
    """
    text = body.strip()
    try:
        import markdown  # pure-Python, optional

        return markdown.markdown(text, extensions=["extra"])
    except ImportError:
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "\n".join(f"<p>{_html.escape(p)}</p>" for p in paras)


def _mjml_html(body_html: str) -> str:
    """Wrap an HTML fragment in a minimal MJML doc and compile via the mjml CLI."""
    doc = (
        "<mjml><mj-body>"
        "<mj-section><mj-column>"
        f"<mj-text>{body_html}</mj-text>"
        "</mj-column></mj-section>"
        "</mj-body></mjml>"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjml", delete=False) as f:
        f.write(doc)
        mjml_path = f.name
    try:
        result = subprocess.run(
            ["mjml", "-s", mjml_path], capture_output=True, text=True
        )
    finally:
        Path(mjml_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"mjml failed:\n{result.stderr.strip()}")
    html = result.stdout
    # `mjml -s` prepends a `<!-- FILE: /tmp/… -->` banner; drop it so the temp
    # path doesn't leak into the rendered email.
    if html.lstrip().startswith("<!-- FILE:"):
        html = html.split("-->", 1)[1].lstrip("\n")
    return html


def _build_eml(subject: str, text_body: str, html_body: str) -> str:
    """An RFC 822 message with a plain-text part and an HTML alternative."""
    msg = EmailMessage()
    if subject:
        msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg.as_string()


def render(session_path: Path, bump_kind: str) -> dict[str, Path]:
    state = session_mod.read_state(session_path)
    resolved = formats_mod.resolve(state["format"])
    targets = formats_mod.channel_targets(resolved)
    if not targets:
        raise RuntimeError(f"format '{state['format']}' declares no render targets")

    msg_path = session_path / "inputs" / "message.md"
    if not msg_path.exists():
        raise FileNotFoundError(f"no message at {msg_path}; compose it first")
    fm, body = lint_mod.parse_message(msg_path)
    subject = str(fm.get("subject") or "").strip()

    new_version = session_mod.next_version(session_path, bump_kind)
    slug = state["format"]
    out_dir = session_path / "outputs"
    outputs: dict[str, Path] = {}

    # Compile the HTML body once if any MJML-gated target is requested and mjml exists.
    need_mjml = bool(_MJML_TARGETS & set(targets))
    body_html = (
        _mjml_html(_md_to_html(body)) if need_mjml and deps_mod.have("mjml") else None
    )

    for target in targets:
        dest = out_dir / f"{slug}.v{new_version}.{target}"
        if target == "txt":
            header = f"Subject: {subject}\n\n" if subject else ""
            dest.write_text(header + body.strip() + "\n")
        elif target == "md":
            dest.write_text(msg_path.read_text())
        elif target == "html":
            if body_html is None:
                continue  # mjml missing — CLI surfaces the install hint
            dest.write_text(body_html)
        elif target == "eml":
            if body_html is None:
                continue
            dest.write_text(_build_eml(subject, body.strip() + "\n", body_html))
        else:
            continue
        outputs[target] = dest

    session_mod.record_render(session_path, new_version, list(outputs), outputs)
    return outputs
