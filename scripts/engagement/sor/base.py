"""SoR adapter base + plan dataclasses.

An adapter:
1. Takes the engagement manifest (Python dict).
2. Produces a ``SyncPlan`` — a structured description of what would
   happen to the SoR if the plan were applied.
3. Optionally applies the plan (live or dry-run).

The plan is the contract. v0.1.0 ships the plan-side of every adapter
plus dry-run application; live writes are a follow-up per adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SyncAction:
    """One action in a sync plan."""

    op: str  # "create" | "update" | "status_move" | "label" | "check" | "comment"
    target: str  # e.g. "project" | "issue:J-001" | "issue:Q-001"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncPlan:
    """Structured plan the adapter would apply."""

    engagement: str
    adapter: str
    actions: list[SyncAction] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "engagement": self.engagement,
            "adapter": self.adapter,
            "action_count": len(self.actions),
            "actions": [
                {"op": a.op, "target": a.target, "payload": a.payload}
                for a in self.actions
            ],
            "conflicts": self.conflicts,
            "notes": self.notes,
        }


class SoRAdapter(ABC):
    """Abstract base. Concrete adapters implement ``build_sync_plan`` and
    optionally ``apply_plan``."""

    name: str = "base"

    @abstractmethod
    def build_sync_plan(self, manifest: dict) -> SyncPlan:
        """Inspect the manifest; return what would happen to the SoR."""

    def apply_plan(self, plan: SyncPlan, *, dry_run: bool = True) -> dict:
        """Apply the plan. Base impl is dry-run only — concrete adapters
        override to make live calls."""
        return {
            "adapter": self.name,
            "applied": [] if dry_run else [],
            "skipped": [],
            "dry_run": dry_run,
            "would_apply": [a.op + ":" + a.target for a in plan.actions],
        }
