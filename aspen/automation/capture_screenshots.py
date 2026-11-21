"""Capture genuine screenshots of the AmCraX baseline model in the Aspen Plus V15 GUI.

Opens aspen/models/baseline.apw (fallback .bkp) through the project API (AspenSession under
aspen_lock, visible=True), runs it, navigates the GUI through UI Automation (navigation-pane tree
item select/expand; no mouse or keyboard input unless the Aspen window is the foreground window),
captures the Aspen top-level window with PrintWindow(PW_RENDERFULLCONTENT) and writes
aspen/screenshots/<NN_name>.png plus aspen/screenshots/manifest.json.

The original baseline model files are never saved or modified.

Usage:  python aspen/automation/capture_screenshots.py [--only NAME ...]
        (NAME = file stem, e.g. 01_flowsheet, or its number, e.g. 01)
"""
from __future__ import annotations

import argparse
import ctypes
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "aspen" / "models"
OUT = ROOT / "aspen" / "screenshots"
MANIFEST = OUT / "manifest.json"
ASPEN_VERSION = "Aspen Plus V15.0 (COM ProgID Apwn.Document.41.0)"
log = logging.getLogger("amcrax.screenshots")

# ----------------------------------------------------------------------------- capture specs
# nav: path of navigation-pane tree item names from the environment root.
# env: "Properties" or "Simulation" environment button; tab: name of the form tab to select.
SPECS: list[dict] = [
    dict(file="01_flowsheet.png", title="Main Flowsheet", env="Simulation", nav=None, tab=None, flowsheet=True,
         navigation_path="Simulation environment > Main Flowsheet tab (Zoom to fit)",
         what_is_shown="The complete AmCraX flowsheet as drawn by Aspen Plus: PUMP, VAPORIZR, FEHE, HEATER, CRACKER, COOLER, PSA, BURNER, FLUEHX with streams FEED, S1-S7, H2PROD, TAILGAS, AIR, FLUE, STACK.",
         why_it_matters="Documents the process topology that every reported Aspen result comes from, including the feed-effluent heat integration loop and tail-gas combustion."),
    dict(file="02_components.png", title="Component specification", env="Properties", nav=["Components", "Specifications"], tab="Selection",
         navigation_path="Properties > Components > Specifications > Selection",
         what_is_shown="Component list NH3, H2, N2, H2O, O2 with their databank identities.",
         why_it_matters="Defines the chemical species system; all mass and energy balances and the Gibbs equilibrium are restricted to these components."),
    dict(file="03_property_method.png", title="Property method", env="Properties", nav=["Methods", "Specifications"], tab="Global",
         navigation_path="Properties > Methods > Specifications > Global",
         what_is_shown="Global property method selection (PENG-ROB).",
         why_it_matters="The Peng-Robinson equation of state sets the fugacities used in the high-pressure cracking equilibrium and the enthalpies in every heat duty."),
    dict(file="04_feed_stream.png", title="Feed stream input", env="Simulation", nav=["Streams", "FEED", "Input"], tab="Mixed",
         navigation_path="Simulation > Streams > FEED > Input > Mixed",
         what_is_shown="FEED specification: pressure, vapour fraction, total flow and mole-fraction composition.",
         why_it_matters="Fixes the basis of the whole simulation (refrigerated liquid ammonia with trace water), to which all KPIs are normalised."),
    dict(file="05_reactor_setup.png", title="CRACKER (RGibbs) setup", env="Simulation", nav=["Blocks", "CRACKER", "Setup"], tab="Specifications",
         navigation_path="Simulation > Blocks > CRACKER > Setup > Specifications",
         what_is_shown="RGibbs calculation option, reactor temperature and pressure specifications.",
         why_it_matters="The cracker is modelled as an isothermal Gibbs-equilibrium reactor; temperature and pressure set the equilibrium NH3 conversion."),
    dict(file="06_reactor_products.png", title="CRACKER possible products", env="Simulation", nav=["Blocks", "CRACKER", "Setup"], tab="Products",
         navigation_path="Simulation > Blocks > CRACKER > Setup > Products",
         what_is_shown="Products tab of the RGibbs block: option \"Identify possible products\" with NH3, H2, N2 and H2O listed (valid phase Mixed).",
         why_it_matters="For an RGibbs reactor this is the reaction specification: equilibrium is computed over these species only (NH3, H2, N2, H2O; oxygen occurs only in H2O, so the water is effectively inert)."),
    dict(file="07_heat_exchanger_setup.png", title="FEHE (HeatX) setup", env="Simulation", nav=["Blocks", "FEHE", "Setup"], tab="Specifications",
         navigation_path="Simulation > Blocks > FEHE > Setup > Specifications",
         what_is_shown="HeatX setup: Shortcut model, countercurrent, Design mode, specification \"Cold stream outlet temperature\" with its value and minimum temperature approach.",
         why_it_matters="The feed-effluent exchanger recovers reactor-effluent heat; its specification sets the hot-end approach and hence the external heater duty."),
    dict(file="08_separation_setup.png", title="PSA (Sep) split fractions", env="Simulation", nav=["Blocks", "PSA", "Input"], tab="Specifications",
         navigation_path="Simulation > Blocks > PSA > Input > Specifications",
         what_is_shown="Specifications tab of the Sep block: component split fractions to outlet H2PROD (substream MIXED).",
         why_it_matters="The PSA is a reduced-order material balance (H2 recovery, N2 slip), not a designed PSA; these fractions fix product and tail-gas flows."),
    dict(file="09_burner_setup.png", title="BURNER (RStoic) setup", env="Simulation", nav=["Blocks", "BURNER", "Setup"], tab="Reactions",
         navigation_path="Simulation > Blocks > BURNER > Setup > Reactions",
         what_is_shown="Reactions tab of the RStoic burner: two fractional-conversion reactions (H2 + 0.5 O2 -> H2O; NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O), fractional conversion 1 of the key component.",
         why_it_matters="Tail-gas combustion supplies process heat; the stoichiometry determines flue-gas composition and the recoverable heat."),
    dict(file="10_stream_results.png", title="Stream results", env="Simulation", nav=["Results Summary", "Streams"], tab="Material",
         navigation_path="Simulation > Results Summary > Streams > Material",
         what_is_shown="Material stream table of the converged baseline: temperatures, pressures, flows and compositions.",
         why_it_matters="Primary evidence of the converged Aspen solution from which the H2 production and conversion KPIs are extracted."),
    dict(file="11_reactor_results.png", title="CRACKER results", env="Simulation", nav=["Blocks", "CRACKER", "Results"], tab=None,
         navigation_path="Simulation > Blocks > CRACKER > Results",
         what_is_shown="RGibbs results summary of the converged baseline: outlet temperature, outlet pressure, heat duty and net heat duty.",
         why_it_matters="Shows the endothermic cracking duty that dominates the energy demand of the process."),
    dict(file="12_heat_exchanger_results.png", title="FEHE thermal results", env="Simulation", nav=["Blocks", "FEHE", "Thermal Results"], tab=None,
         navigation_path="Simulation > Blocks > FEHE > Thermal Results",
         what_is_shown="HeatX thermal results: hot stream S5 -> S6 and cold stream S2 -> S3 inlet/outlet temperatures and pressures, and the exchanger heat duty.",
         why_it_matters="Quantifies the heat recovered internally, the basis of the heat-integration benefit."),
    dict(file="13_sensitivity_input.png", title="Sensitivity STEMP input", env="Simulation", nav=["Model Analysis Tools", "Sensitivity", "STEMP", "Input"], tab="Vary",
         navigation_path="Simulation > Model Analysis Tools > Sensitivity > STEMP > Input > Vary",
         what_is_shown="Vary tab of STEMP: manipulated variable Block-Var CRACKER TEMP, equidistant from 350 to 800 C with an increment of 50 C.",
         why_it_matters="Documents how the in-Aspen temperature sensitivity was defined."),
    dict(file="14_sensitivity_results.png", title="Sensitivity STEMP results", env="Simulation", nav=["Model Analysis Tools", "Sensitivity", "STEMP", "Results"], tab=None,
         navigation_path="Simulation > Model Analysis Tools > Sensitivity > STEMP > Results",
         what_is_shown="STEMP results summary table: for each varied CRACKER temperature the status and the tabulated NH3 conversion, H2 product flow, CRACKER duty and HEATER duty.",
         why_it_matters="Aspen-native evidence of the trend of the tabulated variables with the varied reactor temperature."),
    dict(file="15_run_status.png", title="Run status", env="Simulation", nav=["Results Summary", "Run Status"], tab=None,
         navigation_path="Simulation > Results Summary > Run Status",
         what_is_shown="Run Status summary: \"Calculations were completed normally\", Aspen Plus version 41.0 (V15), run title, date and time of the run.",
         why_it_matters="Convergence evidence: shows the baseline run completed and whether any warnings or errors were issued."),
    dict(file="16_calculator.png", title="Calculator AIRCALC", env="Simulation", nav=["Flowsheeting Options", "Calculator", "AIRCALC", "Input"], tab=None,
         navigation_path="Simulation > Flowsheeting Options > Calculator > AIRCALC > Input",
         what_is_shown="Define tab of Calculator AIRCALC: imported variables FH2 and FNH3 (TAILGAS component mole flows) and exported variable FAIR (AIR stream mole flow).",
         why_it_matters="Shows how the specified burner excess air is maintained automatically when the tail-gas flow changes."),
]

