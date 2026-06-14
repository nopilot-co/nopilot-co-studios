"""Click entry point for the ``commercial`` CLI.

Subcommands mirror the skills 1:1. Judgment stays in the skills; this is glue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from . import REVIEW_POLICY, __version__, commercial_root
from . import checks as checks_mod
from . import deps as deps_mod
from . import nit_bridge, session, store, value


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="commercial")
def main() -> None:
    """Commercial studio — beancounter (check-commercials) + commercial officer
    (assess-commercial-value)."""


# ----------------------------------------------------------------- doctor


@main.command()
def doctor() -> None:
    """Report studio wiring: nit reachable, store present, policy valid."""
    info = deps_mod.doctor()
    click.echo(yaml.safe_dump(info, sort_keys=False))


# ----------------------------------------------------------------- policy / rate-card


@main.group()
def policy() -> None:
    """Org-wide pricing policy."""


@policy.command("init")
@click.option("--force", is_flag=True, help="overwrite existing files")
def policy_init_cmd(force: bool) -> None:
    """Scaffold rate-card.yml + pricing-policy.yml + configs/checks/. Idempotent."""
    out = store.policy_init(force=force)
    click.echo(
        f"rate-card.yml: {'wrote' if out['rate_card'] else 'kept'}  "
        f"pricing-policy.yml: {'wrote' if out['policy'] else 'kept'}  "
        f"checks: {', '.join(out['checks']) or 'kept'}"
    )
    click.echo(f"location: {commercial_root()}")


@policy.command("show")
def policy_show() -> None:
    if not store.policy_exists():
        _die("no pricing-policy.yml — run `commercial policy init`")
    if not store.rate_card_exists():
        _die("no rate-card.yml — run `commercial policy init`")
    click.echo("# rate-card.yml")
    click.echo(yaml.safe_dump(store.read_rate_card(), sort_keys=False))
    click.echo("# pricing-policy.yml")
    click.echo(yaml.safe_dump(store.read_policy(), sort_keys=False))


@main.group("rate-card")
def rate_card() -> None:
    """Org-wide rate card."""


@rate_card.command("show")
def rate_card_show() -> None:
    if not store.rate_card_exists():
        _die("no rate-card.yml — run `commercial policy init`")
    click.echo(yaml.safe_dump(store.read_rate_card(), sort_keys=False))


@rate_card.command("validate")
def rate_card_validate() -> None:
    errs = store.validate_rate_card()
    if errs:
        for e in errs:
            click.echo(f"✗ {e}", err=True)
        sys.exit(2)
    click.echo("✓ rate-card.yml valid")


# ----------------------------------------------------------------- client


@main.group()
def client() -> None:
    """Per-client store: financial profile + research + assessment."""


@client.command("new")
@click.option("--client", "slug", required=True, help="client slug (kebab-case)")
@click.option("--name", help="friendly name")
def client_new(slug: str, name: str | None) -> None:
    try:
        data = store.scaffold_client(slug, name=name)
    except ValueError as e:
        _die(str(e))
    click.echo(f"scaffolded client '{slug}' at {store.client_dir(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


@client.command("show")
@click.option("--client", "slug", required=True)
def client_show(slug: str) -> None:
    try:
        data = store.read_client(slug)
    except FileNotFoundError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(data, sort_keys=False))


@client.command("list")
def client_list() -> None:
    rows = store.list_clients()
    click.echo("\n".join(rows) if rows else "(no clients yet)")


# ----------------------------------------------------------------- research


@main.group()
def research() -> None:
    """File research sources under a client."""


@research.command("add")
@click.option("--client", "slug", required=True)
@click.option("--source", "src", required=True, help="path or URL of the source")
@click.option("--kind", default="doc", type=click.Choice(["doc", "transcript", "url"]))
def research_add(slug: str, src: str, kind: str) -> None:
    if not store.client_exists(slug):
        _die(f"no client '{slug}' — run `commercial client new --client {slug}`")
    sources_dir = store.client_dir(slug) / "research" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    if kind == "url":
        # store as a one-line .url stub; the skill will fetch / review
        stub = sources_dir / (Path(src).name or "source.url")
        stub.write_text(f"{src}\n")
        click.echo(f"filed URL stub: {stub}")
    else:
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            _die(f"source file not found: {src_path}")
        dest = sources_dir / src_path.name
        dest.write_bytes(src_path.read_bytes())
        click.echo(f"filed {kind}: {dest}")
    # provenance: append to the client model
    data = store.read_client(slug)
    data.setdefault("provenance", {}).setdefault("sources", []).append(
        {"source": src, "kind": kind}
    )
    store.write_client(slug, data)


# ----------------------------------------------------------------- checks (rubric)


@main.group()
def checks() -> None:
    """The deterministic check rubric (lives in configs/checks/)."""


@checks.command("list")
def checks_list() -> None:
    path = commercial_root() / "configs" / "checks"
    if not path.is_dir():
        click.echo("(no checks rubric — run `commercial policy init`)")
        return
    rubric = checks_mod.load_checks_dir(path)
    for r in rubric:
        click.echo(
            f"{r.get('id', '?'):<24}  gate={r.get('gate', False)!s:<5}  "
            f"weight={r.get('weight', '?')}  — {r.get('summary', '')}"
        )


@checks.command("show")
@click.option("--check", "cid", required=True)
def checks_show(cid: str) -> None:
    path = commercial_root() / "configs" / "checks"
    if not path.is_dir():
        _die("no checks rubric — run `commercial policy init`")
    for r in checks_mod.load_checks_dir(path):
        if r.get("id") == cid:
            click.echo(yaml.safe_dump(r, sort_keys=False))
            return
    _die(f"no check '{cid}' under {path}")


# ----------------------------------------------------------------- check (review session)


@main.group()
def check() -> None:
    """Per-deal check-commercials review sessions."""


@check.command("new")
@click.option("--deal-slug", "slug", required=True)
@click.option(
    "--deal-file", required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.option("--brief", type=click.Path(exists=True, dir_okay=False))
def check_new(slug: str, deal_file: str, brief: str | None) -> None:
    try:
        data = session.new(
            slug, deal_file=Path(deal_file), brief=Path(brief) if brief else None
        )
    except ValueError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(data, sort_keys=False))


@check.command("score")
@click.option("--deal-slug", "slug", required=True)
@click.option("--bump", default="patch", type=click.Choice(["patch", "minor", "major"]))
def check_score(slug: str, bump: str) -> None:
    """Evaluate the rubric + hand to `nit aggregate` for the verdict."""
    if not session.exists(slug):
        _die(
            f"no session '{slug}' — run "
            f"`commercial check new --deal-slug {slug} --deal-file <path>`"
        )
    rc_errs = store.validate_rate_card()
    pol_errs = store.validate_policy()
    if rc_errs or pol_errs:
        for e in rc_errs + pol_errs:
            click.echo(f"✗ {e}", err=True)
        _die("policy not ready", code=2)
    deal = session.read_deal(slug)
    rate_card_data = store.read_rate_card()
    policy_data = store.read_policy()
    results = checks_mod.evaluate(deal, rate_card_data, policy_data)
    scores = checks_mod.to_scores_yaml(results)
    version = session.bump(slug, level=bump)
    scores_path = session.write_scores(slug, scores)
    checks_dir = commercial_root() / "configs" / "checks"

    if nit_bridge.reachable():
        # `nit aggregate --tests-from` takes a single file; assemble the
        # configs/checks/*.yaml into one in-memory rubric, write to a temp
        # file under the session, and hand that to the engine. This is the
        # commercial-side analogue of audience/rubric.yml.
        rubric_path = session.review_dir(slug) / "rubric.yml"
        rubric = _assemble_rubric(checks_dir)
        rubric_path.write_text(yaml.safe_dump(rubric, sort_keys=False))
        try:
            scorecard = nit_bridge.aggregate(
                scores_path,
                rubric_path,
                policy=REVIEW_POLICY if REVIEW_POLICY.is_file() else None,
            )
            session.write_scorecard(slug, scorecard)
            click.echo(
                f"v{version}: scored via nit aggregate → {session.review_dir(slug)}/scorecard.json"
            )
        except (FileNotFoundError, RuntimeError) as e:
            # Fallback: a local minimum verdict so the studio remains usable
            # when nit isn't installed. The skill should still narrate.
            local = _local_verdict(results)
            session.write_scorecard(slug, local)
            click.echo(
                f"v{version}: scored locally (nit unavailable: {e}) "
                f"→ {session.review_dir(slug)}/scorecard.json"
            )
    else:
        local = _local_verdict(results)
        session.write_scorecard(slug, local)
        click.echo(
            f"v{version}: scored locally (nit not on PATH) "
            f"→ {session.review_dir(slug)}/scorecard.json"
        )

    # Echo a one-line summary.
    sc = json.loads(session.review_dir(slug).joinpath("scorecard.json").read_text())
    gates_failed = sc.get("gates_failed") or []
    gate_items = [i for i in sc.get("items", []) if i.get("gate")]
    click.echo(
        f"verdict: {sc.get('verdict', 'unknown')}  overall: {sc.get('overall', '?')}  "
        f"gates: {len(gate_items) - len(gates_failed)}/{len(gate_items)} pass"
        + (f"  failed: {', '.join(gates_failed)}" if gates_failed else "")
    )


@check.command("status")
@click.option("--deal-slug", "slug", required=True)
@click.option("--set", "new_status", help="new status")
def check_status(slug: str, new_status: str | None) -> None:
    if new_status:
        data = session.set_status(slug, new_status)
        click.echo(yaml.safe_dump(data, sort_keys=False))
        return
    if not session.exists(slug):
        _die(f"no session '{slug}'")
    click.echo(json.dumps(json.loads(session.version_path(slug).read_text()), indent=2))


def _assemble_rubric(checks_dir) -> dict:
    """Combine configs/checks/*.yaml into a single nit-rubric document.

    Mirrors the audience studio's per-reader ``rubric.yml`` shape (one
    ``tests:`` array + ``gates:`` for the critical checks), so ``nit
    aggregate --tests-from`` can score against the same math + policy.
    """
    items = checks_mod.load_checks_dir(checks_dir)
    tests = []
    gates = []
    for r in items:
        cid = r.get("id")
        if not cid:
            continue
        if r.get("gate"):
            gates.append(cid)
        tests.append(
            {
                "test": cid,
                "name": r.get("summary", cid).rstrip("."),
                "question": (r.get("question") or "").strip(),
                "dimension": "commercials",
                "scale": {"min": 1, "max": 5},
                "criteria": [
                    {"label": k, "description": v}
                    for k, v in (r.get("scale") or {}).items()
                ],
                "weight": float(r.get("weight", 1.0)),
            }
        )
    return {"tests": tests, "gates": gates}


def _local_verdict(results: list[dict]) -> dict:
    """Compute a minimal verdict when the nitpicker engine isn't available.

    Mirror of the engine's contract: critical-gate failures override; otherwise
    weighted average → band. Bands are conservative.
    """
    # Treat rate-card-compliance + margin-floor as gates; ratio-mix advisory.
    gates = {"rate-card-compliance", "margin-floor"}
    gate_results = [r for r in results if r["id"] in gates]
    failed = [r for r in gate_results if not r["passed"]]
    avg = sum(r["score"] for r in results) / max(1, len(results))
    if failed:
        verdict = "fail"
    elif avg >= 4.5:
        verdict = "pass"
    elif avg >= 3.5:
        verdict = "revise"
    else:
        verdict = "fail"
    return {
        "verdict": verdict,
        "passed_gates": len(gate_results) - len(failed),
        "total_gates": len(gate_results),
        "score_avg": avg,
        "checks": results,
        "engine": "local-fallback (nit not reachable)",
    }


# ----------------------------------------------------------------- value


@main.group()
def value_cmd() -> None:  # group named ``value`` via add_command below
    """Materialise the commercial officer's value-based assessment."""


# Click rejects ``value`` as a group name when a module-level symbol collides;
# we add it under its CLI name explicitly:
value_cmd.name = "value"
main.add_command(value_cmd)


@value_cmd.command("assess")
@click.option("--client", "slug", required=True)
@click.option(
    "--assessment-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="model-produced assessment (JSON or YAML; schema in the SKILL)",
)
def value_assess(slug: str, assessment_json: str) -> None:
    try:
        data = value.assess_from_file(slug, Path(assessment_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(f"wrote {store.assessment_path(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


if __name__ == "__main__":
    main()
