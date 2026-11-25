//! Single-reaction gas-phase equilibrium of ammonia decomposition (Python
//! `thermodynamics/equilibrium.py`): `NH3 <-> 0.5 N2 + 1.5 H2`, standard state 1 bar, ideal gas
//! or Peng-Robinson fugacity coefficients. Unknown `z = ln n_NH3`, brentq on
//! `[ln n_max - 690, ln n_max]` with `xtol = 1e-13`, `rtol = 1e-15`, `maxiter = 500`.

use crate::error::EngineError;
use crate::props::Phase;
use crate::pyops::{py_max, py_min, py_sum};
use crate::species::{Comp, Species};
use crate::thermo::nasa7::{Element, Nasa7, R_J_MOL_K};
use crate::thermo::peng_robinson::{self as pr, Alpha, Kij};
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use serde::{Deserialize, Serialize};

/// Stoichiometric coefficients per mol NH3, in the Python dict order (NH3, N2, H2).
pub const NU: [(Species, f64); 3] = [(Species::NH3, -1.0), (Species::N2, 0.5), (Species::H2, 1.5)];
/// Change of the gas mole number per mol NH3 (`sum(NU.values())`).
pub const DN_GAS: f64 = 1.0;

/// Equation of state of the equilibrium (Python `eos`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum Eos {
    #[default]
    Ideal,
    Pr,
}

fn nasa() -> &'static Nasa7 {
    Nasa7::embedded()
}

/// Standard reaction enthalpy per mol NH3, kJ/mol.
pub fn reaction_enthalpy_kj_mol(t_k: f64) -> Result<f64, EngineError> {
    let mut v = [0.0; 3];
    for (k, (s, nu)) in NU.iter().enumerate() {
        v[k] = nu * nasa().enthalpy_kj_mol(*s, t_k)?;
    }
    Ok(py_sum(v))
}

/// Standard (1 bar) reaction Gibbs energy per mol NH3, kJ/mol.
pub fn reaction_gibbs_kj_mol(t_k: f64) -> Result<f64, EngineError> {
    let mut v = [0.0; 3];
    for (k, (s, nu)) in NU.iter().enumerate() {
        v[k] = nu * nasa().gibbs_kj_mol(*s, t_k)?;
    }
    Ok(py_sum(v))
}

/// Standard reaction entropy per mol NH3, J/(mol K).
pub fn reaction_entropy_j_mol_k(t_k: f64) -> Result<f64, EngineError> {
    Ok((reaction_enthalpy_kj_mol(t_k)? - reaction_gibbs_kj_mol(t_k)?) * 1000.0 / t_k)
}

/// Kp (standard state 1 bar) of `NH3 <-> 0.5 N2 + 1.5 H2`.
pub fn equilibrium_constant(t_k: f64) -> Result<f64, EngineError> {
    Ok((-reaction_gibbs_kj_mol(t_k)? * 1000.0 / (R_J_MOL_K * t_k)).exp())
}

/// Result of [`solve_equilibrium`] (Python `EquilibriumResult`). Per-species lists are in
/// species order and hold the species Python keeps (NH3, H2, N2, plus inerts with flow > 0).
#[derive(Debug, Clone, PartialEq)]
pub struct EquilibriumResult {
    pub t_k: f64,
    pub p_bar: f64,
    pub eos: Eos,
    /// `1 - n_NH3,out / n_NH3,in` (NaN without NH3 in the feed).
    pub conversion: f64,
    /// NH3 decomposed, feed units (< 0: net synthesis).
    pub extent: f64,
    pub n_out: Vec<(Species, f64)>,
    pub y: Vec<(Species, f64)>,
    pub k_eq: f64,
    pub phi: Vec<(Species, f64)>,
    pub residual: f64,
    pub iterations: u32,
    pub function_calls: u32,
}

fn get(v: &[(Species, f64)], s: Species) -> f64 {
    v.iter().find(|x| x.0 == s).map(|x| x.1).unwrap_or(0.0)
}

fn set(v: &mut [(Species, f64)], s: Species, val: f64) {
    if let Some(x) = v.iter_mut().find(|x| x.0 == s) {
        x.1 = val;
    }
}

