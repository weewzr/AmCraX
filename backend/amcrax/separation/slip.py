"""Ammonia slip vs. the fuel-cell hydrogen quality limit (requirement only; no adsorber is designed)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .params import MODEL_LABEL, cite, params


class AmmoniaSlipResult(BaseModel):
    model: str = MODEL_LABEL
    nh3_cracked_gas_kmol_h: float
    nh3_cracked_gas_ppm: float
    limit_ppm: float
    limit_source: str
    product_kmol_h: float
    nh3_allowed_in_product_kmol_h: float
    required_nh3_removal_factor: float
    meets_limit_without_removal: bool
    removal_evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def ammonia_slip(cracked_gas_kmol_h: dict[str, float], product_kmol_h: float | None = None) -> AmmoniaSlipResult:
    """Required NH3 removal factor so that the H2 product meets the 0.1 ppm limit.

    product_kmol_h: product flow the NH3 ends up in (default: H2 in the cracked gas, i.e. all H2 recovered).
    Removal factor = 1 - (limit * product) / NH3 in cracked gas (fraction of the cracked-gas NH3 that
    must be removed before / in purification).
    """
    S = params()["ammonia_slip"]
    lim = S["fuel_cell_limit_ppm"]
    nh3 = float(cracked_gas_kmol_h.get("NH3", 0.0))
    tot = sum(cracked_gas_kmol_h.values())
    prod = product_kmol_h if product_kmol_h is not None else float(cracked_gas_kmol_h.get("H2", 0.0))
    allowed = lim["value"] * 1e-6 * prod
    rf = max(0.0, 1.0 - allowed / nh3) if nh3 > 0 else 0.0
    return AmmoniaSlipResult(
        nh3_cracked_gas_kmol_h=nh3, nh3_cracked_gas_ppm=1e6 * nh3 / tot if tot else 0.0, limit_ppm=lim["value"],
        limit_source=cite(lim), product_kmol_h=prod, nh3_allowed_in_product_kmol_h=allowed,
        required_nh3_removal_factor=rf, meets_limit_without_removal=rf == 0.0,
        removal_evidence=[f"{e['method']}: {e.get('outlet_ppm', e.get('H2_recovery'))} ({e['citekey']} p. {e['page']}, "
                          f"{e['locator']})" for e in S["removal_evidence"]],
        notes=[f"{MODEL_LABEL}: requirement only - NH3 removal unit (TSA/adsorber) not designed"],
    )