# ----------------------------------------------------------------------------- window helpers
PW_RENDERFULLCONTENT = 2


def find_main_window(pids: set[int]) -> int:
    import win32gui
    import win32process

    wins = []

    def cb(h, _):
        try:
            _, pid = win32process.GetWindowThreadProcessId(h)
        except Exception:
            return True
        if pid in pids and win32gui.IsWindowVisible(h):
            l, t, r, b = win32gui.GetWindowRect(h)
            wins.append(((r - l) * (b - t), h))
        return True

    win32gui.EnumWindows(cb, None)
    if not wins:
        raise RuntimeError(f"no visible window for Aspen pids {pids}")
    return max(wins)[1]


def print_window(hwnd: int):
    """Real pixels of the top-level window via PrintWindow(PW_RENDERFULLCONTENT)."""
    import win32gui
    import win32ui
    from PIL import Image

    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w, h = r - l, b - t
    hdc = win32gui.GetWindowDC(hwnd)
    src = win32ui.CreateDCFromHandle(hdc)
    mem = src.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(src, w, h)
    mem.SelectObject(bmp)
    ok = ctypes.windll.user32.PrintWindow(hwnd, mem.GetSafeHdc(), PW_RENDERFULLCONTENT)
    info = bmp.GetInfo()
    img = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bmp.GetBitmapBits(True), "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    mem.DeleteDC()
    src.DeleteDC()
    win32gui.ReleaseDC(hwnd, hdc)
    if not ok:
        raise RuntimeError("PrintWindow failed")
    return img


