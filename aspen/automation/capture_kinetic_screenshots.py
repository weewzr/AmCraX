"""Capture genuine Aspen Plus V15 screenshots of kinetic RPLUG cases (research expansion, workstream A).

Opens aspen/models/research/<case_id>.bkp (written by run_kinetic_cases.py) in a visible Aspen session through
the project lock, re-runs it, navigates the GUI with UI Automation (same helpers as capture_screenshots.py, no
mouse/keyboard input to other applications), captures the Aspen window only and writes
docs/images/aspen_evidence/<case_id>__<NN_name>.png plus docs/images/aspen_evidence/manifest.json, which links
every file to its case id.

Privacy: before saving, every UI element whose text contains the Windows user name, the host name or a user
profile path is painted over (grey box); the masked element count is recorded in the manifest.

Usage:  python aspen/automation/capture_kinetic_screenshots.py CASE_ID [CASE_ID ...] [--only NN ...]
"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_screenshots import ASPEN_VERSION, Gui, find_main_window, is_blank, print_window, size_window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "aspen" / "models" / "research"
OUT = ROOT / "docs" / "images" / "aspen_evidence"
MANIFEST = OUT / "manifest.json"
log = logging.getLogger("amcrax.kinetic_screenshots")

# block id: RXR for standalone models, CRACKER for integrated ones (filled in per case)
SPECS: list[dict] = [
    dict(n="01_flowsheet", title="Flowsheet", env="Simulation", flowsheet=True,
         what="Flowsheet of the case (standalone: KFEED -> RXR RPLUG -> KPROD with the RGibbs reference REQ)."),
    dict(n="02_reactions_kinetic", title="Reaction set NH3KIN (GENERAL, power law)", env="Simulation",
         nav=["Reactions", "NH3KIN"], tab=None,
         what="Reaction set NH3KIN: stoichiometry 2 NH3 -> N2 + 3 H2, reversible, power-law class, partial-pressure basis."),
    dict(n="03_reactions_kinetic_tab", title="Kinetic parameters", env="Simulation",
         nav=["Reactions", "NH3KIN"], tab="Kinetic",
         what="Kinetic tab: pre-exponential factor, activation energy, rate basis (catalyst weight), driving-force exponents."),
    dict(n="04_reactor_specifications", title="RPLUG specifications", env="Simulation",
         nav=["Blocks", "{B}", "Setup"], tab="Specifications",
         what="RPLUG reactor type (thermal mode) and temperature or coolant specification."),
    dict(n="05_reactor_configuration", title="RPLUG configuration / geometry", env="Simulation",
         nav=["Blocks", "{B}", "Setup"], tab="Configuration",
         what="Number of tubes, tube length and diameter."),
    dict(n="06_reactor_catalyst", title="RPLUG catalyst", env="Simulation",
         nav=["Blocks", "{B}", "Setup"], tab="Catalyst",
         what="Catalyst present, bed voidage and particle density (catalyst loading)."),
    dict(n="07_reactor_pressure", title="RPLUG pressure", env="Simulation",
         nav=["Blocks", "{B}", "Setup"], tab="Pressure",
         what="Pressure-drop option (none, or Ergun correlation with particle diameter)."),
    dict(n="08_reactor_results", title="RPLUG results", env="Simulation",
         nav=["Blocks", "{B}", "Results"], tab=None,
         what="RPLUG results summary: heat duty, residence time, outlet conditions."),
    dict(n="09_reactor_profiles", title="RPLUG profiles", env="Simulation",
         nav=["Blocks", "{B}", "Profiles"], tab=None,
         what="Axial profiles along the bed (temperature, pressure, composition)."),
    dict(n="10_run_status", title="Run status", env="Simulation",
         nav=["Results Summary", "Run Status"], tab=None,
         what="Run status of the case (completed normally / warnings / errors)."),
    # optional forms (part 2); captured only when named with --only
    dict(n="11_components", title="Component specification", env="Properties", optional=True,
         nav=["Components", "Specifications"], tab="Selection",
         what="Component list (NH3, H2, N2, H2O, O2)."),
    dict(n="12_property_method", title="Property method", env="Properties", optional=True,
         nav=["Methods", "Specifications"], tab="Global",
         what="Global property method (PENG-ROB)."),
    dict(n="13_stream_results", title="Stream results", env="Simulation", optional=True,
         nav=["Results Summary", "Streams"], tab="Material",
         what="Material stream results table of the converged case."),
    dict(n="14_psa_block", title="PSA (Sep) split fractions", env="Simulation", optional=True, integrated_only=True,
         nav=["Blocks", "PSA", "Input"], tab="Specifications",
         what="Purification block PSA (Sep): H2 recovery and N2/NH3 split fractions (integrated flowsheet)."),
]


def _identifiers() -> list[str]:
    ids = [v for v in (getpass.getuser(), socket.gethostname()) if v and len(v) >= 4]
    return [i.lower() for i in ids] + ["\\users\\", "/users/"]


def capture_masked(gui: Gui, path: Path) -> tuple[str, int]:
    """Capture the Aspen window, painting over UI elements whose text holds a personal identifier."""
    import win32gui
    from PIL import ImageDraw

    img = print_window(gui.hwnd)
    if is_blank(img):
        raise RuntimeError("PrintWindow returned a blank image (no fallback capture of the desktop is attempted)")
    l, t, _, _ = win32gui.GetWindowRect(gui.hwnd)
    ids = _identifiers()
    draw, masked = ImageDraw.Draw(img), 0
    title = (win32gui.GetWindowText(gui.hwnd) or "").lower()
    if any(i in title for i in ids):
        draw.rectangle([0, 0, img.width, 32], fill=(128, 128, 128))
        masked += 1
    for e in gui.win.descendants():
        try:
            name = (e.element_info.name or "").lower()
            val = ""
            try:
                val = (e.iface_value.CurrentValue or "").lower()
            except Exception:
                pass
            if any(i in name or i in val for i in ids):
                r = e.element_info.rectangle
                draw.rectangle([r.left - l, r.top - t, r.right - l, r.bottom - t], fill=(128, 128, 128))
                masked += 1
        except Exception:
            continue
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return "win32 PrintWindow(PW_RENDERFULLCONTENT) of the Aspen Plus top-level window, UIA-based masking", masked


def _load() -> dict:
    if MANIFEST.exists():
        try:
            return {e["file"]: e for e in json.loads(MANIFEST.read_text(encoding="utf-8"))["captures"]}
        except Exception:
            pass
    return {}


def _save(entries: dict) -> None:
    MANIFEST.write_text(json.dumps({
        "generated_by": "aspen/automation/capture_kinetic_screenshots.py",
        "aspen_version": ASPEN_VERSION,
        "note": "Real Aspen Plus V15 GUI, model re-run through COM before capture. Personal identifiers masked. "
                "visually_verified is set only after the PNG was inspected.",
        "captures": sorted(entries.values(), key=lambda e: e["file"]),
    }, indent=2), encoding="utf-8")


def capture_case(s, case_id: str, block: str, only=None, rxn_class: str = "") -> dict:
    import time as _t

    hwnd = find_main_window(s._own_pids)
    size_window(hwnd)
    _t.sleep(2)
    gui = Gui(hwnd)
    entries = _load()
    for spec in SPECS:
        if only and not any(spec["n"].startswith(o) for o in only):
            continue
        if spec.get("optional") and not only:
            continue
        if spec.get("integrated_only") and block != "CRACKER":
            continue
        fname = f"{case_id}__{spec['n']}.png"
        nav = [x.replace("{B}", block) for x in spec.get("nav", [])]
        title, what = spec["title"], spec["what"]
        if rxn_class and spec["n"].startswith(("02_", "03_")):
            title = title.replace("power law", rxn_class)
            what = what.replace("power-law class, partial-pressure basis", f"{rxn_class} class")
        e = {"file": fname, "case_id": case_id, "title": title, "what_is_shown": what,
             "navigation_path": " > ".join([spec["env"]] + (nav or ["Main Flowsheet"])) + (f" > {spec['tab']}" if spec.get("tab") else ""),
             "model_file": f"aspen/models/research/{case_id}.bkp", "aspen_version": ASPEN_VERSION,
             "captured_local_time": datetime.now().isoformat(timespec="seconds"), "visually_verified": False}
        try:
            gui.env(spec["env"])
            time.sleep(0.8)
            if spec.get("flowsheet"):
                gui.tab("Main Flowsheet")
                time.sleep(0.5)
                for b in gui.win.descendants(control_type="Button"):
                    if b.element_info.automation_id == "PART_ZoomToFitButton":
                        b.invoke()
            else:
                gui.nav(nav)
                time.sleep(2.5)
                if spec.get("tab"):
                    try:
                        gui.tab(spec["tab"])
                        e["tab_selected"] = True
                    except LookupError:
                        e["tab_selected"] = False
                        e["note"] = f"tab {spec['tab']!r} not found; default tab captured"
            time.sleep(1.5)
            e["capture_method"], e["masked_elements"] = capture_masked(gui, OUT / fname)
            e["status"] = "captured"
        except Exception as exc:
            log.error("%s failed: %s", fname, exc)
            e.update(status="not_captured", reason_if_not=f"automation error: {exc}")
        entries[fname] = e
        _save(entries)
    return entries


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from amcrax.aspen.runner import aspen_lock
    from amcrax.aspen.session import AspenSession

    with aspen_lock():
        with AspenSession(visible=True) as s:
            import shutil

            work = ROOT / "aspen" / "runs" / "screenshots_kinetic"
            work.mkdir(parents=True, exist_ok=True)
            for cid in a.cases:
                bkp = work / f"{cid}.bkp"  # work on a copy: Aspen writes scratch/backup files next to the model
                shutil.copy(MODELS / f"{cid}.bkp", bkp)
                text = (MODELS / f"{cid}.inp").read_text(encoding="ascii")
                block = "CRACKER" if "BLOCK CRACKER RPLUG" in text else "RXR"
                s.open(bkp)
                s.run(timeout_s=300)
                time.sleep(3)
                rxn_class = "LHHW" if "REAC-CLASS=LHHW" in text else "power law"
                ent = capture_case(s, cid, block, a.only, rxn_class)
                print(json.dumps({k: v["status"] for k, v in ent.items() if v["case_id"] == cid}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
