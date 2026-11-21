"""Regenerate the thermodynamic data files from their primary machine-readable sources.

Run once (build time only; the runtime model does NOT import Cantera or CoolProp):

    python -m amcrax.thermodynamics.build_data

* ``backend/amcrax/data/nasa7.json``  - NASA 7-coefficient polynomials copied verbatim from
  Cantera's bundled ``gri30.yaml`` (GRI-Mech 3.0 thermo, Smith et al. 1999).
* ``backend/amcrax/data/critical_properties.json`` - Tc, Pc, acentric factor from CoolProp
  (reference-quality Helmholtz equations of state; citations recorded per fluid).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SPECIES = ("NH3", "H2", "N2", "H2O", "O2")
COOLPROP_NAMES = {"NH3": "Ammonia", "H2": "Hydrogen", "N2": "Nitrogen", "H2O": "Water", "O2": "Oxygen"}
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def build_nasa7() -> dict:
    import cantera as ct
    import yaml

    path = Path(ct.__file__).parent / "data" / "gri30.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_name = {sp["name"]: sp for sp in doc["species"]}
    out = {
        "provenance": {
            "source_file": "cantera/data/gri30.yaml (bundled with Cantera)",
            "cantera_version": ct.__version__,
            "mechanism": "GRI-Mech 3.0 (Smith, Golden, Frenklach, et al., 1999, http://combustion.berkeley.edu/gri-mech/)",
            "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "extracted_by": "amcrax.thermodynamics.build_data (programmatic copy, no manual typing)",
            "form": "cp/R = a0 + a1 T + a2 T^2 + a3 T^3 + a4 T^4; h/RT = a0 + a1 T/2 + ... + a5/T; s/R = a0 ln T + a1 T + ... + a6",
            "note": "Reference pressure of the polynomials: see cantera_reference_pressure_Pa (phase value) and per-species p_ref_Pa (null = phase default).",
        },
        "species": {},
    }
    for name in SPECIES:
        th = by_name[name]["thermo"]
        assert th["model"] == "NASA7", name
        p_ref = th.get("reference-pressure", None)
        out["species"][name] = {
            "composition": by_name[name]["composition"],
            "T_ranges_K": [float(x) for x in th["temperature-ranges"]],
            "coeffs_low": [float(x) for x in th["data"][0]],
            "coeffs_high": [float(x) for x in th["data"][1]],
            "p_ref_Pa": p_ref,
            "note": th.get("note", ""),
        }
    # Cantera's own reference pressure for the phase (to record it unambiguously)
    gas = ct.Solution(str(path))
    out["provenance"]["cantera_reference_pressure_Pa"] = float(gas.reference_pressure)
    out["provenance"]["units"] = "T in K; dimensionless coefficients"
    return out


def build_critical() -> dict:
    import CoolProp
    import CoolProp.CoolProp as CP

    out = {
        "provenance": {
            "source": "CoolProp (Bell et al., Ind. Eng. Chem. Res. 53 (2014) 2498-2508), fluid-specific reference EOS",
            "coolprop_version": CoolProp.__version__,
            "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "keys": "Tc_K = PropsSI('Tcrit'), Pc_bar = PropsSI('pcrit')/1e5, omega = PropsSI('acentric')",
        },
        "species": {},
    }
    for sp, fl in COOLPROP_NAMES.items():
        try:
            bib = CP.get_BibTeXKey(fl, "EOS")
        except Exception:  # pragma: no cover
            bib = ""
        out["species"][sp] = {
            "coolprop_fluid": fl,
            "Tc_K": float(CP.PropsSI("Tcrit", fl)),
            "Pc_bar": float(CP.PropsSI("pcrit", fl)) / 1e5,
            "omega": float(CP.PropsSI("acentric", fl)),
            "eos_bibtex_key": bib,
        }
    return out


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "nasa7.json").write_text(json.dumps(build_nasa7(), indent=2), encoding="utf-8")
    (DATA_DIR / "critical_properties.json").write_text(json.dumps(build_critical(), indent=2), encoding="utf-8")
    print("wrote", DATA_DIR / "nasa7.json", DATA_DIR / "critical_properties.json")


if __name__ == "__main__":
    main()
