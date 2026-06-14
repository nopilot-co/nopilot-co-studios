"""Autonomy-ladder rules — Bible §6, contract-enforced.

L0 — Gather (research / analyse / read / capture). Autonomous, always.
L1 — Draft (produce internal reversible artefacts, render, validate, score). Autonomous; logged.
L2 — Decide (objectives, scope, value-based price, cast selection, commercial model,
     delivery commitments). **Checkpointed** — a cleared CP-NNN that lists the
     job in ``blocking_jobs[]`` is required before status can move to ``done``.
L3 — Commit / Deliver (send a proposal, email a client, publish, agree a price
     externally). **Hard-gated** — same as L2 plus the cleared Checkpoint must
     carry ``decided_by`` (explicit human authorisation; never automated).

These rules are checked by ``jobs.set_status`` before any status transition
to ``done``. ``AutonomyError`` carries a clear message + the rule that failed
so the caller surfaces the right install hint (e.g. "open a CP for J-NNN").
"""

from __future__ import annotations

ACTION_CLASSES = ("L0", "L1", "L2", "L3")
GATED_CLASSES = {"L2", "L3"}  # require a cleared checkpoint before `done`
HARD_GATED_CLASSES = {"L3"}  # additionally require decided_by on the CP


class AutonomyError(RuntimeError):
    """Raised when an attempted transition violates the autonomy contract."""

    def __init__(self, message: str, *, rule: str, job_id: str | None = None):
        super().__init__(message)
        self.rule = rule
        self.job_id = job_id


def _clears_job(cp: dict, job_id: str) -> bool:
    return job_id in (cp.get("blocking_jobs") or [])


def _cleared_checkpoint_for(data: dict, job_id: str) -> dict | None:
    """Return the first cleared CP that lists ``job_id`` in its blocking_jobs.

    Returns None if no such CP exists.
    """
    for cp in data.get("checkpoints") or []:
        if cp.get("status") == "cleared" and _clears_job(cp, job_id):
            return cp
    return None


def check_transition(data: dict, *, job: dict, new_status: str) -> None:
    """Raise AutonomyError if this transition violates the contract.

    Only the transition to ``done`` is gated. Other transitions
    (``planned`` → ``in-progress``, ``in-progress`` → ``blocked``,
    ``in-progress`` → ``gated``, etc.) are free at every level.
    """
    if new_status != "done":
        return

    ac = job.get("action_class") or "L1"
    if ac not in ACTION_CLASSES:
        raise AutonomyError(
            f"job {job.get('id')} has unknown action_class '{ac}'",
            rule="unknown-action-class",
            job_id=job.get("id"),
        )

    if ac not in GATED_CLASSES:
        return  # L0 / L1 — autonomous

    job_id = job.get("id") or "<unknown>"
    cp = _cleared_checkpoint_for(data, job_id)
    if cp is None:
        raise AutonomyError(
            f"job {job_id} is {ac} — needs a cleared Checkpoint that lists it "
            "in `blocking_jobs[]` before it can move to done. "
            "Open one with `engagement checkpoint open --level "
            f'{ac} --title "..." --blocking {job_id}`.',
            rule="l2-checkpoint-required",
            job_id=job_id,
        )

    if ac in HARD_GATED_CLASSES and not cp.get("decided_by"):
        raise AutonomyError(
            f"job {job_id} is L3 — its cleared Checkpoint ({cp.get('id')}) "
            "must carry `decided_by` (explicit human authorisation). Re-clear "
            "with `engagement checkpoint clear --id "
            f"{cp.get('id')} --decided-by <who>`.",
            rule="l3-human-authorisation-required",
            job_id=job_id,
        )


def autonomy_state(data: dict) -> list[dict]:
    """Per-job autonomy state for the rollup + the `engagement autonomy` CLI.

    Returns one row per job with:
        { id, action_class, status, blocked_by, can_complete }
    where ``blocked_by`` lists the missing condition(s) preventing a
    ``done`` transition (empty when the job can move freely).
    """
    rows = []
    for j in data.get("jobs") or []:
        jid = j.get("id")
        ac = j.get("action_class") or "L1"
        blocked = []
        if ac in GATED_CLASSES and j.get("status") != "done":
            cp = _cleared_checkpoint_for(data, jid)
            if cp is None:
                blocked.append(f"needs cleared CP (level {ac}) listing {jid}")
            elif ac in HARD_GATED_CLASSES and not cp.get("decided_by"):
                blocked.append(
                    f"{cp.get('id')} cleared but missing decided_by (L3 needs human auth)"
                )
        rows.append(
            {
                "id": jid,
                "action_class": ac,
                "status": j.get("status"),
                "blocked_by": blocked,
                "can_complete": not blocked and j.get("status") != "done",
            }
        )
    return rows


def rollup_counts(data: dict) -> dict:
    """Aggregate autonomy counts for the manifest rollup.

    Returns:
        {
            "awaiting_l2": <int>,  # L2 jobs not yet done + no cleared CP
            "awaiting_l3": <int>,  # L3 jobs not yet done + no cleared CP w/ decided_by
            "by_action_class": {"L0": n, "L1": n, "L2": n, "L3": n},
        }
    """
    by_class = {ac: 0 for ac in ACTION_CLASSES}
    awaiting_l2 = 0
    awaiting_l3 = 0
    for row in autonomy_state(data):
        by_class[row["action_class"]] = by_class.get(row["action_class"], 0) + 1
        if row["action_class"] == "L2" and row["blocked_by"]:
            awaiting_l2 += 1
        if row["action_class"] == "L3" and row["blocked_by"]:
            awaiting_l3 += 1
    return {
        "awaiting_l2": awaiting_l2,
        "awaiting_l3": awaiting_l3,
        "by_action_class": by_class,
    }