/// Equilibrium composition at `t_k`, `p_bar` for the feed `n_feed` (any molar unit; Python
/// `solve_equilibrium`). `kij` and `alpha` are used only with [`Eos::Pr`].
pub fn solve_equilibrium(
    t_k: f64,
    p_bar: f64,
    n_feed: &Comp,
    eos: Eos,
    kij: &Kij,
    alpha: Alpha,
) -> Result<EquilibriumResult, EngineError> {
    for (s, v) in Species::ALL.iter().zip(n_feed) {
        if !v.is_finite() {
            return Err(EngineError::Domain(format!(
                "feed flow of {} is not finite",
                s.name()
            )));
        }
        if *v < 0.0 {
            return Err(EngineError::Domain("negative feed flow".into()));
        }
    }
    let feed: Vec<(Species, f64)> = Species::ALL
        .iter()
        .zip(n_feed)
        .filter(|(s, v)| **v > 0.0 || NU.iter().any(|(n, _)| n == *s))
        .map(|(s, v)| (*s, *v))
        .collect();
    let n_nh3_in = get(&feed, Species::NH3);
    let n_nh3_max = n_nh3_in + py_min(get(&feed, Species::N2) / 0.5, get(&feed, Species::H2) / 1.5);
    if n_nh3_max <= 0.0 {
        return Err(EngineError::Domain(
            "feed contains no NH3 and cannot form any (needs both H2 and N2)".into(),
        ));
    }
    let lnk = -reaction_gibbs_kj_mol(t_k)? * 1000.0 / (R_J_MOL_K * t_k);
    let lnp = (p_bar / 1.0).ln();

    let state = |z: f64| -> (Vec<(Species, f64)>, f64) {
        let n_nh3 = z.exp();
        let xi = n_nh3_in - n_nh3;
        let mut n = feed.clone();
        set(&mut n, Species::NH3, n_nh3);
        set(&mut n, Species::N2, get(&feed, Species::N2) + 0.5 * xi);
        set(&mut n, Species::H2, get(&feed, Species::H2) + 1.5 * xi);
        (n, xi)
    };
    let phis = |n: &[(Species, f64)]| -> Result<Vec<(Species, f64)>, EngineError> {
        match eos {
            Eos::Ideal => Ok(n.iter().map(|x| (x.0, 1.0)).collect()),
            Eos::Pr => {
                let tot = py_sum(n.iter().map(|x| x.1));
                let y: Vec<(Species, f64)> = n.iter().map(|x| (x.0, x.1 / tot)).collect();
                pr::fugacity_coefficients(&y, t_k, p_bar, kij, alpha, Phase::Vapour)
            }
        }
    };
    let resid = |z: f64| -> Result<f64, EngineError> {
        let (n, _) = state(z);
        let tot = py_sum(n.iter().map(|x| x.1));
        let ph = phis(&n)?;
        let mut val = DN_GAS * lnp - lnk;
        for (s, nu) in NU {
            val += nu * ((py_max(get(&n, s), 1e-300) / tot).ln() + get(&ph, s).ln());
        }
        Ok(val)
    };

    let z_hi = n_nh3_max.ln();
    let z_lo = z_hi - 690.0;
    let (f_lo, f_hi) = (resid(z_lo)?, resid(z_hi)?);
    if !(f_lo > 0.0 && 0.0 > f_hi) {
        return Err(EngineError::Bracket(format!(
            "equilibrium bracket failed: f({z_lo})={f_lo}, f({z_hi})={f_hi}"
        )));
    }
    let opts = BrentOptions {
        xtol: 1e-13,
        rtol: 1e-15,
        maxiter: 500,
    };
    let root = brentq_try(resid, z_lo, z_hi, opts).map_err(|e| match e {
        BrentError::Function(e) => e,
        BrentError::NotConverged(r) => EngineError::Numerical(format!(
            "equilibrium brentq failed to converge after {} iterations",
            r.iterations
        )),
        BrentError::NanValue { x, .. } => {
            EngineError::Domain(format!("the function value at x={x} is NaN"))
        }
        other => EngineError::Numerical(format!("equilibrium brentq: {other}")),
    })?;
    let z = root.x;
    let (n, xi) = state(z);
    let tot = py_sum(n.iter().map(|x| x.1));
    let y: Vec<(Species, f64)> = n.iter().map(|x| (x.0, x.1 / tot)).collect();
    let ph = phis(&n)?;
    let conv = if n_nh3_in > 0.0 {
        1.0 - get(&n, Species::NH3) / n_nh3_in
    } else {
        f64::NAN
    };
    for (el, name) in [(Element::N, "N"), (Element::H, "H")] {
        let e_in = py_sum(feed.iter().map(|&(s, v)| v * nasa().atoms(s, el)));
        let e_out = py_sum(n.iter().map(|&(s, v)| v * nasa().atoms(s, el)));
        if (e_in - e_out).abs() > 1e-9 * py_max(e_in, 1e-30) {
            return Err(EngineError::Numerical(format!(
                "{name} balance violated: {e_in} vs {e_out}"
            )));
        }
    }
    let residual = resid(z)?;
    Ok(EquilibriumResult {
        t_k,
        p_bar,
        eos,
        conversion: conv,
        extent: xi,
        n_out: n,
        y,
        k_eq: lnk.exp(),
        phi: ph,
        residual,
        iterations: root.iterations,
        function_calls: root.function_calls,
    })
}

