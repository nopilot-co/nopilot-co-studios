"""Docket sync with the server (ADR-0001): push, pull, render guard."""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from . import brand as brand_mod
from . import session as session_mod

_SYNC_KEY = "sync"
_HTML_ENTRY_RE = re.compile(r"^source\.v\d+\.\d+\.\d+\.html$")


class SyncError(RuntimeError):
    """Base class for sync failures."""


class SyncConflictError(SyncError):
    """Local edits and server drift — needs explicit acknowledgement."""


class SyncGuardError(SyncError):
    """Render blocked until pull reconciles with server."""


def server_url(override: str | None = None) -> str:
    """Resolve the studio server base URL (no trailing slash)."""
    url = (override or os.environ.get("STUDIO_SERVER_URL") or "").strip().rstrip("/")
    if not url:
        raise SyncError(
            "STUDIO_SERVER_URL is not set. Export it or pass --server-url."
        )
    return url


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def source_hash(session_path: Path) -> str:
    """Content hash of the session's source markdown."""
    src = session_path / "inputs" / "source.md"
    if not src.exists():
        raise SyncError(f"session source missing: {src}")
    return _sha256_bytes(src.read_bytes())


def brand_hash(session_path: Path, slug: str) -> str:
    """Content hash of the brand's _brand.yml."""
    brand_yml = brand_mod.brand_yml_path(slug)
    if not brand_yml.exists():
        raise SyncError(f"brand spec missing: {brand_yml}")
    return _sha256_bytes(brand_yml.read_bytes())


def combined_hash(session_path: Path) -> str:
    """Hash covering source + brand — the sync reconciliation fingerprint."""
    state = session_mod.read_state(session_path)
    slug = state["brand"]
    payload = f"{source_hash(session_path)}\n{brand_hash(session_path, slug)}"
    return _sha256_text(payload)


def sync_state(session_path: Path) -> dict:
    state = session_mod.read_state(session_path)
    return state.setdefault(_SYNC_KEY, {})


def ensure_production_uuid(session_path: Path) -> str:
    """Return the session's production_uuid, minting and persisting if absent."""
    state = session_mod.read_state(session_path)
    uuid = state.get("production_uuid")
    if uuid:
        return uuid
    from .uuid_util import mint_production_uuid

    state["production_uuid"] = mint_production_uuid()
    session_mod.write_state(session_path, state)
    return state["production_uuid"]


def require_production_uuid(session_path: Path) -> str:
    state = session_mod.read_state(session_path)
    uuid = state.get("production_uuid")
    if not uuid:
        raise SyncError(
            "session has no production_uuid — re-run `studio session init` "
            "or add one via session init on this folder (issue A3)."
        )
    return uuid


def _request(
    method: str,
    url: str,
    payload: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"error": raw or e.reason}
        if e.code == 409:
            raise SyncError(
                f"server returned 409 (collision): {detail}. "
                "Retry after resolving the docket conflict on the server."
            ) from e
        raise SyncError(f"HTTP {e.code} from {url}: {detail}") from e
    except urllib.error.URLError as e:
        raise SyncError(f"could not reach server at {url}: {e.reason}") from e


def fetch_server_hash(session_path: Path, server: str | None = None) -> str:
    uuid = require_production_uuid(session_path)
    base = server_url(server)
    data = _request("GET", f"{base}/api/admin/dockets/{uuid}/source")
    h = data.get("hash")
    if not h:
        raise SyncError("server response missing `hash`")
    return h


def _latest_html_entry(session_path: Path) -> Path | None:
    outs = session_path / "outputs"
    if not outs.is_dir():
        return None
    candidates = sorted(
        p for p in outs.iterdir() if p.is_file() and _HTML_ENTRY_RE.match(p.name)
    )
    return candidates[-1] if candidates else None


def push(session_path: Path, server: str | None = None) -> dict:
    """POST source, brand, and latest rendered HTML entry to the server."""
    uuid = require_production_uuid(session_path)
    state = session_mod.read_state(session_path)
    slug = state["brand"]
    base = server_url(server)

    src_path = session_path / "inputs" / "source.md"
    brand_path = brand_mod.brand_yml_path(slug)
    entry = _latest_html_entry(session_path)

    payload: dict = {
        "source_md": src_path.read_text(encoding="utf-8"),
        "source_hash": source_hash(session_path),
        "brand_yml": brand_path.read_text(encoding="utf-8"),
        "brand_hash": brand_hash(session_path, slug),
        "combined_hash": combined_hash(session_path),
    }
    if entry is not None:
        payload["entry"] = {
            "filename": entry.name,
            "content_base64": base64.b64encode(entry.read_bytes()).decode("ascii"),
        }

    data = _request("POST", f"{base}/api/admin/dockets/{uuid}/sync", payload)
    status = data.get("status", "updated")
    server_hash = data.get("hash") or payload["combined_hash"]

    sync = sync_state(session_path)
    sync["server_hash"] = server_hash
    sync["source_hash"] = payload["source_hash"]
    sync["local_dirty"] = False
    session_mod.write_state(session_path, state)

    return {"status": status, "hash": server_hash, "production_uuid": uuid}


