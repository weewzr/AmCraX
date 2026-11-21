"""AmCraX - Ammonia Cracking Simulation and Optimisation Platform.

Layers (kept deliberately separate):

* ``amcrax.aspen``            - Aspen Plus V15 COM automation (the principal process simulator)
* ``amcrax.thermodynamics``   - independent equilibrium / thermochemistry model
* ``amcrax.kinetics``         - literature rate laws for Ni and Ru catalysts
* ``amcrax.reactor``          - plug-flow reactor model
* ``amcrax.process_model``    - independent Python flowsheet mirroring the Aspen model
* ``amcrax.heat_integration`` - pinch / heat-recovery analysis
* ``amcrax.separation``       - reduced-order PSA / membrane models
* ``amcrax.economics``        - levelised cost of hydrogen
* ``amcrax.environmental``    - carbon-intensity accounting
* ``amcrax.optimisation``     - single- and multi-objective optimisation
* ``amcrax.api``              - FastAPI application
"""

__version__ = "0.1.0"
