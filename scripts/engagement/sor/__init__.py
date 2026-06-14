"""Systems-of-record adapters — the docket → external-SoR bridge (Bible §8).

The docket (with its ``engagement.json``, ``ledger.jsonl``, and the
artefact tree) is canonical. The SoR adapter projects a subset of that
state into the user's chosen system of engagement (GitHub Projects by
default; Jira / Linear via additional adapters).

Conflict rule (Bible §8): docket wins on artefacts and decisions; the
SoR wins on human task-status edits. The adapter encodes this in the
sync plan — outbound writes carry a hint so a polite adapter can detect
inbound edits and skip overwrites.
"""

from .base import SoRAdapter, SyncPlan  # noqa: F401