/// Total enthalpy flow (formation-enthalpy reference), kW, of flows in kmol/h (Python
/// `mixture_enthalpy_kW`); [`Eos::Pr`] adds the Peng-Robinson residual enthalpy and needs `p_bar`.
pub fn mixture_enthalpy_kw(
    n_kmol_h: &[(Species, f64)],
    t_k: f64,
    p_bar: Option<f64>,
    eos: Eos,
    kij: &Kij,
    alpha: Alpha,
) -> Result<f64, EngineError> {
    let mut terms = Vec::with_capacity(n_kmol_h.len());
    for &(s, v) in n_kmol_h {
        if v != 0.0 {
            terms.push(v * nasa().enthalpy_kj_mol(s, t_k)?);
        }
    }
    let mut h = py_sum(terms);
    let tot = py_sum(n_kmol_h.iter().map(|x| x.1));
    if eos == Eos::Pr && tot > 0.0 {
        let p = p_bar.ok_or_else(|| EngineError::Domain("P_bar required for eos='pr'".into()))?;
        let y: Vec<(Species, f64)> = n_kmol_h
            .iter()
            .filter(|x| x.1 > 0.0)
            .map(|x| (x.0, x.1 / tot))
            .collect();
        h += tot * pr::enthalpy_departure_j_mol(&y, t_k, p, kij, alpha, Phase::Vapour)? / 1000.0;
    }
    Ok(h * 1000.0 / 3600.0)
}

/// Reactor duty `H_out - H_in`, kW (Python `isothermal_reactor_duty_kW`).
pub fn isothermal_reactor_duty_kw(
    n_in: &[(Species, f64)],
    t_in_k: f64,
    n_out: &[(Species, f64)],
    t_out_k: f64,
    p_in_bar: Option<f64>,
    p_out_bar: Option<f64>,
    eos: Eos,
) -> Result<f64, EngineError> {
    let k = Kij::zero();
    Ok(
        mixture_enthalpy_kw(n_out, t_out_k, p_out_bar, eos, &k, Alpha::Standard)?
            - mixture_enthalpy_kw(n_in, t_in_k, p_in_bar, eos, &k, Alpha::Standard)?,
    )
}

/// Ideal-gas equilibrium conversion of a feed (shorthand used by the reactor).
pub fn ideal_conversion(t_k: f64, p_bar: f64, n_feed: &Comp) -> Result<f64, EngineError> {
    Ok(solve_equilibrium(
        t_k,
        p_bar,
        n_feed,
        Eos::Ideal,
        &Kij::zero(),
        Alpha::Standard,
    )?
    .conversion)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn equilibrium_basics() {
        let r = solve_equilibrium(
            873.15,
            20.0,
            &[1.0, 0.0, 0.0, 0.0, 0.0],
            Eos::Ideal,
            &Kij::zero(),
            Alpha::Standard,
        )
        .unwrap();
        assert!(r.conversion > 0.9 && r.conversion < 1.0);
        assert!(r.residual.abs() < 1e-10);
        assert!(
            solve_equilibrium(
                873.15,
                20.0,
                &[-1.0, 0.0, 0.0, 0.0, 0.0],
                Eos::Ideal,
                &Kij::zero(),
                Alpha::Standard
            )
            .is_err()
        );
        let k = equilibrium_constant(873.15).unwrap();
        assert!(k > 100.0);
    }
}
