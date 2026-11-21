"""AmCraX pitch deck builder (re-runnable).

Pipeline
  1. Python reads every number from results/ and research/ files (no typed performance numbers) and
     records each one with its source file and key in a provenance registry.
  2. Python renders the matplotlib figures (dark AmCraX style, 200 dpi) and writes build/deck_data.json.
  3. Node.js + pptxgenjs (deck_layout.js) lays out the editable slides (16) -> AmCraX_Pitch_Deck.pptx.
     Node runtime: $env:AMCRAX_NODE, else `node` on PATH (project toolchain via scripts/env.ps1), else the
     project tool folder, else (last resort) the Node runtime embedded in VS Code (ELECTRON_RUN_AS_NODE=1).
  4. PowerPoint COM exports the PDF and one PNG per slide (preview/slide_NN.png). The build closes only the
     presentation it opened, and quits PowerPoint only if PowerPoint was not already running.
  5. Checks: word counts, leftover placeholder text (non-zero exit), pending items; speaker_script.md.

Run:
  . "<project root>\\scripts\\env.ps1"; python "<project root>\\docs\\pitch_deck\\build_deck.py"
Options: --no-export (skip PowerPoint COM), --no-tests (skip pytest collection count).
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILD = HERE / "build"
FIG = BUILD / "figures"
PREVIEW = HERE / "preview"
PPTX = HERE / "AmCraX_Pitch_Deck.pptx"
PDF = HERE / "AmCraX_Pitch_Deck.pdf"
SCRIPT_MD = HERE / "speaker_script.md"
DATA_JSON = BUILD / "deck_data.json"
LAYOUT_JS = HERE / "deck_layout.js"

TAG_ASPEN = "[Aspen Plus V15]"
TAG_PY = "[Python model]"
TAG_ASPY = "[Aspen Plus V15 + Python]"  # AmCraX Python module applied to an Aspen Plus V15 result
TAG_LIT = "[Literature]"
TAG_ASM = "[Assumption]"

# palette (design_tokens.md)
C = dict(bg="#0b1020", surface="#121a2f", surface2="#1a2542", border="#2a3658", text="#eef2fb",
         text2="#c3cce3", muted="#8e9bbd", primary="#38bdf8", accent="#ff7a3d", nh3="#4ade80",
         h2="#f472b6", n2="#a5b4fc", heat="#ff6b3d", cold="#60a5fa", ok="#3fcf8e", warn="#f5b73b",
         python="#a78bfa")


# ----------------------------------------------------------------------------- registry
class Registry:
    def __init__(self):
        self.numbers: list[tuple[str, str, str, str, str]] = []  # key, shown, file, json key, tag
        self.pending: list[tuple[str, str]] = []                  # item, expected file
        self.warnings: list[str] = []

    def num(self, label: str, value, shown: str, file: str, key: str, tag: str) -> str:
        self.numbers.append((label, shown, file, key, tag))
        return shown

    def pend(self, item: str, path: str):
        if (item, path) not in self.pending:
            self.pending.append((item, path))

    def warn(self, msg: str):
        self.warnings.append(msg)


R = Registry()


def rel(p: Path | str) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v: float, nd: int = 1) -> str:
    return f"{v:,.{nd}f}"


def pct(v: float, nd: int = 1) -> str:
    return f"{100 * v:.{nd}f}%"


def get(d, path: str):
    cur = d
    for part in path.split("."):
        cur = cur[part]
    return cur


def deep_find(obj, key_regex: str, numeric: bool = True, _path: str = ""):
    """First (path, value) whose key matches key_regex (case-insensitive), depth-first."""
    rx = re.compile(key_regex, re.I)
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{_path}.{k}" if _path else str(k)
            if rx.search(str(k)) and ((isinstance(v, (int, float)) and not isinstance(v, bool)) or not numeric):
                if not (isinstance(v, float) and math.isnan(v)):
                    return p, v
        for k, v in obj.items():
            p = f"{_path}.{k}" if _path else str(k)
            r = deep_find(v, key_regex, numeric, p)
            if r:
                return r
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            r = deep_find(v, key_regex, numeric, f"{_path}[{i}]")
            if r:
                return r
    return None


# ----------------------------------------------------------------------------- literature
_REFS = None


def short_apa(citekey: str) -> str:
    global _REFS
    if _REFS is None:
        _REFS = {r["citekey"]: r for r in load_json(ROOT / "research" / "references.json")}
    apa = _REFS[citekey]["apa7"]
    m = re.match(r"^(.*?)\((\d{4}|n\.d\.)\)", apa)
    authors, year = m.group(1), m.group(2)
    first = authors.split(",")[0].strip()
    n_auth = authors.count("&") + authors.count(".,") if "&" in authors else 1
    if "&" not in authors:
        return f"{first}, {year}"
    surnames = re.findall(r"(?:^|&\s|\.,\s)([A-Z][\w'\-]+(?:\s[A-Z][\w'\-]+)?),", authors)
    if len(surnames) == 2:
        return f"{surnames[0]} & {surnames[1]}, {year}"
    return f"{first} et al., {year}"


def lit(citekey: str, name_contains: str, label: str, shown_fmt=None) -> dict:
    """Read a literature parameter from research/notes/<citekey>.json (fails loudly if absent)."""
    p = ROOT / "research" / "notes" / f"{citekey}.json"
    d = load_json(p)
    for i, par in enumerate(d.get("parameters", [])):
        if name_contains.lower() in str(par.get("name", "")).lower():
            v = par["value"]
            shown = shown_fmt(v) if shown_fmt else f"{v}"
            cite = f"{short_apa(citekey)}, p. {par.get('page')}"
            R.num(label, v, shown, rel(p), f"parameters[{i}] '{par.get('name')}' ({par.get('locator')})", TAG_LIT)
            return dict(value=v, shown=shown, unit=par.get("unit", ""), cite=cite, page=par.get("page"),
                        conditions=par.get("conditions", ""))
    raise KeyError(f"literature parameter '{name_contains}' not found in {p}")


# ----------------------------------------------------------------------------- figures
def mpl_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": C["bg"], "axes.facecolor": C["bg"], "savefig.facecolor": C["bg"],
        "axes.edgecolor": C["border"], "axes.labelcolor": C["text2"], "xtick.color": C["text2"],
        "ytick.color": C["text2"], "text.color": C["text"], "font.family": "Segoe UI",
        "font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13, "xtick.labelsize": 12,
        "ytick.labelsize": 12, "legend.fontsize": 12, "axes.grid": True, "grid.color": "#ffffff",
        "grid.alpha": 0.08, "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def fig_equilibrium(out: Path, pressures=(1.0, 5.0, 20.0, 40.0)) -> dict:
    plt = mpl_style()
    ag = read_csv(ROOT / "results/validation/equilibrium_aspen_grid.csv")
    pg = read_csv(ROOT / "results/validation/equilibrium_python_grid.csv")
    cols = [C["primary"], C["nh3"], C["accent"], C["h2"], C["n2"], C["warn"]]
    fig, ax = plt.subplots(figsize=(8.1, 3.55), dpi=200)
    for i, P in enumerate(pressures):
        py = sorted(((float(r["T_C"]), float(r["nh3_conversion"])) for r in pg
                     if float(r["P_bar"]) == P and r["eos"] == "pr"))
        asp = sorted(((float(r["T_C"]), float(r["nh3_conversion"])) for r in ag
                      if float(r["P_bar"]) == P and r["property_method"] == "PENG-ROB"))
        if py:
            ax.plot([t for t, _ in py], [100 * x for _, x in py], color=cols[i % 6], lw=2.2,
                    label=f"{P:g} bar Python")
        if asp:
            ax.scatter([t for t, _ in asp], [100 * x for _, x in asp], s=46, facecolor=C["bg"],
                       edgecolor=cols[i % 6], lw=1.8, zorder=3)
    ax.scatter([], [], s=46, facecolor=C["bg"], edgecolor=C["text2"], lw=1.8, label="Aspen RGibbs points")
    ax.set_xlabel("Reactor temperature (°C)")
    ax.set_ylabel("NH$_3$ equilibrium conversion (%)")
    ax.set_ylim(40, 101)
    ax.legend(loc="lower right", frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return {"path": str(out), "w": 8.1, "h": 3.55}


# ----------------------------------------------------------------------------- helpers
def img_info(p: Path, max_tall: float = 1.0 / 1.25, crop_ratio: float = 1.6) -> dict:
    """Image info for layout. Full-page captures taller than max_tall (w/h ratio) are cropped (top of page,
    viewport-like) into build/figures; the original screenshot file is never modified."""
    from PIL import Image
    with Image.open(p) as im:
        w, h = im.size
        if h > 0 and w / h < max_tall and int(w / crop_ratio) < h:
            ch = int(w / crop_ratio)
            out = FIG / f"crop_{Path(p).stem}.png"
            im.crop((0, 0, w, ch)).save(out)
            return {"path": str(out), "px_w": w, "px_h": ch, "cropped_from": rel(p)}
    return {"path": str(p), "px_w": w, "px_h": h}


def crop_info(p: Path, frac: tuple[float, float, float, float], tag: str, viewport_ratio: float = 1.6) -> dict:
    """Crop a screenshot to its informative region (fractions l, t, r, b of the viewport) so text stays legible on
    the slide. A full-page capture is first reduced to its top viewport (w / viewport_ratio). The source file on disk
    is never modified; whatever capture is on disk at build time is used."""
    from PIL import Image
    with Image.open(p) as im:
        w, h = im.size
        vh = min(h, int(round(w / viewport_ratio))) if h > w / viewport_ratio * 1.05 else h
        l, t, r, b = frac
        box = (int(l * w), int(t * vh), int(r * w), int(b * vh))
        out = FIG / f"crop_{Path(p).stem}_{tag}.png"
        im.crop(box).save(out)
        return {"path": str(out), "px_w": box[2] - box[0], "px_h": box[3] - box[1], "cropped_from": rel(p),
                "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(Path(p).stat().st_mtime))}


def hero_crop(p: Path, tag: str, viewport_ratio: float = 1.6, pad: int = 24) -> dict:
    """Content-aware crop of a web-page capture to its first screen: the horizontal extent of the page content
    (columns that differ from the page background below the navigation bar) and the rows down to the first
    section boundary after the hero. Works for viewport-sized and full-page captures of any width, so a
    re-captured screenshot is framed the same way without editing the build."""
    import numpy as np
    from PIL import Image
    with Image.open(p) as im0:
        im = im0.convert("RGB")
    w, h = im.size
    vh = min(h, int(round(w / viewport_ratio)))
    a = np.asarray(im.crop((0, 0, w, vh)), dtype=np.int16)
    bg = np.median(a[int(0.2 * vh):, :, :].reshape(-1, 3), axis=0)
    diff = np.abs(a - bg).sum(axis=2) > 40
    body = diff[int(0.15 * vh):, :]
    cols = np.where(body.mean(axis=0) > 0.004)[0]
    l, r = (int(cols[0]), int(cols[-1])) if len(cols) else (0, w - 1)
    l, r = max(0, l - pad), min(w, r + pad)
    # first section boundary (a sharp change of the row-mean colour) in the lower half of the first screen
    # page sections span the full width: a persistent step in the colour of the page MARGINS (outside the content
    # column, so never text or pictures) marks the end of the first section
    margins = np.concatenate([a[:, : max(4, l - 4), :], a[:, min(w - 4, r + 4):, :]], axis=1)
    med = np.median(margins.mean(axis=2), axis=1)
    b = int(0.78 * vh)
    for y in range(int(0.55 * vh), vh - 8):
        if abs(med[y + 4] - med[y - 4]) > 2 and abs(med[y + 8] - med[y - 8]) > 2:
            b = y - 4
            break
    out = FIG / f"crop_{Path(p).stem}_{tag}.png"
    im.crop((l, 0, r, b)).save(out)
    return {"path": str(out), "px_w": r - l, "px_h": b, "cropped_from": rel(p),
            "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(Path(p).stat().st_mtime))}


def find_first(patterns: list[str]) -> Path | None:
    for pat in patterns:
        hits = sorted(glob.glob(str(ROOT / pat)))
        if hits:
            return Path(hits[0])
    return None


def count_tests() -> tuple[int | None, str]:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--collect-only",
                              "--continue-on-collection-errors", "-p", "no:cacheprovider"],
                             cwd=ROOT, capture_output=True, text=True, timeout=300).stdout
    except Exception as e:  # noqa: BLE001
        R.warn(f"pytest collection failed: {e}")
        return None, ""
    m = re.search(r"(\d+) tests? collected", out)
    if m:
        return int(m.group(1)), out
    n = sum(int(x) for x in re.findall(r"^tests[/\\][^\s:]+\.py: (\d+)\s*$", out, re.M))
    n += len(re.findall(r"^tests[/\\]\S+::\S+", out, re.M))
    return (n or None), out


def count_endpoints() -> tuple[int, str, str]:
    """(count, source, key). Paths in the running API's OpenAPI schema; fallback: the count stored by the last
    successful fetch (build/api_paths.json); last resort: route decorators in backend/amcrax/api."""
    import urllib.request
    store = BUILD / "api_paths.json"
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/openapi.json", timeout=5) as r:
            spec = json.loads(r.read().decode("utf-8"))
        paths = spec.get("paths", {})
        n_ops = sum(len([m for m in v if m in ("get", "post", "put", "delete", "patch")]) for v in paths.values())
        store.write_text(json.dumps({"paths": len(paths), "operations": n_ops,
                                     "fetched_local": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1), encoding="utf-8")
        return len(paths), "http://127.0.0.1:8000/openapi.json (running API)", f"len(paths) ({n_ops} operations)"
    except Exception as e:  # noqa: BLE001
        R.warn(f"running API not reachable for the OpenAPI path count ({e.__class__.__name__}); using fallback")
    if store.exists():
        d = load_json(store)
        return int(d["paths"]), f"{rel(store)} (stored count from the API fetched {d.get('fetched_local')})", "paths"
    n = 0
    for f in glob.glob(str(ROOT / "backend/amcrax/api/**/*.py"), recursive=True):
        n += len(re.findall(r"@\w+\.(get|post|put|delete|patch)\(", Path(f).read_text(encoding="utf-8", errors="ignore")))
    return n, "backend/amcrax/api/**/*.py", "count of @router/app.<verb>( decorators"


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][\w%.,'/\-+°]*", s))


# ----------------------------------------------------------------------------- data
def collect() -> dict:
    S = {}  # numbers / strings for slides
    f_base = ROOT / "results/simulations/baseline.json"
    f_nohi = ROOT / "results/simulations/baseline_no_hi.json"
    base, nohi = load_json(f_base), load_json(f_nohi)
    assert base["source"] == "aspen_plus_v15", "baseline.json is not an Aspen result"
    k, kn, inp = base["kpis"], nohi["kpis"], base["inputs"]
    fb, fn = rel(f_base), rel(f_nohi)

    def A(label, key, shown, src=fb, d=base):
        return R.num(label, get(d, key), shown, src, key, TAG_ASPEN)

    S["T"] = A("Reactor temperature", "inputs.reactor_temperature_C", f"{inp['reactor_temperature_C']:.0f} °C")
    S["P"] = A("Reactor pressure", "inputs.reactor_pressure_bar", f"{inp['reactor_pressure_bar']:.0f} bar")
    S["feed"] = A("Feed basis", "inputs.feed_total_kmol_h", f"{inp['feed_total_kmol_h']:.0f} kmol/h")
    S["feed_kg"] = A("Feed mass", "streams.FEED.mass_flow_kg_h", f"{fnum(base['streams']['FEED']['mass_flow_kg_h'], 0)} kg/h")
    S["rec"] = A("PSA H2 recovery (input)", "inputs.psa_h2_recovery", f"{inp['psa_h2_recovery']:.2f}")
    S["excess_air"] = A("Burner excess air", "inputs.burner_excess_air", f"{100*inp['burner_excess_air']:.0f}%")
    S["approach"] = A("FEHE hot-end approach", "inputs.fehe_hot_end_approach_K", f"{inp['fehe_hot_end_approach_K']:.0f} K")
    S["method"] = A("Property method", "inputs.property_method", inp["property_method"])
    S["conv"] = A("NH3 conversion", "kpis.nh3_conversion", pct(k["nh3_conversion"]))
    S["h2kg"] = A("H2 product", "kpis.h2_product_kg_h", f"{fnum(k['h2_product_kg_h'])} kg/h")
    S["h2kg_n"] = fnum(k["h2_product_kg_h"])
    S["purity"] = A("H2 purity", "kpis.h2_purity_mole_frac", pct(k["h2_purity_mole_frac"], 2))
    S["lhv"] = A("LHV efficiency", "kpis.lhv_efficiency", pct(k["lhv_efficiency"]))
    S["lhv_nohi"] = A("LHV efficiency no HI", "kpis.lhv_efficiency", pct(kn["lhv_efficiency"]), fn, nohi)
    S["yield"] = A("Overall H2 yield", "kpis.h2_yield_overall", pct(k["h2_yield_overall"]))
    S["duty"] = A("Cracker duty", "kpis.reactor_duty_kW", f"{fnum(k['reactor_duty_kW'], 0)} kW")
    S["recovered"] = A("Recovered heat (FEHE)", "kpis.recovered_heat_kW", f"{fnum(k['recovered_heat_kW'], 0)} kW")
    S["ext"] = A("External heating", "kpis.total_external_heating_kW", f"{fnum(k['total_external_heating_kW'], 0)} kW")
    S["ext_nohi"] = A("External heating no HI", "kpis.total_external_heating_kW", f"{fnum(kn['total_external_heating_kW'], 0)} kW", fn, nohi)
    red = 1 - k["total_external_heating_kW"] / kn["total_external_heating_kW"]
    S["ext_red"] = R.num("External heating reduction (derived)", red, pct(red, 0), f"{fb} + {fn}", "kpis.total_external_heating_kW (ratio)", TAG_ASPEN)
    S["spec"] = A("Specific heat demand", "kpis.specific_heat_demand_kWh_per_kgH2", f"{k['specific_heat_demand_kWh_per_kgH2']:.2f} kWh/kg")
    S["spec_nohi"] = A("Specific heat demand no HI", "kpis.specific_heat_demand_kWh_per_kgH2", f"{kn['specific_heat_demand_kWh_per_kgH2']:.2f} kWh/kg", fn, nohi)
    st = base["status"]
    S["converged"] = R.num("Aspen converged", st["converged"], "Converged, no errors" if st["converged"] and not st["has_errors"] else "Check run status", fb, "status.converged/has_errors", TAG_ASPEN)
    S["engine_s"] = A("Aspen engine time", "status.engine_time_s", f"{st['engine_time_s']:.1f} s")
    S["mass_closure"] = None
    mc = base.get("balances", {}).get("mass_closure_rel")
    if mc is not None:
        S["mass_closure"] = A("Mass balance closure", "balances.mass_closure_rel", f"{abs(mc):.0e}")

    # Aspen cases on disk
    n_cases = 0
    for f in glob.glob(str(ROOT / "results/simulations/*.json")):
        try:
            if load_json(Path(f)).get("source") == "aspen_plus_v15":
                n_cases += 1
        except Exception:  # noqa: BLE001
            pass
    for f in glob.glob(str(ROOT / "results/sensitivity/aspen_*.csv")):
        n_cases += len(read_csv(Path(f)))
    S["n_cases"] = R.num("Aspen cases on disk", n_cases, f"{n_cases}", "results/simulations/*.json + results/sensitivity/aspen_*.csv", "count(source == aspen_plus_v15) + csv rows", TAG_ASPEN)

    # evidence counts (F6), all computed from files at build time
    ev = {}
    sens_files = [f for f in glob.glob(str(ROOT / "results/sensitivity/aspen_*.csv")) if "native" not in Path(f).name]
    ev["sens"] = sum(len(read_csv(Path(f))) for f in sens_files)
    R.num("Aspen sensitivity runs (COM-driven, one Aspen run per row)", ev["sens"], str(ev["sens"]), "results/sensitivity/aspen_*.csv (excl. aspen_native_*)", "row count over " + ", ".join(sorted(Path(f).stem for f in sens_files)), TAG_ASPEN)
    grid = read_csv(ROOT / "results/validation/equilibrium_aspen_grid.csv")
    ev["grid"] = len(grid)
    ev["grid_methods"] = " and ".join(sorted({r["property_method"] for r in grid}, reverse=True))
    R.num("Equilibrium grid points (Aspen RGibbs)", ev["grid"], str(ev["grid"]), "results/validation/equilibrium_aspen_grid.csv", f"row count (property_method: {ev['grid_methods']})", TAG_ASPEN)
    scn = [f for f in glob.glob(str(ROOT / "results/simulations/scn_*.json")) if load_json(Path(f)).get("source") == "aspen_plus_v15"]
    ev["scn"] = len(scn)
    R.num("Named Aspen scenarios", ev["scn"], str(ev["scn"]), "results/simulations/scn_*.json", "count(source == aspen_plus_v15)", TAG_ASPEN)
    f_av = ROOT / "results/optimisation/aspen_verification.json"
    ev["opt"] = len(load_json(f_av)["candidates"]) if f_av.exists() else 0
    R.num("Optimisation candidates re-solved in Aspen", ev["opt"], str(ev["opt"]), rel(f_av), "len(candidates)", TAG_ASPEN)
    man = load_json(ROOT / "aspen/screenshots/manifest.json")
    ev["shots"] = sum(1 for c in man["captures"] if c.get("status") == "captured" and (ROOT / "aspen/screenshots" / c["file"]).exists())
    R.num("Genuine Aspen GUI screenshots", ev["shots"], str(ev["shots"]), "aspen/screenshots/manifest.json", "count(status == captured and file exists)", TAG_ASPEN)
    S["ev"] = ev

    # equilibrium agreement
    f_cmp = ROOT / "results/validation/equilibrium_comparison.csv"
    rows = [r for r in read_csv(f_cmp) if (r["aspen_property_method"], r["python_eos"]) in (("PENG-ROB", "pr"), ("IDEAL", "ideal"))]
    devs = [abs(float(r["nh3_conversion_abs_dev_pp"])) for r in rows if r["nh3_conversion_abs_dev_pp"] not in ("", "nan")]
    S["eq_maxdev"] = R.num("Max |Aspen - Python| equilibrium conversion", max(devs), f"{max(devs):.2f} pp", rel(f_cmp), "max |nh3_conversion_abs_dev_pp| (PENG-ROB~pr, IDEAL~ideal)", TAG_ASPY)
    S["eq_n"] = R.num("Equilibrium comparison points", len(devs), f"{len(devs)}", rel(f_cmp), "row count (matched EOS pairs)", TAG_ASPY)
    Ps = sorted({float(r["P_bar"]) for r in rows})
    Ts = sorted({float(r["T_C"]) for r in rows})
    S["eq_range"] = f"{Ts[0]:.0f}-{Ts[-1]:.0f} °C, {Ps[0]:g}-{Ps[-1]:g} bar"

    # Aspen vs Python flowsheet
    f_avp = ROOT / "results/validation/aspen_vs_python_baseline.csv"
    avp = {r["quantity"]: r for r in read_csv(f_avp)}
    picks = [q for q in ("kpi.nh3_conversion", "kpi.h2_product_kg_h", "kpi.reactor_duty_kW", "kpi.total_external_heating_kW",
                         "kpis.nh3_conversion", "kpis.h2_product_kg_h", "kpis.reactor_duty_kW", "kpis.total_external_heating_kW") if q in avp]
    if not picks:
        picks = [q for q in avp if q.startswith("kpi")][:6]
    rd = [abs(float(avp[q]["rel_diff"])) for q in picks if avp[q]["rel_diff"] not in ("", "nan", "None")]
    if rd:
        S["avp_max"] = R.num("Max relative deviation Aspen vs Python flowsheet KPIs", max(rd), pct(max(rd), 1), rel(f_avp), "max |rel_diff| over " + ", ".join(picks), TAG_PY)
        S["avp_n"] = len(picks)
    else:
        S["avp_max"] = None
        R.warn("aspen_vs_python_baseline.csv: no KPI rows found")

    # native Aspen sensitivity (temperature)
    f_sens = ROOT / "results/sensitivity/aspen_temperature.csv"
    if f_sens.exists():
        rows_t = [r for r in read_csv(f_sens) if str(r.get("converged", "True")).lower() == "true"]
        S["sweep_src"] = rel(f_sens)
        S["sweep_key"] = "h2_product_kg_h"
    else:
        f_sens = ROOT / "results/sensitivity/aspen_native_STEMP_baseline.csv"
        rows_t = read_csv(f_sens)
        S["sweep_src"] = rel(f_sens)
        S["sweep_key"] = "h2_product_kmol_h"
        R.pend("Aspen temperature sweep (fallback: native STEMP block used)", "results/sensitivity/aspen_temperature.csv")
    rows_t.sort(key=lambda r: float(r["reactor_temperature_C"]))
    sweep = [(float(r["reactor_temperature_C"]), float(r[S["sweep_key"]]), float(r["nh3_conversion"]),
              float(r["specific_heat_demand_kWh_per_kgH2"]) if r.get("specific_heat_demand_kWh_per_kgH2") else None) for r in rows_t]
    S["sweep"] = sweep
    R.num("Temperature sweep series", len(sweep), f"{len(sweep)} points", S["sweep_src"], f"reactor_temperature_C, {S['sweep_key']}, nh3_conversion", TAG_ASPEN)
    lo, hi = sweep[0], sweep[-1]
    mid = min(sweep, key=lambda r: abs(r[0] - inp["reactor_temperature_C"]))
    S["sw_lo"] = R.num("Sweep low-T conversion", lo[2], f"{pct(lo[2])} at {lo[0]:.0f} °C", S["sweep_src"], "nh3_conversion (min T)", TAG_ASPEN)
    S["sw_mid"] = R.num("Sweep baseline-T conversion", mid[2], f"{pct(mid[2])} at {mid[0]:.0f} °C", S["sweep_src"], "nh3_conversion (baseline T)", TAG_ASPEN)
    S["sw_hi"] = R.num("Sweep high-T conversion", hi[2], f"{pct(hi[2])} at {hi[0]:.0f} °C", S["sweep_src"], "nh3_conversion (max T)", TAG_ASPEN)
    S["sw_gain"] = f"{100*(hi[2]-mid[2]):.1f}"

    # heat integration (Python on Aspen streams)
    f_hi = ROOT / "results/simulations/heat_integration_baseline.json"
    hi_ = load_json(f_hi)
    cfg = {c["id"]: c for c in hi_["configurations"]}
    S["hi_cfg"] = []
    for cid in ("a", "b", "c", "d2"):
        if cid in cfg:
            c = cfg[cid]
            lab = re.sub(r"^\([a-z0-9]+\)\s*", "", c["label"]).replace(" (dT_min 20 K)", "")
            lab = {"No heat recovery": "No recovery", "Feed/effluent exchanger only": "FEHE only",
                   "FEHE + tail-gas firing": "FEHE + tail-gas firing",
                   "Pinch target incl. tail-gas flue gas": "Pinch target"}.get(lab, lab)
            S["hi_cfg"].append((lab, round(c["external_heating_kW"], 0)))
            R.num(f"HI external heating ({cid})", c["external_heating_kW"], fnum(c["external_heating_kW"], 0), rel(f_hi), f"configurations[id={cid}].external_heating_kW", TAG_ASPY)
    c_c = cfg.get("c")
    S["hi_tail"] = R.num("External heating with tail-gas firing", c_c["external_heating_kW"], f"{fnum(c_c['external_heating_kW'], 0)} kW", rel(f_hi), "configurations[id=c].external_heating_kW", TAG_ASPY)
    S["hi_tail_red"] = R.num("Reduction vs no recovery (tail gas)", c_c["reduction_vs_no_recovery"], pct(c_c["reduction_vs_no_recovery"], 0), rel(f_hi), "configurations[id=c].reduction_vs_no_recovery", TAG_ASPY)
    S["hi_target"] = R.num("Pinch target import incl. flue", hi_["targets_with_flue"]["hot_utility_kW"], f"{fnum(hi_['targets_with_flue']['hot_utility_kW'], 0)} kW", rel(f_hi), "targets_with_flue.hot_utility_kW", TAG_ASPY)
    S["hi_dtmin"] = R.num("dT_min", hi_["dT_min_K"], f"{hi_['dT_min_K']:.0f} K", rel(f_hi), "dT_min_K", TAG_ASPY)
    fe = hi_["fehe"]
    S["fehe_cross"] = R.num("FEHE temperature cross", fe["temperature_cross"], "no temperature cross" if not fe["temperature_cross"] else "temperature cross", rel(f_hi), "fehe.temperature_cross", TAG_ASPY)
    S["fehe_area"] = R.num("FEHE area (order of magnitude)", fe["area_m2"], f"~{fe['area_m2']:.0f} m²", rel(f_hi), "fehe.area_m2 (U assumed)", TAG_ASM)
    S["hi_fig"] = find_first(["results/figures/hi_composite_baseline.png"])

    # literature
    L = {}
    L["comp"] = lit("maccarrone2025comprehensive", "H2 compression energy", "H2 compression energy 1->700 bar")
    L["loss"] = lit("chopra2026decentralized", "Hydrogen loss in transport", "H2 loss in transport (LCA inventory)")
    L["iso_nh3"] = lit("cechetto2023membrane", "Max NH3 in H2", "ISO 14687 NH3 limit")
    L["iso_n2"] = lit("cechetto2023membrane", "Max N2 in H2, vehicle", "ISO 14687 N2 limit (vehicle)")
    L["hrs"] = lit("chopra2026decentralized", "delivery capacity per HRS", "H2 delivered per refuelling station")
    L["rho_nh3"] = lit("cechetto2023membrane", "Liquid NH3 density", "Liquid NH3 density")
    L["p_store"] = lit("cechetto2023membrane", "storage pressure", "Liquid NH3 storage pressure 25 C")
    L["boiloff"] = lit("chopra2026decentralized", "boil-off", "NH3 storage boil-off")
    L["h2wt_lit"] = lit("xu2025review", "H2 content of NH3", "H2 content of NH3 (literature)")
    L["dh"] = lit("cechetto2023membrane", "Reaction enthalpy", "Reaction enthalpy (standard)")
    L["e_ext"] = lit("cechetto2023membrane", "gaseous H2 extraction", "Energy to extract H2 from NH3")
    L["topsoe"] = lit("ahmad2025gtcc", "Commercial NH3 cracking unit capacity", "Commercial cracker capacity")
    L["trl"] = lit("ahmad2025gtcc", "technology readiness", "NH3 cracking TRL")
    L["psa_note"] = "0.71-0.81"  # stated in research/literature_summary.md (Cho 2026; Hansen 2024; Kum 2026)
    m = re.search(r"PSA H2 recoveries are ([0-9.]+-[0-9.]+)", (ROOT / "research/literature_summary.md").read_text(encoding="utf-8"))
    if m:
        L["psa_note"] = R.num("Reported PSA H2 recovery range (literature)", m.group(1), m.group(1), "research/literature_summary.md", "Purification paragraph", TAG_LIT)
    # 0.907 kJ/mol LH2 evaporation is in the conditions text of the same parameter
    m = re.search(r"([0-9.]+) kJ/mol H2 for liquid H2 evaporation", L["e_ext"]["conditions"])
    L["e_lh2"] = float(m.group(1)) if m else None
    if m:
        R.num("Energy to evaporate liquid H2", L["e_lh2"], m.group(1), "research/notes/cechetto2023membrane.json", "parameters 'Energy required for gaseous H2 extraction' conditions", TAG_LIT)
    # stoichiometry (computed): molar masses are standard atomic weights
    MW_H, MW_N = 1.008, 14.007
    wt = 3 * MW_H / (MW_N + 3 * MW_H)
    S["h2wt"] = R.num("H2 mass fraction in NH3 (stoichiometric)", wt, pct(wt), "computed", "3*M(H)/M(NH3)", "[computed]")
    S["h2wt_v"] = round(100 * wt, 1)
    vol = float(L["rho_nh3"]["value"]) * wt
    S["h2vol"] = R.num("H2 per m3 liquid NH3 (derived)", vol, f"{vol:.0f} kg/m³", "research/notes/cechetto2023membrane.json + computed", "Liquid NH3 density x H2 mass fraction", TAG_LIT)
    S["y_h2_stoich"] = R.num("H2 mole fraction, full conversion (stoichiometric)", 0.75, pct(1.5 / 2.0, 0), "computed", "1.5/(1.5+0.5)", "[computed]")
    S["y_n2_stoich"] = R.num("N2 mole fraction, full conversion (stoichiometric)", 0.25, pct(0.5 / 2.0, 0), "computed", "0.5/(1.5+0.5)", "[computed]")
    S["h2_per_t"] = R.num("kg H2 per t NH3 (stoichiometric)", 1000 * wt, f"{1000*wt:.0f} kg", "computed", "1000*wt", "[computed]")
    S["L"] = L

    # architecture
    S["n_endpoints"], ep_src, ep_key = count_endpoints()
    R.num("FastAPI API paths", S["n_endpoints"], str(S["n_endpoints"]), ep_src, ep_key, "[code]")
    mods = [d for d in ("thermodynamics", "process_model", "heat_integration", "kinetics", "reactor", "economics",
                        "environmental", "separation", "optimisation") if (ROOT / "backend/amcrax" / d).is_dir()]
    S["py_mods"] = mods
    return S


def collect_pending(S: dict, run_tests: bool) -> None:
    # tests: the stored JUnit report of the last full pytest run (results/validation/pytest_junit.xml)
    S["n_tests"] = None
    f_junit = ROOT / "results/validation/pytest_junit.xml"
    if f_junit.exists():
        import xml.etree.ElementTree as ET
        root = ET.parse(f_junit).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        tot = sum(int(s.get("tests", 0)) for s in suites)
        fail = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
        skip = sum(int(s.get("skipped", 0)) for s in suites)
        npass = tot - fail - skip
        S["n_tests"] = {"pass": npass, "fail": fail, "skip": skip, "total": tot}
        R.num("Python tests passing (last full run)", npass, str(npass), rel(f_junit), "testsuite@tests - failures - errors - skipped", "[code]")
        R.num("Python tests failing / skipped", (fail, skip), f"{fail} failing, {skip} skipped", rel(f_junit), "testsuite@failures+errors, @skipped", "[code]")
    elif run_tests:
        n, _ = count_tests()
        if n:
            S["n_tests"] = {"pass": None, "fail": None, "skip": None, "total": n}
            R.num("Automated tests collected", n, str(n), "python -m pytest tests -q --collect-only", "collected count", "[code]")
    if not S["n_tests"]:
        R.pend("Automated test count", "results/validation/pytest_junit.xml")

    # Sensitivity files
    for name in ("aspen_temperature", "aspen_pressure", "aspen_tp_map", "aspen_psa_recovery", "aspen_fehe_approach", "aspen_no_hi_temperature"):
        p = ROOT / f"results/sensitivity/{name}.csv"
        if not p.exists():
            R.pend(f"Aspen sensitivity {name}", rel(p))
    # Aspen T-P map, drawn natively (one series per pressure)
    f_tp = ROOT / "results/sensitivity/aspen_tp_map.csv"
    S["tp"] = None
    if f_tp.exists():
        rows = [r for r in read_csv(f_tp) if str(r.get("converged", "True")).lower() == "true"]
        Ts = sorted({float(r["reactor_temperature_C"]) for r in rows})
        Ps = sorted({float(r["reactor_pressure_bar"]) for r in rows})
        look = {(float(r["reactor_temperature_C"]), float(r["reactor_pressure_bar"])): float(r["nh3_conversion"]) for r in rows}
        series = [{"name": f"{p:g} bar", "values": [round(100 * look[(t, p)], 2) if (t, p) in look else None for t in Ts]} for p in Ps]
        S["tp"] = {"labels": [f"{t:.0f}" for t in Ts], "series": series, "src": rel(f_tp)}
        R.num("Aspen T-P map", len(rows), f"{len(rows)} converged points", rel(f_tp), "reactor_temperature_C x reactor_pressure_bar -> nh3_conversion (converged == True)", TAG_ASPEN)
    else:
        R.pend("Aspen T-P map", rel(f_tp))

    # optimisation: minimum-LCOH design point + Aspen re-solve of all candidates (F8)
    f_so = ROOT / "results/optimisation/single_objective.json"
    f_av = ROOT / "results/optimisation/aspen_verification.json"
    S["opt2"] = None
    if f_so.exists():
        so = load_json(f_so)
        src = rel(f_so)
        idx, res = next(((i, r) for i, r in enumerate(so["results"]) if r.get("id") == "min_lcoh"), (None, None))
        if res is None:
            R.pend("Minimum-LCOH result (id == min_lcoh)", src)
        else:
            kp = f"results[{idx}]"
            oi, imp = res["optimum_inputs"], res["improvement"]
            o = {"src": src}
            o["T"] = R.num("Min-LCOH optimum T", oi["reactor_temperature_C"], f"{oi['reactor_temperature_C']:.0f} °C", src, f"{kp}.optimum_inputs.reactor_temperature_C", TAG_PY)
            o["P"] = R.num("Min-LCOH optimum P", oi["reactor_pressure_bar"], f"{oi['reactor_pressure_bar']:.1f} bar", src, f"{kp}.optimum_inputs.reactor_pressure_bar", TAG_PY)
            o["rec"] = R.num("Min-LCOH optimum PSA recovery", oi["psa_h2_recovery"], f"{oi['psa_h2_recovery']:.2f}", src, f"{kp}.optimum_inputs.psa_h2_recovery", TAG_PY)
            o["dt"] = R.num("Min-LCOH optimum FEHE approach", oi["fehe_hot_end_approach_K"], f"{oi['fehe_hot_end_approach_K']:.0f} K", src, f"{kp}.optimum_inputs.fehe_hot_end_approach_K", TAG_PY)
            o["lcoh"] = R.num("Min-LCOH optimum LCOH (Python model)", imp["optimum"], f"{imp['optimum']:.2f}", src, f"{kp}.improvement.optimum", TAG_PY)
            o["lcoh_base"] = R.num("Baseline LCOH, same evaluator (Python model)", imp["baseline"], f"{imp['baseline']:.2f}", src, f"{kp}.improvement.baseline", TAG_PY)
            o["d"] = R.num("Min-LCOH relative change vs baseline", imp["delta_rel"], f"{100*imp['delta_rel']:+.1f}%".replace("-", "−"), src, f"{kp}.improvement.delta_rel", TAG_PY)
            o["bounds"] = R.num("Bound-active variables at min-LCOH optimum", res.get("bound_active"), "; ".join(res.get("bound_active") or []) or "none", src, f"{kp}.bound_active", TAG_PY)
            lim = " ".join(res.get("limitations") or [])
            o["uncosted"] = [w for w, rx in (("exchanger area", r"FEHE area is not costed"), ("PSA size", r"PSA size"), ("catalyst volume", r"catalyst mass"))
                             if re.search(rx, lim, re.I)]
            R.num("Effects not costed at the optimum", len(o["uncosted"]), ", ".join(o["uncosted"]), src, f"{kp}.limitations (text match)", TAG_PY)
            if f_av.exists():
                av = load_json(f_av)
                va = rel(f_av)
                c_ = av["candidates"]
                o["n"] = len(c_)
                o["nconv"] = sum(1 for c in c_ if c.get("aspen_converged"))
                o["npass"] = sum(1 for c in c_ if c.get("status") == "pass")
                mp = max(c["max_relative_deviation_primary"] for c in c_)
                ml = max(abs(c["metrics"]["lcoh_USD_per_kg"]["relative"]) for c in c_)
                ms = max(c["max_relative_deviation_secondary"] for c in c_)
                R.num("Aspen re-solve: candidates / converged / pass", (o["n"], o["nconv"], o["npass"]), f"{o['nconv']} of {o['n']} converged, {o['npass']} pass", va, "len(candidates); count(aspen_converged); count(status == 'pass')", TAG_ASPEN)
                o["prim_v"] = mp
                o["prim"] = R.num("Aspen re-solve: max primary-metric deviation", mp, f"{100*mp:.1f}%", va, "max(candidates[*].max_relative_deviation_primary)", TAG_ASPY)
                o["lcohdev"] = R.num("Aspen re-solve: max LCOH deviation", ml, f"{100*ml:.1f}%", va, "max |candidates[*].metrics.lcoh_USD_per_kg.relative|", TAG_ASPY)
                o["sec"] = R.num("Aspen re-solve: max secondary-metric deviation", ms, f"{100*ms:.0f}%", va, "max(candidates[*].max_relative_deviation_secondary)", TAG_ASPY)
                o["tol"] = R.num("Aspen re-solve pass tolerance", av["tolerance_relative"], f"{100*av['tolerance_relative']:.0f}%", va, "tolerance_relative", TAG_ASPEN)
                o["criterion"] = av.get("criterion", "")
                R.num("Aspen re-solve criterion (text)", None, o["criterion"][:60] + "...", va, "criterion", TAG_ASPEN)
                cl = next((c for c in c_ if c.get("id") == "opt_lcoh"), None)
                if cl:
                    o["lcoh_aspen"] = R.num("Min-LCOH point re-solved in Aspen: LCOH", cl["metrics"]["lcoh_USD_per_kg"]["aspen"], f"{cl['metrics']['lcoh_USD_per_kg']['aspen']:.2f}", va, "candidates[id=opt_lcoh].metrics.lcoh_USD_per_kg.aspen", TAG_ASPY)
                o["va"] = va
            else:
                R.pend("Aspen verification of optimisation candidates", rel(f_av))
            S["opt2"] = o
    else:
        R.pend("Optimisation result", rel(f_so))

    # legacy generic optimisation reader (disabled: replaced by the explicit reader above)
    opt_files = []
    S["opt"] = None
    if opt_files:
        lines = []
        opt_main = [f for f in opt_files if not re.search(r"pareto|verif", Path(f).name, re.I)] or opt_files
        d = load_json(Path(opt_main[0]))
        src = rel(opt_main[0])
        for lab, rx, unit, nd in (("Optimum T", r"reactor_temperature_C$", "°C", 0), ("Optimum P", r"reactor_pressure_bar$", "bar", 1),
                                  ("Objective", r"(objective_value|lcoh|specific_heat_demand|objective)", "", 3)):
            hit = deep_find(d, rx)
            if hit:
                shown = f"{hit[1]:,.{nd}f} {unit}".strip()
                R.num(f"Optimisation {lab}", hit[1], shown, src, hit[0], TAG_PY)
                lines.append((lab if lab != "Objective" else hit[0].split(".")[-1].replace("_", " "), shown))
        ver = [f for f in opt_files if re.search(r"verif|aspen", Path(f).name, re.I)]
        if ver:
            dv = load_json(Path(ver[0]))
            hit = deep_find(dv, r"(nh3_conversion|lcoh|specific_heat_demand)")
            if hit:
                shown = f"{hit[1]:,.3f}"
                R.num("Aspen verification of optimum", hit[1], shown, rel(ver[0]), hit[0], TAG_ASPEN)
                lines.append(("Aspen check: " + hit[0].split(".")[-1].replace("_", " "), shown))
        else:
            R.pend("Aspen verification of optimum", "results/optimisation/*verif*.json")
        par = [f for f in opt_files if re.search(r"pareto", Path(f).name, re.I)]
        if par:
            dp = load_json(Path(par[0]))
            pts = dp if isinstance(dp, list) else next((v for v in dp.values() if isinstance(v, list)), [])
            if pts:
                lines.append(("Pareto front", f"{len(pts)} points"))
                R.num("Pareto points", len(pts), str(len(pts)), rel(par[0]), "len(list)", TAG_PY)
        else:
            R.pend("Pareto front", "results/optimisation/*pareto*.json")
        S["opt"] = lines or None
        S["opt_src"] = src
        S["opt_fig"] = find_first(["results/figures/pareto*.png", "results/figures/opt*.png", "results/figures/*pareto*.png"])
        if not lines:
            R.pend("Optimisation result (unrecognised schema)", src)
    else:
        pass  # optimisation pending items are raised by the explicit reader above

    # economics
    f_eco = ROOT / "results/simulations/economics_baseline.json"
    S["eco"] = None
    if f_eco.exists():
        d = load_json(f_eco)
        hit = deep_find(d, r"^lcoh(_usd_per_kg|_per_kg|_usd_kg|$|.*kg)")
        if hit:
            unit = "USD/kg H2" if "eur" not in hit[0].lower() else "EUR/kg H2"
            eco = {"lcoh": R.num("LCOH", hit[1], f"{hit[1]:.3f}", rel(f_eco), hit[0], TAG_ASPY), "unit": unit, "src": rel(f_eco)}
            bd = None
            for kk in ("breakdown", "lcoh_breakdown", "breakdown_usd_per_kg", "components", "cost_breakdown"):
                h = deep_find(d, f"^{kk}$", numeric=False)
                if h and isinstance(h[1], dict):
                    items = [(str(a).replace("_usd_per_kg", "").replace("_", " "), float(b)) for a, b in h[1].items()
                             if isinstance(b, (int, float)) and not isinstance(b, bool)]
                    if items:
                        bd = items
                        R.num("LCOH breakdown", len(items), f"{len(items)} items", rel(f_eco), h[0], TAG_ASPY)
                        break
            if bd:  # merge items below 1 % of LCOH into "other", sort descending
                big = [(a, b) for a, b in bd if b >= 0.01 * hit[1]]
                small = sum(b for a, b in bd if b < 0.01 * hit[1])
                bd = sorted(big, key=lambda x: -x[1]) + ([("other (<1% each)", small)] if small > 0 else [])
                feed = next((b for a, b in bd if "ammonia" in a or "nh3" in a), None)
                if feed:
                    eco["feed_share"] = R.num("Ammonia feed share of LCOH", feed / hit[1], pct(feed / hit[1], 0), rel(f_eco), "breakdown ammonia_feed / lcoh", TAG_ASPY)
            eco["breakdown"] = bd
            extras = []
            h = deep_find(d, r"^nh3_price_USD_per_t$")
            if h:
                prov = (d.get("provenance") or {}).get("nh3_price_USD_per_t") or {}
                tag = "LIT" if prov.get("source") == "literature" else "ASSUMPTION"
                cite = f" ({short_apa(prov['citekey'])})" if prov.get("citekey") else ""
                extras.append(("NH3 price" + cite,f"{h[1]:,.0f} USD/t", tag))
                R.num("Economics NH3 price", h[1], f"{h[1]:,.0f} USD/t", rel(f_eco), h[0] + " + provenance", TAG_LIT if tag == "LIT" else TAG_ASM)
            h = deep_find(d, r"^total_capex_USD$")
            if h:
                extras.append(("total capital, literature correlation", f"USD {h[1]/1e6:.1f} M", "ASPY"))
                R.num("Economics total CAPEX", h[1], f"USD {h[1]/1e6:.1f} M", rel(f_eco), h[0], TAG_ASPY)
            eco["extras"] = extras
            S["eco"] = eco
        else:
            R.pend("LCOH value (key not recognised)", rel(f_eco))
    else:
        R.pend("Economics baseline (LCOH, breakdown)", rel(f_eco))
    S["tornado"] = None  # the deck draws the LCOH charts natively from the CSV/JSON results
    if not glob.glob(str(ROOT / "results/sensitivity/lcoh_*.csv")):
        R.pend("LCOH sensitivity tables", "results/sensitivity/lcoh_*.csv")

    f_env = ROOT / "results/simulations/environmental_baseline.json"
    S["env"] = None
    if f_env.exists():
        d = load_json(f_env)
        rows = ((d.get("comparison") or {}).get("rows")) if isinstance(d, dict) else None
        vals = [r.get("total_kgCO2e_per_kgH2") for r in (rows or []) if isinstance(r, dict)]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if vals:
            shown = f"{min(vals):.2f}-{max(vals):.2f}"
            S["env"] = R.num("Carbon intensity range over scenarios", (min(vals), max(vals)), shown, rel(f_env), f"comparison.rows[*].total_kgCO2e_per_kgH2 ({len(vals)} scenarios)", TAG_ASPY)
            S["env_n"] = len(vals)
        else:
            hit = deep_find(d, r"(total_kgCO2e_per_kgH2|carbon_intensity)")
            if hit:
                S["env"] = R.num("Carbon intensity", hit[1], f"{hit[1]:.2f}", rel(f_env), hit[0], TAG_ASPY)
                S["env_n"] = 1
            else:
                R.pend("Carbon intensity (key not recognised)", rel(f_env))
    else:
        R.pend("Environmental baseline (carbon intensity)", rel(f_env))

    # kinetics / PFR
    f_pfr = ROOT / "results/simulations/pfr_baseline.json"
    S["pfr"] = None
    if f_pfr.exists():
        d = load_json(f_pfr)
        cases = d.get("cases", {}) if isinstance(d, dict) else {}
        T0 = load_json(ROOT / "results/simulations/baseline.json")["inputs"]["reactor_temperature_C"]
        found = {}
        for key, c in cases.items():
            cat = str(c.get("catalyst_id", "")) if isinstance(c, dict) else ""
            if (isinstance(c, dict) and "takahashi" in cat and c.get("T_C") is not None and float(c["T_C"]) == T0
                    and c.get("mode", "isothermal") == "isothermal" and c.get("W_99pct_eq_kg")):
                found[cat[:2]] = (key, c)
        if "ni" in found and "ru" in found:
            pf = {}
            for m in ("ni", "ru"):
                key, c = found[m]
                pf[m] = R.num(f"{m.capitalize()} catalyst mass to 99% of equilibrium at baseline T (kinetic PFR)", c["W_99pct_eq_kg"],
                              f"{c['W_99pct_eq_kg']:.0f} kg", rel(f_pfr), f"cases['{key}'].W_99pct_eq_kg", TAG_PY)
            pf["ratio"] = found["ni"][1]["W_99pct_eq_kg"] / found["ru"][1]["W_99pct_eq_kg"]
            R.num("Ni / Ru catalyst-mass ratio (derived)", pf["ratio"], f"{pf['ratio']:.1f}", rel(f_pfr), "W_99pct_eq_kg ni / ru", TAG_PY)
            pf["cite"] = short_apa("takahashi2016kinetic")
            S["pfr"] = pf
        else:
            R.pend("Kinetic PFR result (Ni and Ru isothermal cases at baseline T)", rel(f_pfr))
    else:
        R.pend("Kinetic PFR result (optional on slide 8)", rel(f_pfr))

    # validation matrix
    f_vm = ROOT / "results/validation/validation_matrix.json"
    S["vm"] = None
    if f_vm.exists():
        d = load_json(f_vm)
        rows = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
        counts: dict[str, int] = {}
        for r in rows:
            if isinstance(r, dict) and "status" in r:
                counts[str(r["status"]).lower()] = counts.get(str(r["status"]).lower(), 0) + 1
        if not counts and isinstance(d, dict):
            h = deep_find(d, r"^(counts|summary|by_status)$", numeric=False)
            if h and isinstance(h[1], dict):
                counts = {str(a).lower(): int(b) for a, b in h[1].items() if isinstance(b, (int, float))}
        if counts:
            tot = sum(counts.values())
            summ = d.get("summary", {}) if isinstance(d, dict) else {}
            if summ.get("n_items") is not None and int(summ["n_items"]) != tot:
                R.warn(f"validation_matrix.json summary.n_items={summ['n_items']} differs from item count {tot}; item counts used")
            # failure families, named from the item id prefix (never rounded away: every failing item is counted)
            fam_name = {"FS": "flowsheet duties vs the Python model (feed section, cooler)",
                        "KIN": "literature kinetics reproduction", "OPT": "Aspen re-solve of the optimum (secondary duties)",
                        "SECTION": "a validation section that crashed"}
            fams: dict[str, int] = {}
            for r in rows:
                if isinstance(r, dict) and str(r.get("status", "")).lower() == "fail":
                    pre = str(r.get("id", "?")).split("-")[0]
                    fams[fam_name.get(pre, pre)] = fams.get(fam_name.get(pre, pre), 0) + 1
            fam_key = "items[status == fail].id prefix"
            # prefer the documented root causes in summary.failure_root_causes (counts checked against the items)
            # neutral wording (fact sheet F11): a model-form difference, not a verdict on either model
            kin_tol = next((i.get("tolerance") for i in rows if isinstance(i, dict) and i.get("root_cause") == "kinetics_figure_predictions"), None)
            kin_max = max((i.get("value") or 0 for i in rows if isinstance(i, dict) and i.get("root_cause") == "kinetics_figure_predictions"), default=None)
            cause_name = {"feed_section_enthalpy": "flowsheet cross-checks (different feed-section property models)",
                          "kinetics_figure_predictions": (f"kinetics curve reproductions (about {kin_max:.2f} vs a {kin_tol:g} tolerance)"
                                                          if kin_tol and kin_max else "kinetics curve reproductions outside tolerance")}
            if kin_tol and kin_max:
                R.num("Kinetics reproduction: worst deviation vs tolerance", (kin_max, kin_tol), f"{kin_max:.2f} vs {kin_tol:g}", rel(f_vm),
                      "items[root_cause == kinetics_figure_predictions].value (max), .tolerance", TAG_PY)
            rc = summ.get("failure_root_causes") or []
            if rc and sum(int(c.get("n_items", 0)) for c in rc) == counts.get("fail", 0):
                fams = {cause_name.get(c["cause"], c["cause"].replace("_", " ")): int(c["n_items"]) for c in rc}
                fam_key = "summary.failure_root_causes[*].{cause, n_items}"
            elif rc:
                R.warn("validation_matrix.json failure_root_causes do not add up to the failing item count; id prefixes used")
            fams = dict(sorted(fams.items(), key=lambda x: -x[1]))
            S["vm"] = {"total": tot, "counts": counts, "families": fams, "generated": d.get("generated_utc") if isinstance(d, dict) else None}
            R.num("Validation matrix items by status", tot, str(tot), rel(f_vm), "items[*].status counts: " + json.dumps(counts), TAG_ASPY)
            R.num("Validation failure families", sum(fams.values()), json.dumps(fams), rel(f_vm), fam_key, TAG_ASPY)
        else:
            R.pend("Validation matrix counts (schema not recognised)", rel(f_vm))
    else:
        R.pend("Validation matrix (counts by status)", rel(f_vm))

    # dashboard screenshots
    shots = sorted(glob.glob(str(ROOT / "docs/screenshots/dashboard_*.png")))
    pfd = [s for s in shots if re.search(r"pfd|flowsheet", Path(s).name, re.I)]
    other = [s for s in shots if s not in pfd]
    order = ["overview", "simulation", "sensitivity", "reactor", "heat", "validation"]
    pref = sorted(other, key=lambda s: (next((i for i, k in enumerate(order) if k in Path(s).stem.lower()), 99), s))
    exact = [s for s in pfd if Path(s).name.lower() == "dashboard_pfd.png"]
    pfd = exact + [s for s in pfd if s not in exact]
    ov = [s for s in shots if Path(s).name.lower() == "dashboard_overview.png"]
    pref = ov + [s for s in pref if s not in ov]
    S["dash_pfd"] = Path(pfd[0]) if pfd else None
    # slide 9 shows the interactive side of the dashboard: a stream panel opened on the PFD (falls back to any page)
    panel = [s for s in shots if Path(s).name.lower() == "dashboard_pfd_stream_panel.png"]
    S["dash_main"] = Path(panel[0]) if panel else (Path(pref[0]) if pref else (Path(pfd[0]) if pfd else None))
    S["dash_count"] = len(shots)
    if not S["dash_main"]:
        R.pend("Dashboard screenshot (slide 9)", "docs/screenshots/dashboard_*.png")

    # public website screenshots (re-captured by another engineer: whatever is on disk at build time is used)
    sd = ROOT / "docs/screenshots"
    S["site_desk"] = next((sd / n for n in ("site_home_desktop.png", "site_results_desktop.png", "site_pfd_desktop.png") if (sd / n).exists()), None)
    S["site_mob"] = next((sd / n for n in ("site_home_mobile.png", "site_home_phone.png") if (sd / n).exists()), None)
    for lab, pth in (("Website screenshot, desktop (slide 10)", S["site_desk"]), ("Website screenshot, phone (slide 10)", S["site_mob"]),
                     ("Dashboard screenshot (slide 9)", S["dash_main"])):
        if pth:
            R.num(lab, None, pth.name, rel(pth), "file modified " + time.strftime("%Y-%m-%d %H:%M", time.localtime(pth.stat().st_mtime)), "[screenshot]")
    if not S["site_desk"]:
        R.pend("Public website screenshot (slide 10)", "docs/screenshots/site_home_desktop.png")
    if not S["site_mob"]:
        R.pend("Public website mobile screenshot (slide 10)", "docs/screenshots/site_home_mobile.png")


def collect_more(S: dict) -> None:
    """Numbers added for the finished project (public website, regenerated results after the engineering review)."""
    # --- evidence: Aspen runs behind the results (fact sheet F8), all computed from the files
    sims = []
    for f in sorted(glob.glob(str(ROOT / "results/simulations/*.json"))):
        d = load_json(Path(f))
        if d.get("source") == "aspen_plus_v15":
            st = d.get("status") or {}
            sims.append(bool(st.get("converged")) and not st.get("has_errors"))
    sens_rows = []
    for f in sorted(glob.glob(str(ROOT / "results/sensitivity/aspen_*.csv"))):
        if "native" in Path(f).name:
            continue
        for r in read_csv(Path(f)):
            sens_rows.append(str(r.get("converged", "")).lower() == "true")
    grid = read_csv(ROOT / "results/validation/equilibrium_aspen_grid.csv")
    grid_ok = []
    for r in grid:
        try:
            grid_ok.append(math.isfinite(float(r["nh3_conversion"])))
        except (TypeError, ValueError):
            grid_ok.append(False)
    n_runs = len(sims) + len(sens_rows) + len(grid_ok)
    n_conv = sum(sims) + sum(sens_rows) + sum(grid_ok)
    S["runs"] = {"n": n_runs, "conv": n_conv, "sims": len(sims), "all": n_runs == n_conv}
    R.num("Aspen runs behind the results", n_runs, str(n_runs), "results/simulations/*.json (source == aspen_plus_v15) + results/sensitivity/aspen_*.csv (excl. native) + results/validation/equilibrium_aspen_grid.csv",
          f"{len(sims)} flowsheet cases + {len(sens_rows)} sensitivity rows + {len(grid_ok)} grid points", TAG_ASPEN)
    R.num("Aspen runs converged", n_conv, f"{n_conv} of {n_runs}", "same files", "status.converged and not has_errors; csv converged == True; grid nh3_conversion finite", TAG_ASPEN)

    # --- equilibrium agreement, like for like (fact sheet F12)
    f_cmp = ROOT / "results/validation/equilibrium_comparison.csv"
    pairs = {}
    for r in read_csv(f_cmp):
        k = (r["aspen_property_method"], r["python_eos"])
        try:
            v = abs(float(r["nh3_conversion_abs_dev_pp"]))
        except ValueError:
            continue
        m, n = pairs.get(k, (0.0, 0))
        pairs[k] = (max(m, v), n + 1)
    pr, idl = pairs[("PENG-ROB", "pr")], pairs[("IDEAL", "ideal")]
    S["eq_pr"] = R.num("Equilibrium gap Aspen PENG-ROB vs Python PR", pr[0], f"{pr[0]:.2f} pp", rel(f_cmp), f"max |nh3_conversion_abs_dev_pp| (PENG-ROB~pr, {pr[1]} points)", TAG_ASPY)
    S["eq_id"] = R.num("Equilibrium gap Aspen IDEAL vs Python ideal gas", idl[0], f"{idl[0]:.2f} pp", rel(f_cmp), f"max |nh3_conversion_abs_dev_pp| (IDEAL~ideal, {idl[1]} points)", TAG_ASPY)
    S["eq_pr_n"], S["eq_id_n"] = pr[1], idl[1]

    # --- public website and platform (counted from the frontend source; links from README.md)
    routes = (ROOT / "frontend/src/site/routes.ts").read_text(encoding="utf-8")
    block = routes[routes.index("SITE_ROUTES"):]
    block = block[block.index("= [") + 3:]
    block = block[:block.index("\n]")]
    n_sec = len(re.findall(r"\{\s*path:\s*'", block))
    S["site_sections"] = R.num("Public website sections", n_sec, str(n_sec), "frontend/src/site/routes.ts", "len(SITE_ROUTES)", "[code]")
    shell = (ROOT / "frontend/src/components/Shell.tsx").read_text(encoding="utf-8")
    n_pages = len(re.findall(r"\{\s*path:\s*platformPath\(", shell))
    S["dash_pages"] = R.num("Dashboard pages", n_pages, str(n_pages), "frontend/src/components/Shell.tsx", "count of platformPath( nav entries", "[code]")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m_site = re.search(r"https://[\w.-]+\.github\.io/AmCraX/", readme)
    m_repo = re.search(r"https://github\.com/[\w.-]+/AmCraX(?=[/\"'\s)])", readme)
    S["url_site"] = m_site.group(0) if m_site else None
    S["url_repo"] = m_repo.group(0) if m_repo else None
    for lab, v in (("Public website address", S["url_site"]), ("Repository address", S["url_repo"])):
        if v:
            R.num(lab, v, v, "README.md", "first matching link", "[code]")
        else:
            R.pend(lab, "README.md")

    # --- economics: price sensitivity, NH3-price range, literature benchmarks (separate, labelled)
    eco = S.get("eco")
    f_eco = ROOT / "results/simulations/economics_baseline.json"
    if eco and f_eco.exists():
        d = load_json(f_eco)
        bd = d["breakdown_USD_per_kg"]
        eco["bd"] = {k: bd[k] for k in ("ammonia_feed", "capex", "imported_heat", "fixed_opex")}
        for k, v in eco["bd"].items():
            R.num(f"LCOH component {k}", v, f"{v:.2f}", rel(f_eco), f"breakdown_USD_per_kg.{k}", TAG_ASPY)
        eco["price"] = d["assumptions"]["nh3_price_USD_per_t"]
        f_pr = ROOT / "results/sensitivity/lcoh_vs_ammonia_price_baseline.csv"
        rows = [(float(r["nh3_price_USD_per_t"]), float(r["lcoh_USD_per_kg"])) for r in read_csv(f_pr)]
        rows.sort()
        slope = (rows[-1][1] - rows[0][1]) / (rows[-1][0] - rows[0][0]) * 100
        eco["curve"] = rows
        eco["slope"] = R.num("LCOH change per 100 USD/t NH3", slope, f"+{slope:.2f} USD/kg", rel(f_pr), "(lcoh[max] - lcoh[min]) / (price[max] - price[min]) x 100", TAG_ASPY)
        eco["floor"] = R.num("LCOH at zero ammonia price", rows[0][1], f"{rows[0][1]:.2f} USD/kg", rel(f_pr), "lcoh_USD_per_kg at nh3_price_USD_per_t == 0", TAG_ASPY)
        R.num("Ammonia price curve", len(rows), f"{len(rows)} points, {rows[0][0]:.0f}-{rows[-1][0]:.0f} USD/t", rel(f_pr), "nh3_price_USD_per_t, lcoh_USD_per_kg", TAG_ASPY)
        f_tor = ROOT / "results/sensitivity/lcoh_tornado_baseline.csv"
        tr = next(r for r in read_csv(f_tor) if r["parameter"] == "nh3_price_USD_per_t")
        lo, hi = float(tr["low_value"]), float(tr["high_value"])
        llo, lhi = float(tr["lcoh_at_low_USD_per_kg"]), float(tr["lcoh_at_high_USD_per_kg"])
        cite_m = re.match(r"([a-z]+\d{4}[a-z]+)", tr.get("range_source", ""))
        eco["range_cite"] = short_apa(cite_m.group(1)) if cite_m else ""
        eco["range"] = R.num("LCOH over the literature NH3 price range", (lo, hi, llo, lhi), f"{llo:.2f}-{lhi:.2f} USD/kg at {lo:.0f}-{hi:.0f} USD/t",
                             rel(f_tor), "parameter == nh3_price_USD_per_t: low/high_value, lcoh_at_low/high_USD_per_kg (range: " + tr.get("range_source", "") + ")", TAG_ASPY)
        eco["range_lo"], eco["range_hi"] = lo, hi
        # literature LCOH at comparable ammonia price (within the tornado price range), never mixed with AmCraX values
        lb = [b for b in d.get("literature_benchmarks", []) if not b.get("kind") and b.get("nh3_price_USD_per_t")
              and lo <= float(b["nh3_price_USD_per_t"]) <= hi]
        if lb:
            vmin, vmax = min(b["value"] for b in lb), max(b["value"] for b in lb)
            pmin, pmax = min(b["nh3_price_USD_per_t"] for b in lb), max(b["nh3_price_USD_per_t"] for b in lb)
            cites = list(dict.fromkeys(short_apa(b["citekey"]) for b in lb))
            eco["lit"] = {"v": f"{vmin:.1f}-{vmax:.1f}", "p": f"{pmin:.0f}-{pmax:.0f}", "cites": cites, "n": len(lb)}
            R.num("Published LCOH at comparable NH3 price (literature)", (vmin, vmax), f"{vmin:.1f}-{vmax:.1f} USD/kg ({len(lb)} values, {pmin:.0f}-{pmax:.0f} USD/t)",
                  rel(f_eco), "literature_benchmarks[kind absent, nh3_price within tornado range].value; " + "; ".join(f"{b['citekey']} p.{b['page']} {b['locator']}" for b in lb), TAG_LIT)
        else:
            eco["lit"] = None
            R.pend("Literature LCOH benchmarks at comparable NH3 price", rel(f_eco))
        eco["nh3_kg"] = R.num("kg NH3 feed per kg H2", d["kg_nh3_feed_per_kg_h2"], f"{d['kg_nh3_feed_per_kg_h2']:.2f}", rel(f_eco), "kg_nh3_feed_per_kg_h2", TAG_ASPY)
        eco["nh3_floor"] = R.num("Stoichiometric floor kg NH3 per kg H2", d["stoichiometric_floor_kg_nh3_per_kg_h2"], f"{d['stoichiometric_floor_kg_nh3_per_kg_h2']:.2f}", rel(f_eco), "stoichiometric_floor_kg_nh3_per_kg_h2", "[computed]")
        f_nohi = ROOT / "results/simulations/economics_baseline_no_hi.json"
        if f_nohi.exists():
            v = load_json(f_nohi)["lcoh_USD_per_kg"]
            eco["nohi"] = R.num("LCOH without the exchanger", v, f"{v:.3f}", rel(f_nohi), "lcoh_USD_per_kg", TAG_ASPY)

    # --- optimisation: per-candidate Aspen re-solve deviations
    o = S.get("opt2")
    f_av = ROOT / "results/optimisation/aspen_verification.json"
    if o and f_av.exists():
        av = load_json(f_av)
        names = {"opt_lcoh": "min LCOH", "opt_lcoh_tp": "min LCOH (T, P only)", "opt_eff": "max LHV efficiency", "opt_heat": "min heat demand",
                 "opt_h2": "max H2 output", "opt_conv": "max conversion"}
        bars = []
        for c in av["candidates"]:
            cid = c.get("id", "?")
            lab = names.get(cid, re.sub(r"^par_(\d+)$", r"Pareto point \1", cid))
            bars.append((lab, round(100 * c["max_relative_deviation_primary"], 3)))
        o["bars"] = bars
        R.num("Aspen re-solve deviation per candidate", len(bars), f"{len(bars)} bars", rel(f_av), "candidates[*].max_relative_deviation_primary", TAG_ASPY)
        ml = o.get("lcohdev")
        mlv = max(abs(c["metrics"]["lcoh_USD_per_kg"]["relative"]) for c in av["candidates"])
        o["lcoh_up"] = math.ceil(mlv * 1000 - 1e-9) / 10
        R.num("Aspen re-solve: LCOH deviation shown (rounded up)", o["lcoh_up"], f"{o['lcoh_up']:.1f}%", rel(f_av), "ceil(max |candidates[*].metrics.lcoh_USD_per_kg.relative|, 0.1 %)", TAG_ASPY)
        o["prim_up"] = math.ceil(o["prim_v"] * 1000 - 1e-9) / 10
        R.num("Aspen re-solve: primary deviation shown (rounded up)", o["prim_up"], f"{o['prim_up']:.1f}%", rel(f_av), "ceil(max(candidates[*].max_relative_deviation_primary), 0.1 %)", TAG_ASPY)
        o["tol_v"] = 100 * av["tolerance_relative"]


# ----------------------------------------------------------------------------- slides
def spoken(t: str) -> str:
    """Speaker notes are read aloud: units and ranges in spoken form (numbers stay as read from the files)."""
    t = re.sub(r"(\d)\s?%", r"\1 percent", t)
    t = re.sub(r"(\d)\s?°C", r"\1 degrees", t)
    t = re.sub(r"(\d) kmol/h", r"\1 kilomoles per hour", t)
    t = re.sub(r"(\d) kW\b", r"\1 kilowatts", t)
    t = re.sub(r"(\d) K\b", r"\1 kelvin", t)
    t = re.sub(r"(\d) ppm\b", r"\1 parts per million", t)
    t = re.sub(r"(\d)-(\d)", r"\1 to \2", t)
    return t


def src_line(cites: list[str], tags: list[str], extra: str = "") -> str:
    parts = []
    if cites:
        parts.append("Sources: " + "; ".join(dict.fromkeys(cites)) + ".")
    if extra:
        parts.append(extra)
    parts.append(" ".join(dict.fromkeys(tags)))
    return " ".join(parts)


def build_slides(S: dict) -> list[dict]:
    L = S["L"]
    T, P = S["T"], S["P"]
    sl: list[dict] = []
    files_aspen = "results/simulations/baseline.json"
    runs = S["runs"]
    runs_txt = f"{runs['n']} Aspen runs" + (", all converged" if runs["all"] else f", {runs['conv']} converged")
    tests = S.get("n_tests") or {}
    vm = S.get("vm")
    o = S.get("opt2")
    eco = S.get("eco")
    pf = S.get("pfr")
    sp = lambda s: s.replace(" pp", " percentage points")  # noqa: E731  spoken form

    # 1 -------------------------------------------------------------- title
    stats = [
        {"v": S["conv"], "l": f"NH3 conversion, {T}, {P}", "tag": "ASPEN"},
        {"v": S["h2kg"], "l": "H2 product, baseline flowsheet", "tag": "ASPEN"},
        {"v": S["lhv"], "l": "first-law LHV efficiency, heat-integrated", "tag": "ASPEN"},
        {"v": str(runs["n"]), "l": "Aspen runs" + (", all converged" if runs["all"] else f", {runs['conv']} converged"), "tag": "ASPEN"},
    ]
    sl.append(dict(id="title", section="", title="AmCraX",
                   subtitle="Ammonia Cracking Simulation and Optimisation Platform",
                   value="From liquid ammonia to hydrogen: a rigorous Aspen Plus V15 flowsheet, an independent Python cross-check, an interactive dashboard and a public website, with the source of every number shown.",
                   pillars=["Aspen Plus V15 engine", "Independent Python models", "FastAPI + React Flow platform", "Public results website"],
                   stats=stats,
                   source=src_line([], [TAG_ASPEN], f"Baseline case {S['feed']} liquid NH3; results from {files_aspen}; run count from results/simulations, results/sensitivity and the equilibrium grid."),
                   notes=(f"AmCraX is our ammonia cracking simulation and optimisation platform. Aspen Plus V15 is the engine, an independent Python model checks it, "
                          f"and a dashboard and a public website show the results. At {T} and {P}, Aspen converts {S['conv']} of the ammonia into about "
                          f"{S['h2kg_n']} kilograms of hydrogen per hour, and {runs['n']} Aspen runs stand behind the deck. "
                          f"The honest limit: this is a steady-state design study, not a plant design.")))

    # 2 -------------------------------------------------------------- challenge
    cards = [
        {"v": f"{L['comp']['shown']} kWh/kg", "l": "to compress H2 from 1 to 700 bar", "tag": "LIT", "c": "accent"},
        {"v": f"{L['loss']['shown']}%", "l": "H2 lost in transport and handling (LCA inventory)", "tag": "LIT", "c": "h2"},
        {"v": f"{L['hrs']['shown']} kg/day", "l": "H2 per refuelling station, delivered at 350 bar", "tag": "LIT", "c": "primary"},
        {"v": f"{L['iso_nh3']['shown']} ppm", "l": "max NH3 in fuel-cell H2 (ISO 14687:2019)", "tag": "LIT", "c": "nh3"},
    ]
    bullets = [("Light gas", "Hydrogen must be compressed or liquefied before it moves in bulk"),
               ("Energy penalty", "Compression alone costs several kWh per kilogram"),
               ("Losses", "Every handling step leaks product"),
               ("Strict quality", "Fuel cells tolerate almost no ammonia or nitrogen")]
    sl.append(dict(id="challenge", section="The problem", title="Moving hydrogen is harder than making it",
                   cards=cards, bullets=bullets,
                   source=src_line([L["comp"]["cite"], L["loss"]["cite"], L["hrs"]["cite"], L["iso_nh3"]["cite"]], [TAG_LIT],
                                   "Literature values, not AmCraX results."),
                   notes=(f"Hydrogen is easy to make and hard to move. Compressing it from one to seven hundred bar costs about {L['comp']['shown']} "
                          f"kilowatt-hours per kilogram, and one life-cycle study assumes {L['loss']['shown']} percent is lost on the way. A refuelling "
                          f"station needs around {L['hrs']['shown']} kilograms a day at 350 bar, and fuel cells accept only {L['iso_nh3']['shown']} ppm ammonia. "
                          f"These are literature figures, not our results.")))

    # 3 -------------------------------------------------------------- why ammonia
    kpis = [
        {"v": f"{S['h2wt_v']} wt%", "l": "hydrogen by mass in NH3 (stoichiometry)", "tag": "COMPUTED", "c": "nh3"},
        {"v": S["h2vol"], "l": f"H2 carried per m³ of liquid NH3 ({L['rho_nh3']['shown']} kg/m³)", "tag": "LIT", "c": "primary"},
        {"v": f"{L['p_store']['shown']} bar", "l": "to keep NH3 liquid at 25 °C", "tag": "LIT", "c": "accent"},
    ]
    sl.append(dict(id="ammonia", section="The carrier", title="Ammonia carries hydrogen as an easy-to-store liquid",
                   kpis=kpis,
                   chart={"labels": ["NH3 molecule (17.03 g/mol)"], "h": S["h2wt_v"], "n": round(100 - S["h2wt_v"], 1)},
                   takeaway=[("No carbon", "the only other atom is nitrogen, released as N2"),
                             (f"{S['h2_per_t']} of H2", "in every tonne of ammonia"),
                             ("Mild storage", f"liquid at {L['p_store']['shown']} bar and 25 °C; boil-off about {L['boiloff']['shown']}%/day")],
                   source=src_line([L["rho_nh3"]["cite"], L["p_store"]["cite"], L["boiloff"]["cite"]], [TAG_LIT, TAG_ASM],
                                   "H2 mass fraction computed from standard atomic masses (3 x 1.008 / 17.031); boil-off is the cited study's assumption."),
                   notes=(f"Why ammonia? By mass it is {S['h2wt_v']} percent hydrogen, and the only other atom is nitrogen, so there is no carbon to manage. "
                          f"It stays liquid at about {L['p_store']['shown']} bar at room temperature, so one cubic metre carries roughly "
                          f"{S['h2vol'].split()[0]} kilograms of hydrogen. Those density and pressure values are from the literature. "
                          f"The catch is that ammonia is toxic and the hydrogen still has to be released.")))

    # 4 -------------------------------------------------------------- why cracking
    e_ext, e_lh2 = float(L["e_ext"]["value"]), L["e_lh2"]
    sl.append(dict(id="cracking", section="The conversion step", title="Cracking releases the hydrogen, but it costs heat",
                   left={"head": "Why crack", "eq": "NH3  →  ½ N2  +  1.5 H2",
                         "items": [("Endothermic", f"ΔH ≈ {L['dh']['shown']} kJ per mol NH3"),
                                   ("Equilibrium", "favoured by high temperature, low pressure"),
                                   ("Product", f"{S['y_h2_stoich']} H2 and {S['y_n2_stoich']} N2 by mole at full conversion"),
                                   ("At scale", f"commercial units up to {L['topsoe']['shown']} t H2/day; TRL {L['trl']['shown']}")]},
                   chart={"labels": ["Crack NH3", "Evaporate liquid H2"], "values": [e_ext, e_lh2 or 0],
                          "title": "Energy to release H2 (kJ per mol H2)"},
                   right_head="What cracking costs",
                   takeaway="Heat supply and recovery decide whether ammonia is a good hydrogen carrier.",
                   source=src_line([L["dh"]["cite"], L["e_ext"]["cite"], L["topsoe"]["cite"]], [TAG_LIT], "Literature values, not AmCraX results."),
                   notes=(f"To use the hydrogen we crack ammonia back into nitrogen and hydrogen. The reaction absorbs about {L['dh']['shown']} kilojoules "
                          f"per mole, so releasing hydrogen takes around {e_ext:g} kilojoules per mole of hydrogen, versus under one for evaporating "
                          f"liquid hydrogen. Industry already offers large crackers, but the technology readiness is quoted at only {L['trl']['shown']}. "
                          f"Heat is therefore the design problem AmCraX targets.")))

    # 5 -------------------------------------------------------------- introducing AmCraX
    mods = S["py_mods"]
    if tests.get("pass") is not None:
        note = f"{tests['pass']} Python tests pass" + (f"; {tests['skip']} opt-in live-Aspen test skipped" if tests.get("skip") == 1 else (f"; {tests['skip']} skipped" if tests.get("skip") else "")) \
               + (f"; {tests['fail']} failing" if tests.get("fail") else "")
    elif tests.get("total"):
        note = f"{tests['total']} automated tests collected"
    else:
        note = "Automated test count: RESULT PENDING"
    sl.append(dict(id="intro", section="The solution", title="Rigorous simulation, independent checks, open results",
                   chips=[("Feed conditioning", "nh3"), ("Cracking", "accent"), ("Heat recovery", "cold"), ("H2 purification", "h2")],
                   cards=[("Aspen Plus V15 engine", "RGibbs cracker and PENG‑ROB, generated and run from Python", "ASPEN"),  # non-breaking hyphen
                          ("Independent Python", f"{len(mods)} model packages recompute the physics to check Aspen", "PYTHON"),
                          ("Platform", f"FastAPI backend ({S['n_endpoints']} API paths) and a {S['dash_pages']}-page React Flow dashboard", "CODE"),
                          ("Public website", f"{S['site_sections']} sections of published results, no install needed", "CODE")],
                   note=note, pending_note=not bool(tests),
                   source=src_line([], [TAG_ASPEN, TAG_PY], "Architecture counted from the repository at build time (backend/amcrax, frontend/src); tests: results/validation/pytest_junit.xml."),
                   notes=(f"AmCraX has four parts. Aspen Plus V15 solves the flowsheet, with the input files generated and run from Python. An independent set of "
                          f"{len(mods)} Python packages recomputes the physics so we check Aspen rather than trust it. A FastAPI backend and a dashboard with "
                          f"{S['dash_pages']} pages let you explore every case, and a public website shows the published results. "
                          + (f"{tests['pass']} Python tests pass. " if tests.get("pass") else "")
                          + "It is a design-study tool, not a control system.")))

    # 6 -------------------------------------------------------------- PFD (native, editable, drawn from the flowsheet definition)
    fs = load_json(ROOT / "config/flowsheet.json")
    sl.append(dict(id="pfd", section="The process", title="One flowsheet: liquid ammonia in, purified hydrogen out",
                   flowsheet=fs, screenshot=None,
                   chips=[("Feed", f"{S['feed']} liquid NH3", "nh3"), ("Cracker", f"RGibbs, {T}, {P}", "accent"),
                          ("PSA (reduced-order)", f"H2 recovery {S['rec']} assumed; literature {L['psa_note']}", "h2"), ("Burner", f"tail gas, {S['excess_air']} excess air", "heat")],
                   caption="Drawn from config/flowsheet.json, the same topology as the Aspen model",
                   source=src_line([], [TAG_ASPEN, TAG_ASM], "Topology: config/flowsheet.json; conditions: results/simulations/baseline.json. PSA recovery is an assumption."),
                   notes=(f"Here is the whole process. Liquid ammonia at {S['feed']} is pumped, vaporised and preheated by the hot product gas in a "
                          f"feed-effluent exchanger, then cracked at {T} and {P}. The cooled gas goes to a PSA unit that recovers "
                          f"{S['rec']} of the hydrogen, and the tail gas is burned to supply heat. The PSA is a reduced-order split, not a designed adsorber, "
                          f"and its {S['rec']} recovery is our assumption, above the {L['psa_note']} reported in the literature.")))

    # 7 -------------------------------------------------------------- Aspen
    shot = ROOT / "aspen/screenshots/01_flowsheet.png"
    man = load_json(ROOT / "aspen/screenshots/manifest.json")
    cap = next((c for c in man["captures"] if c["file"] == "01_flowsheet.png"), {})
    ev = S["ev"]
    sl.append(dict(id="aspen", section="Aspen Plus simulation", title="Aspen Plus V15 solves the full flowsheet in seconds",
                   screenshot=img_info(shot), caption=f"Genuine Aspen Plus V15 screenshot (1 of {ev['shots']} GUI captures): " + cap.get("title", "Main Flowsheet"),
                   chips=[(f"RGibbs cracker, {S['method']}", "accent"), (f"{S['converged']}, {S['engine_s']}", "ok"),
                          (runs_txt.replace(" Aspen runs", " runs"), "primary"),
                          (f"{ev['sens']} sweep runs, {ev['grid']}-pt grid", "n2"),
                          (f"{ev['scn']} scenarios, {ev['opt']} optima", "h2")],
                   source=src_line([], [TAG_ASPEN], f"Counts at build time: results/simulations/*.json, results/sensitivity/aspen_*.csv, equilibrium_aspen_grid.csv ({ev['grid_methods']}), "
                                   "optimisation/aspen_verification.json, aspen/screenshots/manifest.json."),
                   notes=(f"This is a genuine Aspen Plus V15 screenshot of our model, not a mock-up. The cracker is an RGibbs equilibrium reactor with "
                          f"the Peng-Robinson method, and the baseline converges without errors in about {S['engine_s'].replace(' s', '')} seconds. "
                          f"Behind the deck are {runs['n']} Aspen runs: {S['runs']['sims']} flowsheet cases, {ev['sens']} sensitivity runs and a {ev['grid']}-point equilibrium grid"
                          + (", all converged. " if runs["all"] else ". ")
                          + "An equilibrium reactor is optimistic: a real catalyst bed may not reach it.")))

    # 8 -------------------------------------------------------------- reactor and kinetics
    fig = fig_equilibrium(FIG / "equilibrium_conversion.png")
    k8 = [{"v": S["eq_pr"], "l": f"max gap, Peng-Robinson in both ({S['eq_pr_n']} points)", "tag": "ASPY", "c": "python"},
          {"v": S["eq_id"], "l": f"max gap, ideal gas in both ({S['eq_id_n']} points)", "tag": "ASPY", "c": "primary"}]
    if pf:
        k8.append({"v": f"{pf['ni']} vs {pf['ru']}", "l": f"Ni vs Ru catalyst to 99% of equilibrium, {T}", "tag": "PYTHON", "c": "accent"})
    sl.append(dict(id="reactor", section="Reactor and kinetics", title="Two independent models agree on equilibrium; kinetics size the bed",
                   kpis=k8, figure=fig, fig_title="Equilibrium conversion: Python curves, Aspen RGibbs points (PENG-ROB)",
                   takeaway=[("Like for like", f"same property basis, {S['eq_range']}"),
                             ("Kinetics", ("Ni/MgO and Ru/MgO microkinetics, Python plug-flow reactor" if pf else "kinetic plug-flow reactor pending")),
                             ("Limit", "kinetics fitted at 1 atm, extrapolated to 20 bar")],
                   pending=None if pf else "kinetic PFR check (results/simulations/pfr_baseline.json)",
                   source=src_line([pf["cite"]] if pf else [], [TAG_ASPEN, TAG_PY, TAG_ASPY, TAG_LIT], "results/validation/equilibrium_*_grid.csv, equilibrium_comparison.csv"
                                   + ("; results/simulations/pfr_baseline.json (Python model, literature kinetics)." if pf else ".")),
                   notes=(f"To trust Aspen we rebuilt the equilibrium independently in Python and compared like with like. With Peng-Robinson in both, the "
                          f"largest gap over {S['eq_pr_n']} points is {sp(S['eq_pr'])}; with ideal gas in both it is {sp(S['eq_id'])}. "
                          + (f"A kinetic plug-flow model then sizes the bed: about {pf['ni'].replace(' kg', '')} kilograms of nickel catalyst against "
                             f"{pf['ru'].replace(' kg', '')} of ruthenium to reach 99 percent of equilibrium. " if pf else "")
                          + "The limit: those kinetics were fitted at one atmosphere and are extrapolated to 20 bar.")))

    # 9 -------------------------------------------------------------- dashboard
    dm = S["dash_main"]
    dshot = crop_info(dm, (0.0, 0.06, 1.0, 1.0), "slide") if dm else None
    sl.append(dict(id="dashboard", section="Interactive dashboard", title="Click any stream: every value shows where it came from",
                   screenshot=dshot,
                   caption=("Actual AmCraX dashboard screenshot: stream S5 opened on the process flow diagram" if dm and "stream_panel" in dm.name
                            else ("Actual AmCraX dashboard screenshot: " + dm.stem.replace("dashboard_", "").replace("_", " ") + " page" if dm else "")),
                   chips=[(f"{S['dash_pages']} pages, one sidebar", "primary"), ("Click any unit or stream", "nh3"), ("Source pill on every value", "accent"),
                          ("Run new cases locally", "h2"), ("Validation page", "ok")],
                   footnote=f"FastAPI backend ({S['n_endpoints']} API paths) + React and React Flow",
                   source=src_line([], [TAG_ASPEN, TAG_PY], "Dashboard reads results/ through the FastAPI backend; every value keeps its DataSource label."),
                   notes=(f"The dashboard is where engineers meet the model. It has {S['dash_pages']} pages. Here I have clicked the hot cracked gas on the flowsheet: "
                          "temperature, pressure, flows and composition appear, each with a pill saying it came from Aspen Plus. Other pages cover "
                          "sensitivity, optimisation, economics and validation, and locally you can run new cases. "
                          "It displays stored and computed cases; it is not a live plant interface.")))

    # 10 ------------------------------------------------------------- public website (NEW)
    wd, wm = S.get("site_desk"), S.get("site_mob")
    sl.append(dict(id="website", section="Website", title="A static website shows the published results without Aspen Plus",
                   # desktop: banner + navigation + hero (the honest "published results" banner stays in view); phone: whole viewport
                   desk=hero_crop(wd, "slide") if wd else None,
                   mob=crop_info(wm, (0.0, 0.0, 1.0, 1.0), "slide", viewport_ratio=0.46) if wm else None,
                   chips=[(f"{S['site_sections']} public sections", "primary"), ("Interactive PFD", "nh3"), ("Engineering results", "accent"),
                          ("In-browser calculator", "python"), ("Report downloads", "h2")],
                   links=[("Website", S["url_site"]), ("Repository", S["url_repo"])],
                   boundary="Static site with published results; live Aspen runs need the local platform.",
                   source=src_line([], [TAG_ASPEN, TAG_PY], "Sections counted from frontend/src/site/routes.ts; screenshots from docs/screenshots/ (static build, published results only)."),
                   notes=(f"The finished project adds a public website, so anyone can inspect the work without installing anything. It has {S['site_sections']} sections: "
                          "the interactive flow diagram, the engineering results, the methodology, the validation evidence, downloads, and an equilibrium "
                          "calculator that runs in your browser and is labelled as such. The address and the repository are on the slide. "
                          "The boundary: it shows published results only; live Aspen runs need the local platform.")))

    # 11 ------------------------------------------------------------- simulation results
    sw = S["sweep"]
    tp = S.get("tp")
    sl.append(dict(id="results", section="Simulation results", title=f"At {T} and {P}, Aspen converts {S['conv']} of the ammonia",
                   cards=[{"v": S["conv"], "l": "NH3 conversion (equilibrium)", "tag": "ASPEN", "c": "nh3"},
                          {"v": S["h2kg"], "l": "H2 product after the PSA", "tag": "ASPEN", "c": "h2"},
                          {"v": S["ext"], "l": "external heating demand", "tag": "ASPEN", "c": "accent"},
                          {"v": S["lhv"], "l": "first-law LHV efficiency", "tag": "ASPEN", "c": "primary"}],
                   purity=f"H2 purity {S['purity']} is set by the assumed PSA split (recovery {S['rec']}), not predicted.",
                   tp=tp,
                   chart={"labels": [f"{t:.0f}" for t, *_ in sw], "values": [round(100 * c, 1) for _, _, c, _ in sw], "title": f"Aspen temperature sweep at {P}: NH3 conversion (%)"},
                   takeaway=f"At {P}: {S['sw_lo']}, {S['sw_mid']}, {S['sw_hi']}. Above {T}, extra heat buys little.",
                   source=src_line([], [TAG_ASPEN, TAG_ASM], f"{files_aspen}; " + (tp["src"] if tp else S["sweep_src"]) + f", {S['sweep_src']}. PSA split is an assumption."),
                   notes=(f"These are the baseline results from Aspen. At {T} and {P}, {S['conv']} of the ammonia converts, giving {S['h2kg_n']} kilograms of hydrogen an hour "
                          f"with {S['ext']} of external heat. The first-law efficiency is {S['lhv']}, an upper bound. The map shows why we stop at {T}: at {P}, conversion "
                          f"rises only {S['sw_gain']} points more by 800 degrees. The purity of {S['purity']} is set by our assumed PSA split, not predicted.")))

    # 12 ------------------------------------------------------------- heat integration
    sl.append(dict(id="heat", section="Heat integration", title=f"The feed/effluent exchanger cuts external heat by {S['ext_red']} in Aspen",
                   cards=[{"v": f"−{S['ext_red']}", "l": f"external heat in Aspen: {S['ext_nohi'].replace(' kW', '')} → {S['ext']}", "tag": "ASPEN", "c": "nh3"},
                          {"v": S["recovered"], "l": "recovered by the feed/effluent exchanger", "tag": "ASPEN", "c": "primary"},
                          {"v": S["hi_tail"], "l": f"import target with tail-gas firing (−{S['hi_tail_red']})", "tag": "ASPY", "c": "accent"},
                          {"v": S["hi_target"], "l": f"pinch target incl. flue gas, ΔTmin {S['hi_dtmin']}", "tag": "ASPY", "c": "h2"}],
                   chart={"labels": [a for a, _ in S["hi_cfg"]], "values": [b for _, b in S["hi_cfg"]], "title": "External heating by configuration (kW), Python pinch analysis"},
                   bullets=[("Efficiency", f"first-law LHV {S['lhv_nohi']} → {S['lhv']} with the exchanger (Aspen)"),
                            ("Feasible", f"{S['approach']} approach, {S['fehe_cross']}"),
                            ("Targets", "pinch values are targets, not a designed network")],
                   source=src_line([], [TAG_ASPEN, TAG_ASPY, TAG_ASM], "Aspen: results/simulations/baseline.json vs baseline_no_hi.json; targets: heat_integration_baseline.json (Python pinch analysis on Aspen streams)."),
                   notes=(f"Heat is where the design is won. In Aspen, the feed/effluent exchanger recovers {S['recovered']} and cuts external heating by "
                          f"{S['ext_red']}, from {S['ext_nohi']} to {S['ext']}, lifting first-law efficiency from {S['lhv_nohi']} to {S['lhv']}. Our Python pinch analysis "
                          f"on the Aspen streams sets targets: burning the tail gas could bring imports down to about {S['hi_tail']}. "
                          f"Those are targets, not a designed exchanger network.")))

    # 13 ------------------------------------------------------------- optimisation
    opt = None
    if o:
        bnames = {"psa_h2_recovery": "PSA recovery", "fehe_hot_end_approach_K": "exchanger approach", "reactor_temperature_C": "temperature", "reactor_pressure_bar": "pressure"}
        bl = [bnames.get(b.split("=")[0], b.split("=")[0]) for b in (o["bounds"].split("; ") if o["bounds"] != "none" else []) if "=" in b]
        unc = o.get("uncosted") or []
        opt = {"rows": [("reactor", o["T"]), ("pressure", o["P"]), ("PSA H2 recovery", o["rec"]), ("exchanger approach", o["dt"])],
               "lcoh": f"{o['lcoh']} vs {o['lcoh_base']} USD/kg ({o['d']})",
               "lcoh_l": "LCOH, optimum vs baseline, same Python evaluator",
               "bars": o.get("bars"), "tol": o.get("tol_v"),
               "lcoh_aspen": (f"{o['lcoh_aspen']} USD/kg" if o.get("lcoh_aspen") else None),
               "aspen": (f"{o['nconv']} of {o['n']} converged in Aspen Plus V15; primary metrics within {o['prim_up']:.1f}%, LCOH within {o['lcoh_up']:.1f}%"
                         if o.get("n") is not None and o.get("prim_up") is not None else None),
               "honest": ("The optimum sits on the " + " and ".join(bl) + " bounds" if bl else "The optimum is partly bound-driven")
                         + (": the cost model does not see " + ", ".join(unc[:-1]) + (" or " if len(unc) > 1 else "") + unc[-1] + "." if unc else ".")}
    sl.append(dict(id="optim", section="Optimisation", title=(f"Aspen re-solves all {o['n']} optimised designs within {o['prim_up']:.1f}%" if o and o.get("prim_up") is not None
                                                                else "The optimiser runs on the Python model; Aspen re-solves the result"),
                   opt=opt,
                   source=src_line([], [TAG_PY, TAG_ASPEN, TAG_ASPY], (f"{o['src']}; {o.get('va', '')}" if o else "results/optimisation/") + ". Optimisation on the Python process model; candidates re-solved in Aspen Plus V15."),
                   notes=((f"We optimise on the fast Python process model. The minimum-cost point is {o['T']}, {o['P']}, recovery {o['rec']} and a {o['dt']} approach, "
                           f"cutting LCOH by {o['d'].replace('−', '')} against the same evaluator. We then re-solved all {o['n']} candidates in Aspen: "
                           f"{o['nconv']} converged and every primary metric agrees within {o['prim_up']:.1f} percent. The honest limit: the optimum sits on the "
                           f"recovery and approach bounds because the cost model does not see equipment size.") if o and o.get("n") else
                          "The optimiser result will be added automatically once the files exist. It runs on the Python model, so Aspen must re-solve it.")))

    # 14 ------------------------------------------------------------- techno-economics
    sl.append(dict(id="economics", section="Techno-economics", title=(f"Ammonia is {eco['feed_share']} of a {float(eco['lcoh']):.2f} USD/kg hydrogen cost" if eco and eco.get("feed_share")
                                                                     else "The cost model plugs into the same flowsheet results"),
                   eco=eco,
                   env=(f"{S['env']} kg CO2e/kg H2" if S.get("env") else None),
                   env_label=(f"{S.get('env_n', 0)} ammonia-route and heating scenarios; simplified accounting, not an LCA" if S.get("env") else ""),
                   source=src_line((eco["lit"]["cites"] if eco and eco.get("lit") else []) + ([eco["range_cite"]] if eco and eco.get("range_cite") else []),
                                   [TAG_ASPY, TAG_LIT, TAG_ASM],
                                   ("AmCraX: " + eco["src"] + ", results/sensitivity/lcoh_*_baseline.csv, environmental_baseline.json; cost inputs are cited assumptions. " if eco else "")
                                   + "Literature values shown separately."),
                   notes=((f"Our levelised cost of hydrogen for the baseline is {eco['lcoh']} dollars per kilogram, computed in Python from the Aspen flows at "
                           f"{eco['price']:.0f} dollars per tonne of ammonia, and {eco['feed_share']} of it is the ammonia itself. Every hundred dollars per tonne adds about "
                           f"{eco['slope'].replace('+', '').replace(' USD/kg', '')} dollars. Published studies at comparable prices report {eco['lit']['v'].replace('-', ' to ')} dollars. "
                           "Ours is a preliminary order-of-magnitude estimate that omits NOx treatment, polishing and compression.") if eco and eco.get("lit") else
                          "The economics module computes a levelised cost of hydrogen from the same Aspen flows. This is a preliminary estimate, not a quotation.")))

    # 15 ------------------------------------------------------------- applications and differentiation
    fam = []
    if vm:
        for f, n in vm["families"].items():
            fam.append(f"{n} {f}")
    sl.append(dict(id="different", section="Applications", title="Every number carries its source and its check",
                   users=[("Import terminals and hubs", "nh3"), ("Process engineers", "accent"), ("Teaching", "python")],
                   cards=[("Source on every value", "Aspen, Python, literature, assumption", "CODE"),
                          ("Two models cross-check", f"equilibrium within {S['eq_pr']}, like for like", "ASPY"),
                          ("Failures published", (f"{vm['total']} checks: {vm['counts'].get('pass', 0)} pass, {vm['counts'].get('fail', 0)} fail, {vm['counts'].get('informational', 0)} informational" if vm else "validation matrix pending"), "ASPY")],
                   failures=("Failures: " + "; ".join(fam) + "." if fam else None),
                   proof_pending=None if vm else "Validation matrix counts: RESULT PENDING (results/validation/validation_matrix.json)",
                   noclaim=["Not a validated digital twin", "Steady state only", "Equilibrium reactor in Aspen", "Reduced-order PSA", "Preliminary costs", "Simplified carbon accounting"],
                   source=src_line([], [TAG_ASPY, TAG_PY], "results/validation/validation_matrix.json; equilibrium_comparison.csv."),
                   notes=((f"Who would use this? Teams screening crackers at import terminals and hubs, engineers testing what heat integration is worth, and teachers. "
                           f"What is different is traceability: every value names its source, and Aspen and an independent model check each other. Of {vm['total']} validation checks, "
                           f"{vm['counts'].get('pass', 0)} pass and {vm['counts'].get('fail', 0)} fail, and we publish the failures: mostly two models using different feed-section property methods. "
                           "We do not claim a validated digital twin.") if vm else
                          "What is different is traceability. We do not claim a validated digital twin.")))

    # 16 ------------------------------------------------------------- future development and close
    sl.append(dict(id="close", section="Next steps", title="AmCraX makes ammonia-to-hydrogen design traceable",
                   claim="Ammonia can move hydrogen. AmCraX shows, with checked numbers, what it costs to get it back.",
                   links=[("Website", S["url_site"]), ("Code", S["url_repo"])],
                   steps=[("Aspen RPlug reactor", "with the kinetics already implemented in Python", "primary"),
                          ("Designed PSA/TSA", "and NH3 polishing in the flowsheet", "h2"),
                          ("Hydrogen compression", "modelled and costed in the flowsheet", "n2"),
                          ("Equipment-level costing", "so the optimiser sees equipment size", "accent")],
                   footer="Next steps are future work, not results.",
                   source=src_line([], [TAG_ASPEN, TAG_PY], "Links from README.md. Next steps follow the limits stated on slides 8, 13 and 15."),
                   notes=("Our next steps follow directly from the limits I have shown. We will put the kinetics we already have into an Aspen RPlug reactor, "
                          "design the PSA or TSA with ammonia polishing, add hydrogen compression to the flowsheet, and cost equipment so the optimiser sees its size. "
                          "Ammonia can move hydrogen; AmCraX shows, with checked numbers, what it costs to get it back. Everything is open at the addresses on the slide. "
                          "These steps are plans, not results.")))

    for i, s in enumerate(sl, 1):
        s["n"] = i
        s["notes"] = spoken(s["notes"])
        if s.get("section"):  # section tag number == slide number ("08  ..." beside "8 / 16")
            s["section"] = f"{i:02d}  " + re.sub(r"^\d+\s+", "", s["section"])
    return sl


# ----------------------------------------------------------------------------- node + COM
def find_node() -> tuple[list[str], dict]:
    env = dict(os.environ)
    cand = os.environ.get("AMCRAX_NODE")
    if cand and Path(cand).exists():
        if Path(cand).name.lower() == "code.exe":
            env["ELECTRON_RUN_AS_NODE"] = "1"
        return [cand], env
    # 1) a real Node.js: on PATH (scripts/env.ps1) or in the project tool folder
    n = shutil.which("node")
    if n:
        return [n], env
    tool_node = Path(os.environ.get("LOCALAPPDATA", "")) / "AmCraX-tools/node/node.exe"
    if tool_node.exists():
        return [str(tool_node)], env
    # 2) last resort: the Node runtime embedded in VS Code
    vscode = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Microsoft VS Code/Code.exe",
              Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft VS Code/Code.exe"]
    for v in vscode:
        if v.exists():
            env["ELECTRON_RUN_AS_NODE"] = "1"
            return [str(v)], env
    raise SystemExit("No Node.js runtime found (dot-source scripts/env.ps1, or set AMCRAX_NODE)")


def run_layout() -> str:
    cmd, env = find_node()
    log = BUILD / "layout_log.txt"
    if log.exists():
        log.unlink()
    p = subprocess.run(cmd + [str(LAYOUT_JS), str(DATA_JSON), str(PPTX), str(log)], cwd=HERE, env=env,
                       capture_output=True, text=True, timeout=300)
    out = (p.stdout or "") + (p.stderr or "")
    if log.exists():
        out += log.read_text(encoding="utf-8")
    if p.returncode != 0 or not PPTX.exists():
        print(out)
        raise SystemExit(f"deck_layout.js failed (exit {p.returncode}) with runtime {cmd[0]}")
    return f"runtime: {cmd[0]}" + (" (VS Code built-in Node, ELECTRON_RUN_AS_NODE=1)" if Path(cmd[0]).name.lower() == "code.exe" else "") + "\n" + out.strip()


def export_with_powerpoint() -> int:
    import pythoncom
    import win32com.client
    PREVIEW.mkdir(exist_ok=True)
    for f in PREVIEW.glob("slide_*.png"):
        f.unlink()
    pids_before = ppt_pids()
    user_had_ppt = bool(pids_before)
    if user_had_ppt:
        print("note: PowerPoint was already running; the build closes only its own presentation and leaves PowerPoint open")
    pythoncom.CoInitialize()
    app = None
    pres = None
    n = 0
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            app.DisplayAlerts = 1  # ppAlertsNone
        except Exception:  # noqa: BLE001
            pass
        pres = app.Presentations.Open(str(PPTX), True, False, False)  # ReadOnly, Untitled, WithWindow
        if PDF.exists():
            PDF.unlink()
        pres.SaveAs(str(PDF), 32)  # ppSaveAsPDF
        for i in range(1, pres.Slides.Count + 1):
            pres.Slides(i).Export(str(PREVIEW / f"slide_{i:02d}.png"), "PNG", 1600, 900)
            n += 1
    finally:
        own_pids = set() if user_had_ppt else (ppt_pids() - pids_before)
        try:
            if pres is not None:
                pres.Close()
        except Exception:  # noqa: BLE001
            pass
        pres = None
        quit_ok = False
        try:
            # quit only an instance this build started, and only if no other presentation is open in it
            if app is not None and not user_had_ppt and int(app.Presentations.Count) == 0:
                app.Quit()
                quit_ok = True
        except Exception:  # noqa: BLE001
            pass
        app = None
        pythoncom.CoUninitialize()
        # an automation instance can linger after Quit(); end it only if this build started it (new PID) and Quit succeeded
        if quit_ok and own_pids:
            for _ in range(20):
                if not (ppt_pids() & own_pids):
                    break
                time.sleep(0.5)
            for pid in ppt_pids() & own_pids:
                subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
                print(f"note: ended the PowerPoint instance started by this build (PID {pid}) after Quit()")
    return n


def ppt_pids() -> set[int]:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return {int(r[1]) for r in csv.reader(out.splitlines()) if len(r) > 1 and r[0].upper() == "POWERPNT.EXE"}


# ----------------------------------------------------------------------------- checks
BAD = re.compile(r"(\bTODO\b|\bTBD\b|lorem|ipsum|\bXXX\b|\{\{|\}\}|\bNone\b|\bnan\b|\bundefined\b|\[insert|PLACEHOLDER)", re.I)


def inspect_pptx(slides: list[dict]) -> tuple[list[str], int]:
    from pptx import Presentation
    prs = Presentation(str(PPTX))
    lines, bad = [], 0
    for i, slide in enumerate(prs.slides, 1):
        body, src = [], ""
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text
            name = sh.name or ""
            if name.startswith("src_"):
                src = t
            elif name.startswith(("foot_", "tag_", "pill_", "cap_", "pfd_", "glyph_")):
                continue  # footer, section tag, provenance pills, captions, diagram labels (numbers in num_ shapes DO count)
            else:
                body.append(t)
            if BAD.search(t):
                bad += 1
                lines.append(f"  !! slide {i}: placeholder-like text in shape '{name}': {t[:80]!r}")
        alltext = " ".join(body)
        w = words(alltext)
        img_slide = slides[i - 1]["id"] in ("pfd", "aspen", "dashboard", "website")
        limit = 40 if img_slide else (130 if i == 1 else 90)
        flag = "OK" if w <= limit else f"OVER (limit {limit})"
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        if BAD.search(notes):
            bad += 1
            lines.append(f"  !! slide {i}: placeholder-like text in the speaker notes: {BAD.search(notes).group(0)!r}")
        if re.search(r"fuel[- ]cell grade", alltext + " " + notes, re.I):
            bad += 1
            lines.append(f"  !! slide {i}: 'fuel-cell grade' wording (fact sheet F4)")
        nw = words(notes)
        nflag = "OK" if 40 <= nw <= 90 else "CHECK (40-90)"
        pend = "RESULT PENDING" in alltext
        lines.append(f"  slide {i:2d} {slides[i-1]['id']:<12} words={w:3d} {flag:<14} notes={nw:3d} {nflag:<14} src={'yes' if src else 'NO'}{'  [contains RESULT PENDING]' if pend else ''}")
        if i > 1 and not src:
            bad += 1
            lines.append(f"  !! slide {i}: no source line")
    return lines, bad


def write_script(slides: list[dict]) -> None:
    out = ["# AmCraX pitch: speaker script", "",
           "Generated by `docs/pitch_deck/build_deck.py` from the same data as the deck; timing at 150 words per minute.", "",
           "| Slide | Start | Duration | Words |", "|---|---|---|---|"]
    t = 0.0
    rows = []
    for s in slides:
        w = words(s["notes"])
        d = w / 150 * 60
        out.append(f"| {s['n']}. {s['title'] if s['id'] != 'title' else 'AmCraX title'} | {int(t//60)}:{int(t%60):02d} | {d:.0f} s | {w} |")
        rows.append((s, t, d))
        t += d
    out.append(f"| **Total** | | **{int(t//60)} min {int(t%60):02d} s** | |")
    out.append("")
    for s, t0, d in rows:
        out.append(f"## {s['n']}. {s['title'] if s['id'] != 'title' else 'AmCraX: title and value proposition'}")
        out.append(f"*Start {int(t0//60)}:{int(t0%60):02d}, about {d:.0f} s*")
        out.append("")
        out.append(s["notes"])
        out.append("")
    SCRIPT_MD.write_text("\n".join(out), encoding="utf-8")


# ----------------------------------------------------------------------------- main
def main() -> int:
    t0 = time.time()
    args = set(sys.argv[1:])
    BUILD.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    S = collect()
    collect_pending(S, run_tests="--no-tests" not in args)
    collect_more(S)
    slides = build_slides(S)
    data = {"slides": slides, "colors": {k: v.lstrip("#").upper() for k, v in C.items()}, "total": len(slides),
            "pending": [list(p) for p in R.pending]}
    DATA_JSON.write_text(json.dumps(data, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    layout_out = run_layout()
    n_png = 0
    export_err = None
    if "--no-export" not in args:
        try:
            n_png = export_with_powerpoint()
        except Exception as e:  # noqa: BLE001
            export_err = repr(e)
    lines, bad = inspect_pptx(slides)
    write_script(slides)

    print("=" * 100)
    print("AmCraX pitch deck build log")
    print("=" * 100)
    print(f"Layout: {layout_out}")
    print(f"PPTX: {PPTX}\nPDF : {PDF if PDF.exists() else 'not exported'}\nPNGs: {n_png} in {PREVIEW}\nScript: {SCRIPT_MD}")
    if export_err:
        print(f"!! PowerPoint export failed: {export_err}")
    print(f"\nSlides built: {len(slides)}")
    for l in lines:
        print(l)
    print("\nNumbers used (label | shown | file | key | tag):")
    for lab, shown, f, key, tag in R.numbers:
        print(f"  - {lab} | {shown} | {f} | {key} | {tag}")
    print(f"\nPending items ({len(R.pending)}):")
    for item, path in R.pending:
        print(f"  - PENDING: {item}  <- {path}")
    for w in R.warnings:
        print(f"  warning: {w}")
    print(f"\nBuild time {time.time()-t0:.1f} s")
    if bad:
        print(f"FAILED: {bad} placeholder / missing-source problem(s) found")
        return 2
    if export_err:
        return 3
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
