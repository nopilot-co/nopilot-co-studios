"""``assess-commercial-value`` materialiser.

Caller-supplied-JSON materialiser pattern (mirror of the theme-entity /
source-summarise materialisers in the tools tier, and of the `audience
review score` shape). The model produces a structured value-based assessment;
this module validates the schema, stamps provenance, and writes the
assessment into the per-client store.

No model calls live here — judgment lives in the
`assess-commercial-value` skill.
"""

from __future__ import annotations

import json
from pathlib import Path

from .store import write_assessment


def assess_from_file(slug: str, assessment_json: Path) -> dict:
    """Load + materialise a caller-supplied assessment JSON.

    Args:
        slug: the client slug under ``~/context/studios/commercial/clients/``.
        assessment_json: path to the model-produced JSON or YAML file.

    Returns:
        The materialised assessment data (post-validation, with provenance
        stamped).
    """
    text = Path(assessment_json).read_text()
    # Accept either JSON or YAML on input (the SKILL spec uses YAML shape;
    # callers sometimes hand JSON straight from the model).
    if assessment_json.suffix in (".yml", ".yaml"):
        import yaml

        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    return write_assessment(slug, data)
