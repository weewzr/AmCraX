"""Packed-bed plug-flow reactor (1-D pseudo-homogeneous). See :mod:`amcrax.reactor.pfr` for equations,
assumptions and the list of neglected effects (effectiveness factor, radial gradients, axial dispersion)."""
from .pfr import (
    BASELINE_FEED_kmol_h,
    DEFAULT_BED,
    DEFAULT_BED_SOURCE,
    PFRResult,
    catalyst_mass_for_conversion,
    gas_viscosity_Pa_s,
    simulate_pfr,
)

__all__ = [
    "BASELINE_FEED_kmol_h",
    "DEFAULT_BED",
    "DEFAULT_BED_SOURCE",
    "PFRResult",
    "catalyst_mass_for_conversion",
    "gas_viscosity_Pa_s",
    "simulate_pfr",
]
