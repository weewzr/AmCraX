//! Numerical methods for AmCraX, written to reproduce the Python reference (SciPy and NumPy).
//!
//! The crate has no dependencies, no I/O and no AmCraX physics. Each routine states how closely it
//! reproduces its reference:
//!
//! | Module | Routine | Reference | Agreement |
//! |---|---|---|---|
//! | [`roots`] | [`roots::brentq`] | `scipy.optimize.brentq` | bit for bit (same iterates) |
//! | [`ode`] | [`ode::dopri5`] | `scipy.integrate.solve_ivp(method="RK45")` | same steps and RHS count; values within 0.05 x tolerance |
//! | [`interp`] | [`interp::Pchip`] | `scipy.interpolate.PchipInterpolator` | bit for bit |
//! | [`interp`] | [`interp::interp_linear`] | `numpy.interp` | bit for bit |
//! | [`interp`] | [`interp::Bilinear`] | browser model (`frontend/src/sim`) | bit for bit |
//! | [`poly`] | [`poly::cubic_real_roots`] | `numpy.roots` | 1e-10 relative |
//! | [`stats`] | sum, mean, var, std, median, quantile | NumPy (`method="linear"`) | bit for bit |
//! | [`random`] | [`random::SeedSequence`], [`random::Pcg64`] | `numpy.random.default_rng` | bit for bit for `random()`, `uniform()`, raw output |
//! | [`special`] | [`special::ndtri`] | `scipy.special.ndtri` (Cephes) | bit for bit |
//! | [`qmc`] | [`qmc::Sobol`], [`qmc::latin_hypercube`] | `scipy.stats.qmc` | bit for bit for the recorded versions |
//!
//! The golden tables that prove these statements are generated once by
//! `rust/golden/generate_numerics_golden.py` and checked by `tests/golden.rs`.
//!
//! Floating point: no fused multiply-add is used anywhere (`mul_add` is never called), and the
//! operation order follows the reference code, so results do not depend on the compiler's
//! contraction choices.

pub mod interp;
pub mod ode;
pub mod poly;
pub mod qmc;
pub mod random;
pub mod roots;
mod sobol_directions;
pub mod special;
pub mod stats;
