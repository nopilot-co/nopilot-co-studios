"""Orchestrate ingest / map / extend pipelines over the tool-bench.

The CLI calls into the functions here; this module knows which tool runs
when, captures the invocation into ``manifest.json`` via ``store``, and
returns a structured result.
"""

from __future__ import annotations

from pathlib import Path

from . import bridge
from .store import record_run, sources_dir


def ingest_notion(slug: str, *, database: str) -> dict:
    """Run ``notion-sources`` against the engagement's sources/ dir."""
    args = ["--database", database, "--out", str(sources_dir(slug))]
    proc = bridge.run("notion-sources", args)
    record_run(
        slug,
        tool="notion-sources",
        action="extract",
        args=args,
        exit_code=proc.returncode,
        note=(proc.stderr or proc.stdout or "")[:240],
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }


def ingest_source(slug: str, *, source: str, kind: str = "file") -> dict:
    """Append a single source. For files/URLs we file the source into the
    sources/ batch dir directly (notion-sources handles its own batch
    layout)."""
    src = Path(source).expanduser() if kind in ("file",) else None
    sd = sources_dir(slug)
    sd.mkdir(parents=True, exist_ok=True)
    if kind == "file":
        if src is None or not src.is_file():
            raise FileNotFoundError(f"source file not found: {source}")
        dest = sd / src.name
        dest.write_bytes(src.read_bytes())
        record_run(
            slug,
            tool="(none)",
            action=f"add-{kind}",
            args=[str(source)],
            note=f"copied to {dest}",
        )
        return {"ok": True, "dest": str(dest)}
    if kind == "url":
        # Park a one-line .url stub; source-enrich does the fetching.
        stub = sd / (Path(source).name or "source.url")
        stub.write_text(f"{source}\n")
        record_run(
            slug,
            tool="(none)",
            action="add-url",
            args=[source],
            note=f"filed stub at {stub}",
        )
        return {"ok": True, "dest": str(stub)}
    raise ValueError(f"unknown kind: {kind}")


def ingest_youtube(slug: str, *, url: str, out_name: str = "transcript.md") -> dict:
    """Run ``yt-transcript`` into the engagement's sources/ dir."""
    out_path = sources_dir(slug) / out_name
    args = [url, "--out", str(out_path), "--front-matter"]
    proc = bridge.run("yt-transcript", args)
    record_run(
        slug,
        tool="yt-transcript",
        action="extract",
        args=args,
        exit_code=proc.returncode,
    )
    return {
        "ok": proc.returncode == 0,
        "out": str(out_path),
        "stderr": proc.stderr,
    }


def ingest_enrich(slug: str) -> dict:
    args = ["--batch", str(sources_dir(slug))]
    proc = bridge.run("source-enrich", args)
    record_run(
        slug,
        tool="source-enrich",
        action="enrich",
        args=args,
        exit_code=proc.returncode,
    )
    return {"ok": proc.returncode == 0, "returncode": proc.returncode}


def ingest_summarise(slug: str, *, summary_json: str) -> dict:
    args = [
        "--batch",
        str(sources_dir(slug)),
        "--summary-json",
        summary_json,
    ]
    proc = bridge.run("source-summarise", args)
    record_run(
        slug,
        tool="source-summarise",
        action="summarise",
        args=args,
        exit_code=proc.returncode,
    )
    return {"ok": proc.returncode == 0, "returncode": proc.returncode}


def map_propose(
    slug: str, *, proposal_json: str | None = None, adopt: str | None = None
) -> dict:
    args = ["--batch", str(sources_dir(slug))]
    action = "propose"
    if adopt:
        args += ["--adopt", adopt]
        action = "adopt"
    elif proposal_json:
        args += ["--proposal-json", proposal_json]
        action = "materialise-proposal"
    proc = bridge.run("theme-propose", args)
    record_run(
        slug,
        tool="theme-propose",
        action=action,
        args=args,
        exit_code=proc.returncode,
    )
    return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}


def map_cluster(slug: str, *, assignments: str) -> dict:
    args = [
        "--batch",
        str(sources_dir(slug)),
        "--assignments",
        assignments,
        "--write-tags",
    ]
    proc = bridge.run("theme-cluster", args)
    record_run(
        slug,
        tool="theme-cluster",
        action="cluster",
        args=args,
        exit_code=proc.returncode,
    )
    return {"ok": proc.returncode == 0, "returncode": proc.returncode}


def map_entity(slug: str, *, spec: str) -> dict:
    args = [
        "--batch",
        str(sources_dir(slug)),
        "--spec",
        spec,
    ]
    proc = bridge.run("theme-entity", args)
    record_run(
        slug,
        tool="theme-entity",
        action="build",
        args=args,
        exit_code=proc.returncode,
    )
    return {"ok": proc.returncode == 0, "returncode": proc.returncode}
