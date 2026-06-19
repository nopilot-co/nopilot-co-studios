"""Render the 360-gtm-proposition docket → native gslide payload, MANIFEST-NATIVE.

The deck's brand expression (tone rhythm, colour-split eyebrows, cover, contents,
part dividers) comes from the docket manifest via `gslide.build_requests`; this
driver only supplies the 360 *viz map* (the data-backed graphics) since those are
docket-specific. Run from anywhere:

    python design/uds/examples/render_360.py            # uses the default docket path
    DOCKET_360=/path/to/360-gtm-proposition/source python design/uds/examples/render_360.py

Then push with:  python -m studio.gslide --execute --account npt \
                    --payload design/uds/examples/_360-longform-full.gslide.json \
                    --presentation-id <PID>

NOTE: the docket source lives in the sibling `nopilot-co-www` repo. Wiring this
into `studio render` (viz specs carried by the docket itself) is the remaining
#129 follow-up; until then this driver is the reproducible generator.
"""
import os
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # design/uds/examples/ → repo root
sys.path.insert(0, str(REPO / "design" / "scripts"))
from studio import gslide  # noqa: E402

DEFAULT_DOCKET = Path.home() / "Projects/aqua/nopilot-co-www/assets/dockets/360-gtm-proposition/source"
DOCKET = Path(os.environ.get("DOCKET_360", str(DEFAULT_DOCKET)))
MANI = DOCKET / "content" / "manifest.yaml"
DATA = DOCKET / "content" / "data"
OUT = REPO / "design" / "uds" / "examples" / "_360-longform-full.gslide.json"

if not MANI.exists():
    sys.exit(f"docket manifest not found: {MANI}\nset DOCKET_360 to the 360-gtm-proposition/source path")


def _k(n):  # GBP → £k, rounded
    return round(float(n) / 1000)


# --- commercials: bar chart from financials.csv (Revenue / Exit ARR / EBIT, £k) ---
fin = {r["metric"]: r for r in csv.DictReader((DATA / "financials.csv").open(encoding="utf-8"))}
yr = lambda m: [_k(fin[m]["Year1"]), _k(fin[m]["Year2"]), _k(fin[m]["Year3"])]
exit_arr = [_k(float(fin["Exit MRR"]["Year1"]) * 12), _k(float(fin["Exit MRR"]["Year2"]) * 12), _k(float(fin["Exit MRR"]["Year3"]) * 12)]
chart_spec = {"title": "Three years on one model (GBP k)", "type": "bar", "x": ["Year 1", "Year 2", "Year 3"],
              "series": [{"name": "Revenue", "y": yr("Revenue")}, {"name": "Exit ARR", "y": exit_arr}, {"name": "EBIT", "y": yr("EBIT")}]}

# --- landscape: hype-cycle from timeline.csv (one well-spaced milestone per phase) ---
PHASE = {"innovation-trigger": "Trigger", "peak-of-expectations": "Peak", "trough-of-disillusionment": "Trough",
         "slope-of-enlightenment": "Slope", "plateau-of-productivity": "Plateau"}
rows = list(csv.DictReader((DATA / "timeline.csv").open(encoding="utf-8")))
points = []
for ph in ["innovation-trigger", "peak-of-expectations", "trough-of-disillusionment", "slope-of-enlightenment", "plateau-of-productivity"]:
    cand = [r for r in rows if r.get("phase") == ph and r.get("event")]
    if not cand:
        continue
    cand.sort(key=lambda r: (0 if r.get("stat") else 1, len(r["event"])))
    r = cand[0]
    ev = r["event"].split("(")[0].split(";")[0]
    for pre in ("OpenAI ", "Anthropic ", "Google ", "Meta ", "Mistral "):
        ev = ev.replace(pre, "")
    points.append({"label": " ".join(ev.split()[:3]), "phase": PHASE[ph], "tooltip": (r.get("stat") or "").strip()[:80]})
hype_spec = {"title": "The commercial-AI hype cycle, 2022-2027", "phases": ["Trigger", "Peak", "Trough", "Slope", "Plateau"], "points": points}

# --- authored structural viz (tech bullseye, structure swimlane + figure, section figures) ---
bullseye_spec = {"rings": [
    {"ring": "PBOS", "items": ["Platform business operating system"]},
    {"ring": "Scaled context to code", "items": ["Reusable patterns and assets"]},
    {"ring": "Customer systems of record", "items": ["Where the work already lives"]},
    {"ring": "Infrastructure pillars", "items": ["Cloud, identity, governance"]}]}
swimlane_spec = {"months": ["Now", "Sep 2026", "Jan 2027", "Apr 2027"], "lanes": [
    {"name": "Commercial / sales", "stages": ["Pipeline and lunch-and-learns", "Priced rungs in market", "Repeatable sales motion"]},
    {"name": "Delivery", "stages": ["Templates and first method", "First engagements delivered", "Productised delivery at pace"]},
    {"name": "Tech / BOS", "stages": ["BOS prototype", "BOS in live use", "BOS as the platform"]},
    {"name": "Fin-ops / legal", "stages": ["Entity contracts and banking", "Billing and cash discipline", "Forecasting and reporting"]}],
    "milestones": [{"at": "Apr 2027", "label": "A business that runs"}]}
img = lambda src, cap: {"src": src, "caption": cap}

VIZ = {
    "commercials": {"kind": "chart", "spec": chart_spec, "title": chart_spec["title"]},
    "landscape": {"kind": "hype-cycle", "spec": hype_spec, "title": hype_spec["title"]},
    "tech": {"kind": "bullseye", "spec": bullseye_spec, "title": "The dartboard"},
    "structure": [{"kind": "diagram", "spec": swimlane_spec, "title": "A first business that runs"},
                  {"kind": "image", "spec": img("viz/lean-core.svg", "Operating structure - a small fixed core that carries none of the weight (0 employees, 0 offices, 0 assets, 0 creditors).")}],
    "pillars": {"kind": "image", "spec": img("viz/pillars.svg", "Four pillars - adoption starts with understanding, lasts with structure, and turns into a business by selling through the work.")},
    "model": {"kind": "image", "spec": img("viz/model.svg", "The shape of the business - a lean core that grows sideways through partners, not payroll.")},
    "gtm": {"kind": "image", "spec": img("viz/economics.svg", "Founder economics - from a job you own (1:1 draw) to a margin engine that pays you.")},
}

if __name__ == "__main__":
    title, reqs = gslide.build_requests(MANI, brand="360", profile="proposal", viz=VIZ)
    pl = {"title": title, "slides": sum(1 for r in reqs if "createSlide" in r),
          "requests": [r for r in reqs if "_studio_image" not in r]}
    OUT.write_text(json.dumps(pl, indent=2), encoding="utf-8")
    print(f"hype points: {len(points)} | gslide: {pl['slides']} slides, {len(pl['requests'])} requests → {OUT.relative_to(REPO)}")