def _diff_summary(local: str, remote: str, label: str) -> str:
    diff = difflib.unified_diff(
        local.splitlines(keepends=True),
        remote.splitlines(keepends=True),
        fromfile=f"local {label}",
        tofile=f"server {label}",
        n=2,
    )
    lines = list(diff)
    if not lines:
        return f"(no textual diff for {label})"
    return "".join(lines[:40]) + ("…\n" if len(lines) > 40 else "")


def pull(
    session_path: Path,
    server: str | None = None,
    *,
    accept_server_wins: bool = False,
) -> dict:
    """GET server source; overwrite local when server has moved."""
    uuid = require_production_uuid(session_path)
    state = session_mod.read_state(session_path)
    slug = state["brand"]
    base = server_url(server)

    data = _request("GET", f"{base}/api/admin/dockets/{uuid}/source")
    server_hash = data.get("hash")
    if not server_hash:
        raise SyncError("server response missing `hash`")

    sync = sync_state(session_path)
    recorded = sync.get("server_hash")
    local_combined = combined_hash(session_path)
    local_dirty = sync.get("local_dirty") or (
        recorded is not None and local_combined != sync.get("last_synced_combined_hash")
    )

    if server_hash == recorded and not local_dirty:
        return {"status": "unchanged", "hash": server_hash}

    if local_dirty and recorded and server_hash != recorded and not accept_server_wins:
        local_src = (session_path / "inputs" / "source.md").read_text(encoding="utf-8")
        remote_src = data.get("source_md", "")
        summary = _diff_summary(local_src, remote_src, "source.md")
        raise SyncConflictError(
            "local source was edited since the last sync and the server has also "
            "moved. Re-run with --accept-server-wins to overwrite local with the "
            f"server copy (ADR-0001: server wins).\n\n{summary}"
        )

    if server_hash == local_combined and not data.get("source_md"):
        sync["server_hash"] = server_hash
        sync["last_synced_combined_hash"] = local_combined
        sync["local_dirty"] = False
        session_mod.write_state(session_path, state)
        return {"status": "unchanged", "hash": server_hash}

    src_md = data.get("source_md")
    brand_yml = data.get("brand_yml")
    if src_md is None:
        raise SyncError("server response missing `source_md`")

    (session_path / "inputs").mkdir(parents=True, exist_ok=True)
    (session_path / "inputs" / "source.md").write_text(src_md, encoding="utf-8")

    if brand_yml is not None:
        brand_path = brand_mod.brand_yml_path(slug)
        brand_path.parent.mkdir(parents=True, exist_ok=True)
        brand_path.write_text(brand_yml, encoding="utf-8")

    new_combined = combined_hash(session_path)
    sync["server_hash"] = server_hash
    sync["source_hash"] = source_hash(session_path)
    sync["last_synced_combined_hash"] = new_combined
    sync["local_dirty"] = False
    session_mod.write_state(session_path, state)

    status = "updated" if server_hash != recorded else "unchanged"
    return {"status": status, "hash": server_hash}


def check_render_guard(
    session_path: Path,
    server: str | None = None,
    *,
    no_sync_guard: bool = False,
) -> None:
    """Refuse render when local sync state is behind the server."""
    if no_sync_guard:
        return
    if not os.environ.get("STUDIO_SERVER_URL") and not server:
        return  # offline — no guard without a configured server
    sync = sync_state(session_path)
    if not sync.get("server_hash"):
        return  # never synced — allow first local render
    try:
        live = fetch_server_hash(session_path, server)
    except SyncError:
        return  # unreachable server — don't block offline render
    if live != sync.get("server_hash"):
        raise SyncGuardError(
            "render blocked: server content hash differs from the last pull/push. "
            "Run `studio sync pull --session <path>` first, or pass --no-sync-guard "
            "for offline work."
        )


def stamp_html_production_uuid(html_path: Path, production_uuid: str) -> None:
    """Inject a production-uuid meta tag into rendered HTML."""
    text = html_path.read_text(encoding="utf-8")
    tag = f'<meta name="production-uuid" content="{production_uuid}">'
    if "name=\"production-uuid\"" in text or "name='production-uuid'" in text:
        text = re.sub(
            r'<meta\s+name=["\']production-uuid["\']\s+content=["\'][^"\']*["\']\s*/?>',
            tag,
            text,
            count=1,
        )
    elif re.search(r"<head[^>]*>", text, re.I):
        text = re.sub(r"(<head[^>]*>)", rf"\1\n  {tag}", text, count=1, flags=re.I)
    else:
        text = f"{tag}\n{text}"
    html_path.write_text(text, encoding="utf-8")


def prune_rendered_html(session_path: Path, keep: int = 30) -> list[Path]:
    """Drop oldest source.v*.html artefacts beyond ``keep`` (dist only)."""
    outs = session_path / "outputs"
    if not outs.is_dir():
        return []
    files = sorted(
        p for p in outs.iterdir() if p.is_file() and _HTML_ENTRY_RE.match(p.name)
    )
    removed: list[Path] = []
    for path in files[:-keep]:
        path.unlink(missing_ok=True)
        sidecar = outs / f"{path.stem}_files"
        if sidecar.is_dir():
            shutil.rmtree(sidecar, ignore_errors=True)
        removed.append(path)
    return removed
