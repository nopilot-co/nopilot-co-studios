"""Jobs in the engagement manifest: id allocation + status transitions.

A job is one invocation of a capability within the engagement. The Producer
spawns + advances them as the cast does the work. The manifest is the
audit trail.
"""

from __future__ import annotations

import re

from . import autonomy
from .manifest import (
    JOB_STATUSES,
    append_history,
    read,
    write,
)


def _allocate_id(jobs: list[dict]) -> str:
    used = []
    for j in jobs:
        jid = j.get("id") or ""
        if jid.startswith("J-"):
            try:
                used.append(int(jid[2:]))
            except ValueError:
                continue
    n = (max(used) + 1) if used else 1
    return f"J-{n:03d}"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "job"


def add(
    root,
    *,
    capability: str,
    role: str | None = None,
    title: str | None = None,
    inputs: dict | None = None,
    checkpoint: str | None = None,
    action_class: str = "L1",
) -> dict:
    if action_class not in autonomy.ACTION_CLASSES:
        raise ValueError(
            f"action_class must be one of: {', '.join(autonomy.ACTION_CLASSES)}"
        )
    data = read(root)
    jobs = data.setdefault("jobs", [])
    jid = _allocate_id(jobs)
    job = {
        "id": jid,
        "slug": _slugify(title or capability),
        "capability": capability,
        "role": role or "",
        "title": title or "",
        "status": "planned",
        "action_class": action_class,
    }
    if inputs:
        job["inputs"] = inputs
    if checkpoint:
        job["checkpoint"] = checkpoint
    jobs.append(job)
    append_history(data, f"job + {jid} ({capability}, {action_class})")
    write(root, data)
    return job


def set_status(root, *, job_id: str, status: str) -> dict:
    if status not in JOB_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(JOB_STATUSES)}")
    data = read(root)
    for j in data.get("jobs", []):
        if j.get("id") == job_id:
            autonomy.check_transition(data, job=j, new_status=status)
            j["status"] = status
            append_history(data, f"job {job_id} → {status}")
            write(root, data)
            return j
    raise KeyError(f"no job '{job_id}'")


def set_outputs(root, *, job_id: str, outputs: list[str] | dict) -> dict:
    data = read(root)
    for j in data.get("jobs", []):
        if j.get("id") == job_id:
            j["outputs"] = (
                list(outputs) if isinstance(outputs, (list, tuple)) else outputs
            )
            append_history(data, f"job {job_id} outputs set")
            write(root, data)
            return j
    raise KeyError(f"no job '{job_id}'")


def list_jobs(root, *, status: str | None = None) -> list[dict]:
    data = read(root)
    rows = data.get("jobs") or []
    if status:
        rows = [j for j in rows if j.get("status") == status]
    return rows
