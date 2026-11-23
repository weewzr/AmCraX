"""Write the catalyst-specific Aspen RPLUG case lists (research expansion, workstream A part 2).

Usage (from the project root, after scripts/env.ps1)::

    python aspen/automation/make_catalyst_study_cases.py

Writes (deterministic):
    aspen/automation/cases/catalyst_validation_cases.json   spec reference test points (Aspen vs Python)
    aspen/automation/cases/catalyst_study_cases.json        standalone studies (T, P, W, mass targets, adiabatic)
    aspen/automation/cases/catalyst_integrated_cases.json   full flowsheet with the RPLUG cracker per catalyst

Basis: pure NH3 100 kmol/h (as the baseline flowsheet), isothermal RPLUG, no pressure drop, 50 tubes of
0.126 m (kum2026heatintegrated Table 1). Bed properties per catalyst from aspen_kinetics_spec.json.
Takahashi Ni/MgO and Ru/MgO use the kinetics workstream's fitted LHHW approximation (source_type python),
which is valid at 20 bar only, so they appear only in 20 bar cases.

Operating temperature (defined once): the temperature at which a practical inventory of 100 kg catalyst per
100 kmol/h NH3 reaches 95 % NH3 conversion at the baseline 20 bar, isothermal (from the kinetics workstream's
study_temperature_for_target_conversion.json, rounded up to the next whole degC; confirmed by an Aspen run).
95 % is used because 99 % at 20 bar is equilibrium-limited below about 685 degC for every catalyst.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
KIN = ROOT / "results" / "research" / "kinetics"
CASES = ROOT / "aspen" / "automation" / "cases"

CATS = {  # catalyst_id: (short tag, kinetic_form)
    "ru_kum_temkin_pyzhev": ("kum", "auto"),
    "nire_ceo2_5ni1ru_lucentini_lhhw": ("luc5", "lhhw"),
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": ("luc25", "lhhw"),
    "ni_takahashi_microkinetic": ("tni", "lhhw_approximation"),
    "ru_takahashi_microkinetic": ("tru", "lhhw_approximation"),
}
APPROX = {"ni_takahashi_microkinetic", "ru_takahashi_microkinetic"}
P_BASE = 20.0
W_OP = 100.0
X_OP = 0.95


def _tag(v: float) -> str:
    s = f"{v:g}".replace(".", "p")
    return s


def bed(entry: dict) -> dict:
    b = entry["bed_properties"]
    return {"particle_density_kg_m3": b["particle_density_kg_m3"]["value"], "bed_voidage": b["bed_voidage"]["value"],
            "particle_diameter_m": b["particle_diameter_m"]["value"]}


def case(cid, cat, form, T, P, W, bd, **kw):
    d = {"case_id": cid, "catalyst_id": cat, "kinetic_form": form, "temperature_C": round(float(T), 3),
         "pressure_bar": float(P), "catalyst_mass_kg": round(float(W), 4), "n_tubes": 50,
         "feed_kmol_h": {"NH3": 100.0}, "h2_seed_conversion": 1e-6}
    d.update(bd)
    d.update(kw)
    return d


def operating_temperatures() -> dict[str, float]:
    rows = json.loads((KIN / "study_temperature_for_target_conversion.json").read_text(encoding="utf-8"))["rows"]
    out = {}
    for r in rows:
        if r["P_bar"] == P_BASE and r["W_cat_kg"] == W_OP and r["X_target"] == X_OP:
            out[r["catalyst_id"]] = float(math.ceil(r["T_required_C"]))
    return out


def main() -> None:
    spec = {c["catalyst_id"]: c for c in json.loads(SPEC.read_text(encoding="utf-8"))["catalysts"]}
    val, study, integ = [], [], []
    for cat, (t, form) in CATS.items():
        e, bd = spec[cat], bed(spec[cat])
        for n, p in enumerate(e["reference_test_points"]):
            if cat in APPROX and abs(p["P_bar"] - P_BASE) > 1e-9:
                continue
            val.append(case(f"cv_{t}_{n:02d}_T{_tag(p['T_C'])}_P{_tag(round(p['P_bar'], 3))}_W{_tag(p['W_cat_kg'])}",
                            cat, form, p["T_C"], p["P_bar"], p["W_cat_kg"], bd))
    # standalone studies
    mass_rows = json.loads((KIN / "study_mass_for_fraction_of_equilibrium.json").read_text(encoding="utf-8"))["rows"]
    t_op = operating_temperatures()
    for cat, (t, form) in CATS.items():
        bd = bed(spec[cat])
        for T in (450, 500, 550, 600, 650, 700):
            study.append(case(f"cs_T_{t}_T{T}_P20_W100", cat, form, T, P_BASE, W_OP, bd))
        if cat not in APPROX:
            for P in (1.01325, 5.0, 10.0, 20.0, 40.0):
                if P == P_BASE:
                    continue  # identical to cs_T_*_T550_P20_W100
                study.append(case(f"cs_P_{t}_T550_P{_tag(round(P, 3))}_W100", cat, form, 550, P, W_OP, bd))
        for W in (5, 10, 20, 50, 200, 500):  # W = 100 is cs_T_*_T600_P20_W100
            study.append(case(f"cs_W_{t}_T600_P20_W{W}", cat, form, 600, P_BASE, W, bd))
        for r in mass_rows:
            if r["catalyst_id"] == cat and r["P_bar"] == P_BASE and r["T_C"] in (500, 600) \
                    and r["fraction_of_equilibrium"] in (0.95, 0.99) and r.get("reachable_within_1e7_kg", True):
                study.append(case(f"cs_M_{t}_T{r['T_C']}_f{_tag(r['fraction_of_equilibrium'])}", cat, form, r["T_C"],
                                  P_BASE, r["W_cat_kg"], bd))
        if cat in t_op:
            study.append(case(f"cs_OP_{t}_T{_tag(t_op[cat])}_P20_W100", cat, form, t_op[cat], P_BASE, W_OP, bd))
        study.append(case(f"cs_AD_{t}_Tin650_P20_W100", cat, form, 650, P_BASE, W_OP, bd,
                          thermal_mode="adiabatic", h2_seed_conversion=1e-3))
        if cat in t_op:
            for hi in (True, False):
                integ.append(case(f"ci_{t}_T{_tag(t_op[cat])}_P20_W100_{'hi' if hi else 'nohi'}", cat, form, t_op[cat],
                                  P_BASE, W_OP, bd, configuration="integrated", h2_seed_conversion=1e-4,
                                  flowsheet={"heat_integration": hi}))
                integ[-1].pop("feed_kmol_h")
    CASES.mkdir(parents=True, exist_ok=True)
    for name, lst in (("catalyst_validation_cases", val), ("catalyst_study_cases", study),
                      ("catalyst_integrated_cases", integ)):
        (CASES / f"{name}.json").write_text(json.dumps(lst, indent=1), encoding="utf-8")
        print(name, len(lst))
    print("operating temperatures:", t_op)


if __name__ == "__main__":
    main()
