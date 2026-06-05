#!/usr/bin/env python3
"""observability + SoR (#95) — ledger.jsonl + GitHubProjectsAdapter sync plan.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_observability_sor.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from engagement import (  # noqa: E402
    checkpoints as cp_mod,
    decisions as dec_mod,
    items as items_mod,
    jobs as jobs_mod,
    ledger,
    manifest as man,
)
from engagement.sor.github import GitHubProjectsAdapter  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    man.new(root, engagement_slug="demo", objective="Test the observability spine")

    # Ledger starts empty before any mutation that wires through.
    initial = ledger.read(root)
    check("ledger starts empty (manifest.new doesn't append)", initial == [])

    # Each tracked mutation appends one event.
    j1 = jobs_mod.add(root, capability="render-asset", role="design", title="deck")
    j2 = jobs_mod.add(
        root, capability="check-commercials", role="commercial", action_class="L2"
    )

    events = ledger.read(root)
    check(
        "ledger has 2 job.add events",
        sum(1 for e in events if e["kind"] == "job.add") == 2,
    )
    check(
        "first event subject = J-001",
        events[0]["kind"] == "job.add" and events[0]["subject"] == j1["id"],
    )
    check(
        "event carries actor (role)",
        events[0]["actor"] == "design",
    )
    check(
        "event details capture action_class",
        events[1]["details"]["action_class"] == "L2",
    )

    jobs_mod.set_status(root, job_id=j1["id"], status="in-progress")
    jobs_mod.set_status(root, job_id=j1["id"], status="done")
    events = ledger.read(root)
    set_status_events = [e for e in events if e["kind"] == "job.set_status"]
    check("2 job.set_status events", len(set_status_events) == 2)
    check(
        "set_status event captures transition",
        set_status_events[-1]["details"]["previous"] == "in-progress"
        and set_status_events[-1]["details"]["status"] == "done",
    )

    # First-class items
    q1 = items_mod.add(
        root,
        kind="question",
        title="deck or doc?",
        raised_by_role="principal",
        needs="user",
    )
    events = ledger.read(root)
    q_add = [e for e in events if e["kind"].startswith("item.add.")]
    check(
        "item.add.question event", any(e["kind"] == "item.add.question" for e in q_add)
    )
    check("item event carries subject Q-001", q_add[-1]["subject"] == q1["id"])

    items_mod.resolve(root, kind="question", item_id=q1["id"], resolution="deck")
    events = ledger.read(root)
    check(
        "item.resolve event",
        any(e["kind"] == "item.resolve.question" for e in events),
    )

    # Checkpoint + clear
    cp1 = cp_mod.open_checkpoint(
        root, level="L2", title="Confirm scope", blocking_jobs=[j2["id"]]
    )
    cp_mod.clear(root, checkpoint_id=cp1["id"], outcome="Approved", decided_by="user")
    events = ledger.read(root)
    cp_events = [e for e in events if e["kind"].startswith("checkpoint.")]
    check(
        "checkpoint open + clear logged",
        any(e["kind"] == "checkpoint.open" for e in cp_events)
        and any(e["kind"] == "checkpoint.clear" for e in cp_events),
    )

    # Decisions
    dec_mod.add(root, title="value-based price band £75k-£250k", role="commercial")
    events = ledger.read(root)
    check(
        "decision.add event",
        any(e["kind"] == "decision.add" for e in events),
    )

    # show() with filters
    only_jobs = ledger.show(root, kind="job.add")
    check("ledger.show kind filter", all(e["kind"] == "job.add" for e in only_jobs))
    only_j1 = ledger.show(root, subject=j1["id"])
    check(
        "ledger.show subject filter",
        all(e.get("subject") == j1["id"] for e in only_j1),
    )

    # Ledger file is valid JSONL
    raw = ledger.path_for(root).read_text().splitlines()
    check(
        "every line is valid JSON",
        all(json.loads(line) for line in raw if line.strip()),
    )

    # ============= SoR bridge — GitHubProjectsAdapter =============

    adapter = GitHubProjectsAdapter(owner="nopilot-co", project_name="Demo Engagement")
    plan = adapter.build_sync_plan(man.read(root))

    check("plan engagement = demo", plan.engagement == "demo")
    check("plan adapter = github-projects", plan.adapter == "github-projects")

    actions = plan.actions
    ops = [a.op for a in actions]
    check("plan creates the project", "create-if-absent" in ops)
    check("plan has upsert-issue for each job", ops.count("upsert-issue") >= 2)
    check("plan has status_move actions for jobs", "status_move" in ops)
    check("plan has comment actions for decisions", "comment" in ops)
    check("plan has check actions for checkpoints", "check" in ops)

    # Job → issue mapping
    issue_targets = {a.target for a in actions if a.op == "upsert-issue"}
    check(f"issue:{j1['id']} present", f"issue:{j1['id']}" in issue_targets)
    check(f"issue:{j2['id']} present", f"issue:{j2['id']}" in issue_targets)

    # Q-001 also gets a labelled issue (`question`)
    q_action = next(
        (
            a
            for a in actions
            if a.op == "upsert-issue" and a.target == f"issue:{q1['id']}"
        ),
        None,
    )
    check("Q-001 mapped to a labelled issue", q_action is not None)
    if q_action:
        check(
            "Q-001 label includes 'question'", "question" in q_action.payload["labels"]
        )

    # Status move respects inbound edits
    sm = [a for a in actions if a.op == "status_move"]
    check(
        "status_move actions carry respect_inbound_edit",
        all(a.payload.get("respect_inbound_edit") for a in sm),
    )

    # Conflict-rule note recorded
    check(
        "plan includes the conflict-rule note",
        any("Conflict rule" in n for n in plan.notes),
    )

    # plan.to_dict shape
    pd = plan.to_dict()
    check("plan dict has action_count", pd["action_count"] == len(actions))
    check("plan dict has actions list", isinstance(pd["actions"], list))
    check("plan dict has notes", "notes" in pd)

    # Dry-run apply
    result = adapter.apply_plan(plan, dry_run=True)
    check("apply dry_run returns adapter name", result["adapter"] == "github-projects")
    check("apply dry_run lists would_apply", len(result["would_apply"]) == len(actions))

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: observability + SoR (ledger appends across job/item/checkpoint/decision mutations; jsonl round-trip; show filters; GitHubProjectsAdapter plan covers project/jobs/items/decisions/checkpoints with respect_inbound_edit + conflict-rule note)"
)
