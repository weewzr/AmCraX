"""Independent thermochemistry and NH3-cracking equilibrium model (validates Aspen Plus RGibbs).

Run time depends only on numpy/scipy; data files are built from Cantera (gri30.yaml NASA7)
and CoolProp (critical constants) by :mod:`amcrax.thermodynamics.build_data`.
Reaction basis (per mol NH3): NH3 <-> 0.5 N2 + 1.5 H2. Standard state 1 bar.
"""
from .equilibrium import (
    NU,
    EquilibriumResult,
    equilibrium_constant,
    isothermal_reactor_duty_kW,
    mixture_enthalpy_kW,
    reaction_enthalpy_kJ_mol,
    reaction_entropy_J_molK,
    reaction_gibbs_kJ_mol,
    solve_equilibrium,
)
from .nasa7 import (
    R_J_molK,
    species_cp_J_molK,
    species_enthalpy_kJ_mol,
    species_entropy_J_molK,
    species_gibbs_kJ_mol,
    species_list,
)
from .peng_robinson import fugacity_coefficients

__all__ = [
    "NU",
    "EquilibriumResult",
    "R_J_molK",
    "equilibrium_constant",
    "fugacity_coefficients",
    "isothermal_reactor_duty_kW",
    "mixture_enthalpy_kW",
    "reaction_enthalpy_kJ_mol",
    "reaction_entropy_J_molK",
    "reaction_gibbs_kJ_mol",
    "solve_equilibrium",
    "species_cp_J_molK",
    "species_enthalpy_kJ_mol",
    "species_entropy_J_molK",
    "species_gibbs_kJ_mol",
    "species_list",
]
