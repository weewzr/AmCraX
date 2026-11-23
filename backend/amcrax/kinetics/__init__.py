"""Literature rate laws for NH3 decomposition (registry loaded from ``amcrax/data/kinetics.yaml``).

Public API (docs/developer_guide.md section 7)::

    rate_mol_per_kgcat_s(catalyst_id, T_K, p_bar, *, approach_factor=None, keq_basis="published") -> float
    list_catalysts() -> list[CatalystModel]

``p_bar`` is a dict of partial pressures in bar (keys NH3, H2, N2; any other key, e.g. H2O or Ar, is an inert
that only contributes to the total pressure). The returned rate is the NH3 consumption rate in
mol NH3 / (kg_cat s) (positive = net decomposition).

Implemented catalysts (all provenance ``literature``; parameters and units in kinetics.yaml):

* ``ni_takahashi_microkinetic``  30 wt% Ni/MgO, elementary-step model, takahashi2016kinetic Table 1.
* ``ru_takahashi_microkinetic``  5 wt% Ru/MgO, same model, takahashi2016kinetic Table 1.
* ``ru_kum_temkin_pyzhev``       8 wt% Ru/Al2O3, reversible Temkin-Pyzhev, kum2026heatintegrated Eq. 2 / Table 1.

AmCraX extension (labelled assumption, switchable): the Takahashi model is irreversible (steps 2 and 3 have no
reverse), so by default its rate is multiplied by (1 - Q/Kp) with Kp from :mod:`amcrax.thermodynamics`.
Pass ``approach_factor=False`` for the published form.
"""
from .rate_laws import (
    CatalystModel,
    G_PER_KG,
    BAR_PER_ATM,
    R_KIN_J_molK,
    kum_keq,
    list_catalysts,
    list_research_catalysts,
    lucentini_rate_mol_per_g_s,
    get_catalyst,
    rate_mol_per_kgcat_s,
    reaction_quotient,
    takahashi_constants,
    takahashi_coverages,
)

__all__ = [
    "BAR_PER_ATM",
    "CatalystModel",
    "G_PER_KG",
    "R_KIN_J_molK",
    "get_catalyst",
    "kum_keq",
    "list_catalysts",
    "list_research_catalysts",
    "lucentini_rate_mol_per_g_s",
    "rate_mol_per_kgcat_s",
    "reaction_quotient",
    "takahashi_constants",
    "takahashi_coverages",
]
