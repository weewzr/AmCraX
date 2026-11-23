"""Unified techno-economic reference scenario (Phase 2, task C1).

The single source of truth for every research cost path is ``backend/amcrax/data/reference_scenario.yaml``.

    from amcrax.economics.reference import load_reference_scenario, reference_capex, provenance_stamp
    ref = load_reference_scenario()          # cached, typed
    ref.fx_SGD_per_USD, ref.electricity_USD_per_kWh, ref.discount_rate, ...
    cap = reference_capex(nh3_feed_kmol_h=99.8)   # CAPEX method cho2026_itemised_v1

CAPEX METHOD cho2026_itemised_v1 (see docs/research/unified_baseline.md)
    Installed cost of item i in the Cho et al. (2026) Ni-24.34 bar plant (2024 USD):
        I_i,ref = u_i * m_H2,ref * OH_ref / CRF(d_ref, n_ref)          u_i: unit CAPEX, USD/kg H2 (Cho Table 7)
    ISBL items (boiler, heat exchangers, T/PSA split into PSA and adsorber, reactor, other ISBL) are scaled
        I_i = I_i,ref * (S_i / S_i,ref) ** n * location_factor           n = 0.8 (Chopra 2026 Eq. 5)
    the product compressor is excluded (AmCraX has none), and
        TCI = sum(I_i) * (1 + OSBL) * (1 + engineering + contingency)   (Cho Table 4: 0.12, 0.10 + 0.18)
    S_i is the NH3 feed by default; the reactor may follow the catalyst inventory; any item accepts a caller
    size ratio (for example an exchanger-area ratio).

The legacy correlation in amcrax.economics.lcoh is NOT changed and stays the version 1 basis of the core
stored results; it is superseded for research outputs by this reference scenario.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "reference_scenario.yaml"
REL_PATH = "backend/amcrax/data/reference_scenario.yaml"
ISBL_ITEMS = ("boiler", "heat_exchangers", "psa", "adsorber", "reactor", "other_isbl")
#: map from reference CAPEX items to the four keys used by Phase 1 consumers (tci_by_equipment_USD)
LEGACY_KEY = {"reactor": "cracker"}


def _crf(i: float, n: float) -> float:
    if i == 0:
        return 1.0 / n
    f = (1.0 + i) ** n
    return i * f / (f - 1.0)


@dataclass(frozen=True)
class ReferenceScenario:
    raw: dict = field(repr=False)
    sha256: str
    version: str
    id: str
    nh3_feed_kmol_h: float
    h2_product_kg_h: float
    operating_hours_h_per_yr: float
    discount_rate: float
    plant_life_yr: float
    maintenance_frac_capex_per_yr: float
    insurance_frac_capex_per_yr: float
    labour_USD_per_yr: float
    plant_overhead_frac_labour_maint: float
    g_and_a_frac_fixed_opex: float
    fx_SGD_per_USD: float
    fx_date: str
    usd_per_eur: float
    electricity_USD_per_kWh: float
    nh3_prices_USD_per_t: dict
    default_nh3_scenario: str
    h2_selling_price_USD_per_kg: float
    carbon_tax_SGD_per_t: float
    carbon_threshold_tCO2e_per_yr: float
    capex_method: str
    capex_scaling_exponent: float
    power_plant: dict
    literature_reproduction: dict
    sensitivity_ranges: dict

    # -------------------------------------------------------------- helpers
    def to_sgd(self, usd: Optional[float]) -> Optional[float]:
        return None if usd is None else usd * self.fx_SGD_per_USD

    def economic_overrides(self) -> dict:
        """Reference values of the EconomicAssumptions fields this scenario owns."""
        return {"discount_rate": self.discount_rate, "plant_life_yr": self.plant_life_yr,
                "operating_hours_h_per_yr": self.operating_hours_h_per_yr,
                "maintenance_frac_capex_per_yr": self.maintenance_frac_capex_per_yr,
                "insurance_frac_capex_per_yr": self.insurance_frac_capex_per_yr,
                "labour_USD_per_yr": self.labour_USD_per_yr,
                "plant_overhead_frac_labour_maint": self.plant_overhead_frac_labour_maint,
                "g_and_a_frac_fixed_opex": self.g_and_a_frac_fixed_opex,
                "electricity_price_USD_per_kWh": self.electricity_USD_per_kWh}

    def crf(self) -> float:
        return _crf(self.discount_rate, self.plant_life_yr)

    def power_value(self, key: str) -> float:
        v = self.power_plant[key]["value"]
        if v == "from_finance":
            return float(getattr(self, key))
        return float(v)

    def reproduction(self, name: str) -> dict:
        return dict(self.literature_reproduction[name]["value"])

    def sens(self, key: str) -> tuple:
        return tuple(self.sensitivity_ranges[key]["value"])


@lru_cache(maxsize=1)
def load_reference_scenario() -> ReferenceScenario:
    text = DATA_FILE.read_bytes()
    d = yaml.safe_load(text.decode("utf-8"))
    v = lambda *k: _get(d, k)["value"]  # noqa: E731
    return ReferenceScenario(
        raw=d, sha256=hashlib.sha256(text).hexdigest(), version=str(d["version"]), id=d["id"],
        nh3_feed_kmol_h=float(v("plant", "nh3_feed_kmol_h")), h2_product_kg_h=float(v("plant", "h2_product_kg_h")),
        operating_hours_h_per_yr=float(v("operation", "operating_hours_h_per_yr")),
        discount_rate=float(v("finance", "discount_rate")), plant_life_yr=float(v("finance", "plant_life_yr")),
        maintenance_frac_capex_per_yr=float(v("finance", "maintenance_frac_capex_per_yr")),
        insurance_frac_capex_per_yr=float(v("finance", "insurance_frac_capex_per_yr")),
        labour_USD_per_yr=float(v("finance", "labour_USD_per_yr")),
        plant_overhead_frac_labour_maint=float(v("finance", "plant_overhead_frac_labour_maint")),
        g_and_a_frac_fixed_opex=float(v("finance", "g_and_a_frac_fixed_opex")),
        fx_SGD_per_USD=float(v("currency", "fx_SGD_per_USD")), fx_date=str(d["currency"]["fx_SGD_per_USD"]["date"]),
        usd_per_eur=float(v("currency", "usd_per_eur")),
        electricity_USD_per_kWh=float(v("prices", "electricity_USD_per_kWh")),
        nh3_prices_USD_per_t={k: float(e["value"]) for k, e in d["prices"]["nh3_price_scenarios_USD_per_t"].items()},
        default_nh3_scenario=str(v("prices", "default_nh3_scenario")),
        h2_selling_price_USD_per_kg=float(v("prices", "h2_selling_price_USD_per_kg")),
        carbon_tax_SGD_per_t=float(v("carbon_pricing", "rate_SGD_per_tCO2e")),
        carbon_threshold_tCO2e_per_yr=float(v("carbon_pricing", "threshold_tCO2e_per_yr")),
        capex_method=str(v("capex", "method")), capex_scaling_exponent=float(v("capex", "scaling_exponent")),
        power_plant=d["power_plant"], literature_reproduction=d["literature_reproduction"],
        sensitivity_ranges=d["sensitivity_ranges"])


def _get(d: dict, keys: tuple) -> Any:
    for k in keys:
        d = d[k]
    return d


def provenance_stamp() -> dict:
    """Object for provenance.reference_scenario in every research output JSON."""
    r = load_reference_scenario()
    return {"file": REL_PATH, "sha256": r.sha256, "version": r.version, "id": r.id,
            "fx_SGD_per_USD": r.fx_SGD_per_USD, "fx_date": r.fx_date, "capex_method": r.capex_method}


# ------------------------------------------------------------------------------------------ CAPEX
def reference_item_costs() -> dict:
    """Installed ISBL cost of each item in the Cho reference plant (USD, 2024), and the factors."""
    c = load_reference_scenario().raw["capex"]
    u = dict(c["unit_capex_USD_per_kg_h2"]["value"])
    m = c["reference_plant_h2_kg_h"]["value"]
    oh = c["reference_operating_hours_h_per_yr"]["value"]
    k = _crf(c["reference_discount_rate"]["value"], c["reference_plant_life_yr"]["value"])
    fac = (1.0 + c["osbl_frac_isbl"]["value"]) * (1.0 + c["engineering_frac_isbl_osbl"]["value"]
                                                   + c["contingency_frac_isbl_osbl"]["value"])
    isbl_total_u = u["total"] / fac
    itemised = u["boiler"] + u["heat_exchangers"] + u["compressor"] + u["tpsa"] + u["reactor"]
    split = c["tpsa_split_psa_adsorber"]["value"]
    s = split["psa"] + split["adsorber"]
    unit = {"boiler": u["boiler"], "heat_exchangers": u["heat_exchangers"], "compressor": u["compressor"],
            "psa": u["tpsa"] * split["psa"] / s, "adsorber": u["tpsa"] * split["adsorber"] / s,
            "reactor": u["reactor"], "other_isbl": isbl_total_u - itemised}
    to_usd = m * oh / k
    return {"installed_USD": {i: x * to_usd for i, x in unit.items()}, "unit_USD_per_kg_h2": unit,
            "indirect_factor": fac, "reference_crf": k, "reference_h2_kg_h": m,
            "reference_nh3_feed_kmol_h": c["reference_plant_nh3_feed_kmol_h"]["value"]}


def reference_catalyst_mass_kg(space_velocity_mL_per_g_h: float = 9000.0, molar_volume_L_per_mol: float = 22.414) -> float:
    """Cho reference catalyst inventory from its space velocity (same sizing rule as AmCraX)."""
    n = load_reference_scenario().raw["capex"]["reference_plant_nh3_feed_kmol_h"]["value"]
    return n * 1000.0 * molar_volume_L_per_mol * 1000.0 / space_velocity_mL_per_g_h / 1000.0


def reference_capex(nh3_feed_kmol_h: float, *, catalyst_mass_kg: Optional[float] = None,
                    reactor_size_driver: Optional[str] = None, item_size_ratio: Optional[dict] = None,
                    exclude: tuple = (), exponent: Optional[float] = None, capex_multiplier: float = 1.0,
                    location_factor: Optional[float] = None) -> dict:
    """CAPEX by method cho2026_itemised_v1. Returns ISBL by item, TCI by item (indirects allocated pro rata),
    the total, and the Phase 1 keys (pec_USD, tci_by_equipment_USD with cracker/psa/adsorber/heat_exchangers)."""
    ref = load_reference_scenario()
    c = ref.raw["capex"]
    base = reference_item_costs()
    n = ref.capex_scaling_exponent if exponent is None else exponent
    lf = c["location_factor_singapore"]["value"] if location_factor is None else location_factor
    driver = dict(c["size_driver"]["value"])
    if reactor_size_driver:
        driver["reactor"] = reactor_size_driver
    feed_ratio = nh3_feed_kmol_h / base["reference_nh3_feed_kmol_h"]
    ratios = {}
    for i in ISBL_ITEMS:
        if item_size_ratio and i in item_size_ratio:
            ratios[i] = float(item_size_ratio[i])
        elif driver[i] == "catalyst_mass":
            if catalyst_mass_kg is None:
                raise ValueError("reactor_size_driver 'catalyst_mass' needs catalyst_mass_kg")
            ratios[i] = catalyst_mass_kg / reference_catalyst_mass_kg()
        else:
            ratios[i] = feed_ratio
    isbl = {i: base["installed_USD"][i] * ratios[i] ** n * lf * capex_multiplier
            for i in ISBL_ITEMS if i not in exclude}
    fac = base["indirect_factor"]
    tci_items = {i: v * fac for i, v in isbl.items()}
    total = sum(tci_items.values())
    legacy4 = {LEGACY_KEY.get(i, i): v for i, v in tci_items.items()}
    return {"method": ref.capex_method, "total_capex_USD": total, "isbl_USD": isbl, "isbl_total_USD": sum(isbl.values()),
            "indirect_factor": fac, "indirects_USD": total - sum(isbl.values()), "tci_by_item_USD": tci_items,
            "size_ratio": ratios, "scaling_exponent": n, "location_factor": lf, "capex_multiplier": capex_multiplier,
            "excluded": ["compressor", *exclude], "cost_year": c["cost_year"]["value"],
            # Phase 1 compatible keys
            "pec_USD": {LEGACY_KEY.get(i, i): v for i, v in isbl.items()}, "pec_total_USD": sum(isbl.values()),
            "tci_over_pec": fac, "tci_by_equipment_USD": legacy4,
            "basis": ("cho2026_itemised_v1: Cho 2026 Ni-24.34 bar itemised installed cost (2024 USD), product compressor "
                      f"removed, items scaled by size ratio^{n:g}, x (1+OSBL 0.12)(1+eng 0.10+cont 0.18)")}
