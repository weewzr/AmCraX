"""Hydrogen purification reduced-order models (PSA split, Pd-Ag membrane, NH3 slip, compression).

All results carry ``model == "reduced-order model"``. None of these is a designed or validated unit:
PSA performance is a literature operating point applied as a split; the membrane uses ideal
Sieverts flux with literature permeability. Parameters: backend/amcrax/data/separation.yaml.
"""
from .compare import ComparisonRow, PurificationComparison, compare_purification, cracked_gas
from .compression import compression_power_kW, default_stages
from .membrane import (MembraneProfilePoint, MembraneResult, area_for_recovery, membrane_separator, permeance,
                       sieverts_flux)
from .params import MODEL_LABEL, params
from .psa import PSAResult, psa_performance
from .slip import AmmoniaSlipResult, ammonia_slip

__all__ = [
    "MODEL_LABEL", "params",
    "compression_power_kW", "default_stages",
    "psa_performance", "PSAResult",
    "membrane_separator", "MembraneResult", "MembraneProfilePoint", "permeance", "sieverts_flux", "area_for_recovery",
    "ammonia_slip", "AmmoniaSlipResult",
    "compare_purification", "PurificationComparison", "ComparisonRow", "cracked_gas",
]
