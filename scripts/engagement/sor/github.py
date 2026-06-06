"""GitHub Projects adapter — the docket → GitHub Projects bridge (Bible §8).

Mapping (one-way default; conflict rule per Bible §8):

| Docket entity          | GitHub Projects entity                                |
|------------------------|-------------------------------------------------------|
| engagement             | Project                                               |
| job (J-NNN)            | Issue / card; status column = job.status              |
| question (Q-NNN)       | Issue labelled `question`; assignee = needs (when role) |
| blocker (B-NNN)        | Issue labelled `blocked`                              |
| risk (R-NNN)           | Issue labelled `risk`                                 |
| decision (D-NNN)       | Linked comment + ADR file pointer                     |
| checkpoint (CP-NNN)    | Check / status label tied to the blocking job(s)      |
| gate verdict           | Check (pass / revise / fail)                          |

v0.1.0 produces the plan structurally — full ``gh`` shell-out wiring is
a follow-up. The plan is the load-bearing contract here: a CI / cron
can ``apply_plan(dry_run=False)`` once the live writes are wired.
"""

from __future__ import annotations

from .base import SoRAdapter, SyncAction, SyncPlan

ISSUE_STATUS_COLUMN = {
    "planned": "Planned",
    "briefed": "Briefed",
    "in-progress": "In Progress",
    "blocked": "Blocked",
    "gated": "Gated",
    "done": "Done",
}


class GitHubProjectsAdapter(SoRAdapter):
    name = "github-projects"

    def __init__(self, *, owner: str | None = None, project_name: str | None = None):
        self.owner = owner
        self.project_name = project_name

    def build_sync_plan(self, manifest: dict) -> SyncPlan:
        engagement = manifest.get("engagement") or "<unknown>"
        plan = SyncPlan(engagement=engagement, adapter=self.name)

        # 1. Project itself
        title = self.project_name or f"engagement: {engagement}"
        plan.actions.append(
            SyncAction(
                op="create-if-absent",
                target="project",
                payload={
                    "title": title,
                    "owner": self.owner,
                    "description": (manifest.get("brief") or {}).get("objective", ""),
                },
            )
        )

        # 2. Jobs → issues / cards
        for j in manifest.get("jobs") or []:
            jid = j.get("id")
            plan.actions.append(
                SyncAction(
                    op="upsert-issue",
                    target=f"issue:{jid}",
                    payload={
                        "title": j.get("title") or j.get("capability"),
                        "body": _job_body(j),
                        "labels": [
                            "job",
                            f"action-class:{j.get('action_class', 'L1')}",
                        ],
                    },
                )
            )
            plan.actions.append(
                SyncAction(
                    op="status_move",
                    target=f"issue:{jid}",
                    payload={
                        "column": ISSUE_STATUS_COLUMN.get(j.get("status"), "Planned"),
                        # Inbound-conflict hint: skip the move if the SoR shows a
                        # newer human edit on this card's status.
                        "respect_inbound_edit": True,
                    },
                )
            )

        # 3. Questions / Blockers / Risks → labelled issues
        for kind, lst, label in (
            ("question", manifest.get("questions") or [], "question"),
            ("blocker", manifest.get("blockers") or [], "blocked"),
            ("risk", manifest.get("risks") or [], "risk"),
        ):
            for it in lst:
                iid = it.get("id")
                plan.actions.append(
                    SyncAction(
                        op="upsert-issue",
                        target=f"issue:{iid}",
                        payload={
                            "title": it.get("title"),
                            "body": _item_body(it),
                            "labels": [label, f"status:{it.get('status', 'open')}"],
                            "needs": it.get("needs"),
                        },
                    )
                )

        # 4. Decisions → comments on the engagement project
        for d in manifest.get("decisions") or []:
            plan.actions.append(
                SyncAction(
                    op="comment",
                    target="project",
                    payload={
                        "subject": d.get("id"),
                        "title": d.get("title"),
                        "ref": d.get("ref"),
                        "role": d.get("role"),
                        "summary": d.get("summary"),
                    },
                )
            )

        # 5. Checkpoints → checks tied to the blocking jobs
        for cp in manifest.get("checkpoints") or []:
            for jid in cp.get("blocking_jobs") or [cp.get("id")]:
                plan.actions.append(
                    SyncAction(
                        op="check",
                        target=f"issue:{jid}",
                        payload={
                            "checkpoint": cp.get("id"),
                            "level": cp.get("level"),
                            "name": cp.get("title"),
                            "conclusion": _cp_conclusion(cp),
                            "decided_by": cp.get("decided_by"),
                        },
                    )
                )

        # Conflict-rule note for the operator.
        plan.notes.append(
            "Conflict rule: this plan writes outbound; for any issue whose "
            "card column has been moved by a human in GitHub since the last "
            "sync, the `status_move` action will skip per `respect_inbound_edit`. "
            "Inbound sync is opt-in (`engagement sync github --inbound`)."
        )
        return plan


def _job_body(job: dict) -> str:
    return (
        f"capability: {job.get('capability')}\n"
        f"role: {job.get('role') or '-'}\n"
        f"action_class: {job.get('action_class', 'L1')}\n"
    )


def _item_body(item: dict) -> str:
    parts = [f"kind: {item.get('kind')}", f"status: {item.get('status')}"]
    if item.get("needs"):
        parts.append(f"needs: {item['needs']}")
    if item.get("blocking_jobs"):
        parts.append(f"blocking_jobs: {', '.join(item['blocking_jobs'])}")
    if item.get("resolution"):
        parts.append(f"resolution: {item['resolution']}")
    return "\n".join(parts)


def _cp_conclusion(cp: dict) -> str:
    if cp.get("status") == "cleared":
        return "success"
    if cp.get("status") == "declined":
        return "failure"
    return "neutral"