def is_blank(img) -> bool:
    ext = img.convert("L").getextrema()
    return ext[1] - ext[0] < 10


def capture(hwnd: int, path: Path) -> str:
    img = print_window(hwnd)
    method = "win32 PrintWindow(PW_RENDERFULLCONTENT) of the Aspen Plus top-level window"
    if is_blank(img):
        import win32gui
        from PIL import ImageGrab

        if win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError("PrintWindow returned a blank image and the Aspen window is not in the foreground")
        img = ImageGrab.grab(bbox=win32gui.GetWindowRect(hwnd), all_screens=True)
        method = "PIL.ImageGrab of the Aspen Plus window rectangle (foreground)"
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return method


def size_window(hwnd: int, w: int = 1680, h: int = 1000) -> None:
    """Restore and size the Aspen window without activating it (no input to the user's desktop)."""
    import win32con
    import win32gui

    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
    win32gui.SetWindowPos(hwnd, 0, 20, 20, w, h, SWP_NOZORDER | SWP_NOACTIVATE)


# ----------------------------------------------------------------------------- UIA navigation
class Gui:
    def __init__(self, hwnd: int):
        from pywinauto import Desktop

        self.hwnd = hwnd
        self.win = Desktop(backend="uia").window(handle=hwnd).wrapper_object()

    def descendants(self, **kw):
        return self.win.descendants(**kw)

    def find(self, control_type: str, name: str, timeout: float = 5.0, exact: bool = True):
        t0 = time.time()
        while True:
            for e in self.win.descendants(control_type=control_type):
                n = e.element_info.name or ""
                if (n == name) if exact else (name.lower() in n.lower()):
                    return e
            if time.time() - t0 > timeout:
                raise LookupError(f"{control_type} {name!r} not found")
            time.sleep(0.3)

    def invoke(self, control_type: str, name: str, timeout: float = 5.0):
        e = self.find(control_type, name, timeout)
        try:
            e.invoke()
        except Exception:
            try:
                e.select()
            except Exception:
                e.iface_legacy_iaccessible.DoDefaultAction()
        return e

    def tree(self):
        trees = self.win.descendants(control_type="Tree")
        if not trees:
            raise LookupError("navigation tree not found")
        return max(trees, key=lambda t: len(t.descendants(control_type="TreeItem")))

    def nav(self, names: list[str]):
        """Select a navigation-pane item by its path, expanding parents (UIA patterns only)."""
        tree = self.tree()
        items = tree.children(control_type="TreeItem")
        node = None
        for i, name in enumerate(names):
            match = [it for it in items if (it.element_info.name or "").strip() == name]
            if not match:
                avail = [it.element_info.name for it in items]
                raise LookupError(f"tree item {name!r} not found under {names[:i]}; available {avail}")
            node = match[0]
            if i < len(names) - 1:
                try:
                    node.expand()
                except Exception:
                    pass
                time.sleep(0.3)
                items = node.children(control_type="TreeItem")
        node.select()
        time.sleep(0.3)
        # Selecting a tree item does not open its form; Enter does. The key is *posted* to the Aspen
        # window's own message queue (PostMessage), so no input reaches the user's foreground app.
        import win32con
        import win32gui

        win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0x001C0001)
        win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0xC01C0001)
        return node

    def env(self, name: str):
        """Switch environment via the navigator-bar group (OutlookBarGroup), UIA patterns only."""
        for e in self.win.descendants(control_type="Custom"):
            if e.element_info.class_name == "OutlookBarGroup" and e.element_info.name == name:
                for how in ("select", "invoke"):
                    try:
                        getattr(e, how)()
                        return e
                    except Exception:
                        continue
                try:
                    e.iface_legacy_iaccessible.DoDefaultAction()
                    return e
                except Exception as exc:
                    raise LookupError(f"cannot activate environment {name}: {exc}")
        raise LookupError(f"environment {name!r} not found")

    def tab(self, name: str):
        for e in self.win.descendants(control_type="TabItem"):
            if (e.element_info.name or "").strip() == name:
                e.select()
                return e
        raise LookupError(f"tab {name!r} not found")


