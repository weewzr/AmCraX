"""Reduced-order PSA model: literature recovery/purity operating point applied as a component split.

Not a designed or validated PSA. The H2 recovery and product purity are taken from a single
literature-reported operating point (``basis``) or given explicitly; no interpolation between
points is done (the points use different adsorbents and pressures, so a trend between them would
be invented). Impurity split: NH3, H2O -> tail gas; product impurity = N2 (assumption, see
data/separation.yaml psa.impurity_split_assumption). If the available feed pressure is below the
point's feed-pressure requirement, a cracked-gas compressor is added (compression_power_kW).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

from .compression import compression_power_kW
from .params import MODEL_LABEL, cite, params, psa_point


class PSAResult(BaseModel):
    model: str = MODEL_LABEL
    basis: str
    basis_source: str
    h2_recovery: float
    h2_purity_mole_frac: float
    feed_kmol_h: dict[str, float]
    product_kmol_h: dict[str, float]
    tailgas_kmol_h: dict[str, float]
    tailgas_mole_frac: dict[str, float]
    feed_pressure_bar: float
    required_feed_pressure_bar: float
    required_feed_pressure_source: str
    tailgas_pressure_bar: float
    pressure_ratio_feed_to_tail: float
    compression_power_kW: float = 0.0
    compression_stages: int = 0
    compression_eta: Optional[float] = None
    product_h2_kg_h: float
    specific_energy_kWh_per_kgH2: float
    h2_loss_kmol_h: float
    h2_loss_lhv_kW: float
    nh3_in_product_ppm: float
    notes: list[str] = Field(default_factory=list)


def psa_performance(feed_kmol_h: dict[str, float], feed_pressure_bar: float, tailgas_pressure_bar: float | None = None,
                    target_purity: float | None = None, *, basis: str = "cho2026_5A",
                    h2_recovery: float | None = None, required_feed_pressure_bar: float | None = None,
                    feed_temperature_K: float = 313.15, compressor_eta: float | None = None,
                    compressor_stages: int | None = None) -> PSAResult:
    """Apply a literature PSA operating point to a cracked-gas feed.

    basis: an id from data/separation.yaml psa.operating_points, or "amcrax_baseline" (0.85, assumption).
    h2_recovery / target_purity override the basis values (then labelled as user input).
    """
    P = params()["psa"]
    notes = [f"{MODEL_LABEL}: literature operating point applied as a fixed split; not a designed PSA"]
    if basis == "amcrax_baseline":
        pt = {"recovery": P["amcrax_baseline"]["recovery"], "purity": None, "feed_pressure_bar": None,
              "tail_pressure_bar": None}
        src = cite(P["amcrax_baseline"])
    else:
        pt = psa_point(basis)
        src = cite(pt)
    R = h2_recovery if h2_recovery is not None else pt["recovery"]
    if h2_recovery is not None:
        notes.append(f"H2 recovery {R} given by caller (overrides basis value {pt['recovery']})")
    purity = target_purity if target_purity is not None else pt.get("purity")
    if purity is None:
        purity = P["product_purity_spec"]["value"]
        notes.append(f"basis reports no purity; product purity set to spec {purity} ({cite(P['product_purity_spec'])})")
    if target_purity is not None and pt.get("purity") is not None and target_purity > pt["purity"]:
        notes.append(f"WARNING: target purity {target_purity} exceeds the purity reported with this recovery "
                     f"({pt['purity']}); recovery at higher purity is not known from the source")
    if not (0 <= R <= 1 and 0 < purity <= 1):
        raise ValueError("recovery must be in [0,1], purity in (0,1]")
    feed = {k: float(v) for k, v in feed_kmol_h.items() if v}
    h2_in = feed.get("H2", 0.0)
    h2_p = R * h2_in
    n2_p = min(h2_p * (1.0 - purity) / purity, feed.get("N2", 0.0))
    if n2_p < h2_p * (1.0 - purity) / purity - 1e-12:
        notes.append("feed N2 insufficient to reach purity floor; product purity is higher than target")
    product = {"H2": h2_p, "N2": n2_p}
    tail = {k: v - product.get(k, 0.0) for k, v in feed.items()}
    tail = {k: max(v, 0.0) for k, v in tail.items()}
    ttot = sum(tail.values())
    y_tail = {k: v / ttot for k, v in tail.items()} if ttot > 0 else {}
    # pressure requirement
    if required_feed_pressure_bar is None:
        req = pt.get("feed_pressure_bar") or P["feed_pressure_requirement_bar"]["default"]
        req_src = cite(pt) if pt.get("feed_pressure_bar") else cite(P["feed_pressure_requirement_bar"])
    else:
        req, req_src = required_feed_pressure_bar, "caller input"
    if tailgas_pressure_bar is None:
        tailgas_pressure_bar = pt.get("tail_pressure_bar") or 1.2
        if not pt.get("tail_pressure_bar"):
            notes.append("tail-gas pressure 1.2 bar taken from cho2026nickel p. 6 Table 3 (labelled 'Assumed' there)")
    P_ads = max(feed_pressure_bar, req)
    comp = {"power_kW": 0.0, "stages": 0, "eta": None}
    if feed_pressure_bar < req:
        ftot = sum(feed.values())
        comp = compression_power_kW(ftot, feed, feed_temperature_K, feed_pressure_bar, req,
                                    compressor_stages, compressor_eta)
        notes.append(f"feed {feed_pressure_bar:.2f} bar < required {req:.2f} bar: cracked-gas compression "
                     f"{comp['power_kW']:.1f} kW ({comp['stages']} stages, eta {comp['eta']})")
    kg_h2 = h2_p * MOLAR_MASS["H2"]
    loss = h2_in - h2_p
    nh3_ppm = 1e6 * product.get("NH3", 0.0) / max(h2_p + n2_p, 1e-30)
    return PSAResult(
        basis=basis, basis_source=src, h2_recovery=R, h2_purity_mole_frac=h2_p / (h2_p + n2_p) if h2_p > 0 else 0.0,
        feed_kmol_h=feed, product_kmol_h=product, tailgas_kmol_h=tail, tailgas_mole_frac=y_tail,
        feed_pressure_bar=feed_pressure_bar, required_feed_pressure_bar=req, required_feed_pressure_source=req_src,
        tailgas_pressure_bar=tailgas_pressure_bar, pressure_ratio_feed_to_tail=P_ads / tailgas_pressure_bar,
        compression_power_kW=comp["power_kW"], compression_stages=comp["stages"], compression_eta=comp["eta"],
        product_h2_kg_h=kg_h2,
        specific_energy_kWh_per_kgH2=comp["power_kW"] / kg_h2 if kg_h2 > 0 else float("nan"),
        h2_loss_kmol_h=loss, h2_loss_lhv_kW=loss * LHV_KJ_PER_MOL["H2"] / 3.6,
        nh3_in_product_ppm=nh3_ppm, notes=notes,
    )