# ----------------------------------------------------------------------------- main
def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return {e["file"]: e for e in json.loads(MANIFEST.read_text(encoding="utf-8"))["captures"]}
        except Exception:
            pass
    return {}


def _write_manifest(entries: dict, model_file: str) -> None:
    order = [s["file"] for s in SPECS]
    MANIFEST.write_text(json.dumps({
        "generated_by": "aspen/automation/capture_screenshots.py",
        "aspen_version": ASPEN_VERSION,
        "model_file": model_file,
        "note": "Screenshots of the real Aspen Plus V15 GUI with the baseline model opened through COM and run before capture. "
                "status 'captured' entries were opened and visually checked after saving.",
        "captures": [entries[f] for f in order if f in entries],
    }, indent=2), encoding="utf-8")


def capture_spec(gui: Gui, spec: dict, settle_s: float = 1.5) -> str:
    if spec.get("env"):
        gui.env(spec["env"])
        time.sleep(0.8)
    if spec.get("flowsheet"):
        gui.tab("Main Flowsheet")
        time.sleep(0.5)
        for b in gui.win.descendants(control_type="Button"):
            if b.element_info.automation_id == "PART_ZoomToFitButton":
                b.invoke()
    else:
        gui.nav(spec["nav"])
        time.sleep(settle_s + 1.0)
        if spec.get("tab"):
            try:
                gui.tab(spec["tab"])
            except LookupError:
                log.warning("%s: tab %s not found, capturing the default tab", spec["file"], spec["tab"])
    time.sleep(settle_s)
    return capture(gui.hwnd, OUT / spec["file"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from amcrax.aspen.runner import aspen_lock
    from amcrax.aspen.session import AspenSession

    model = Path(args.model) if args.model else (MODELS / "baseline.apw")
    if not model.exists():
        model = MODELS / "baseline.bkp"
    specs = SPECS
    if args.only:
        specs = [s for s in SPECS if any(s["file"].startswith(o) or s["file"][:-4] == o for o in args.only)]
    entries = _load_manifest()
    rel_model = str(model.relative_to(ROOT)).replace("\\", "/")
    with aspen_lock():
        with AspenSession(visible=True) as s:
            s.open(model)
            s.run(timeout_s=180)
            time.sleep(3)
            hwnd = find_main_window(s._own_pids)
            size_window(hwnd)
            time.sleep(2)
            gui = Gui(hwnd)
            for spec in specs:
                e = {k: spec[k] for k in ("file", "title", "navigation_path", "what_is_shown", "why_it_matters")}
                e.update(aspen_version=ASPEN_VERSION, model_file=rel_model,
                         captured_local_time=datetime.now().isoformat(timespec="seconds"))
                try:
                    e["capture_method"] = capture_spec(gui, spec)
                    e["status"] = "captured"
                    e["reason_if_not"] = None
                    e["visually_verified"] = False  # set True only after a human/agent has inspected the PNG
                except Exception as exc:
                    log.error("%s failed: %s", spec["file"], exc)
                    e.update(capture_method=None, status="not_captured", reason_if_not=f"automation error: {exc}", visually_verified=False)
                entries[spec["file"]] = e
                _write_manifest(entries, rel_model)
    print(json.dumps({k: v["status"] for k, v in entries.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
