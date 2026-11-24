//! Propagation of the published Lucentini et al. (2021) Table 3 parameter intervals through the
//! plug-flow reactor (`scripts/research/uq_kinetic_propagation.py`): per draw the three laboratory
//! conversions, eight inlet temperatures for a target conversion (brentq, xtol 0.02 K, bracket
//! 350-900 degC) and the catalyst mass for 99 % of equilibrium at 600 degC and 20 bar.
//!
//! The Latin hypercube is SciPy's with the legacy `seed=` keyword (`default_rng(seed)`), the
//! normal scores `norm.ppf` (Cephes `ndtri`); the draws are therefore reproduced bit for bit up to
//! NumPy's vectorised `log`/`exp` (an ulp). Parallel runs use fixed contiguous chunks of draws
//! and write each result to its own index: the output does not depend on the thread count.

use crate::economics::jf;
use crate::error::EngineError;
use crate::kinetics::KineticsRegistry;
use crate::odata::OValue;
use crate::pyops::fmt_g;
use crate::reactor::{PfrInput, SolverOptions, Target, catalyst_mass_for_conversion, simulate_pfr};
use crate::uq::{SEED, norm_ppf};
use amcrax_numerics::random::Pcg64;
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use amcrax_numerics::stats;
use serde_json::{Value, json};
use std::collections::BTreeMap;

/// The two Lucentini catalysts with their Table 1 laboratory points (degC, conversion).
pub const KP_CATS: [(&str, &str, [f64; 3], [f64; 3]); 2] = [
    (
        "nire_ceo2_5ni1ru_lucentini_lhhw",
        "5Ni1Ru_CeO2",
        [400.0, 450.0, 500.0],
        [0.365, 0.861, 0.996],
    ),
    (
        "nire_ceo2_2p5ni0p5ru_lucentini_lhhw",
        "2p5Ni0p5Ru_CeO2",
        [400.0, 450.0, 500.0],
        [0.497, 0.887, 0.992],
    ),
];
/// 1 atm in bar.
pub const ATM: f64 = 1.01325;
/// Reference temperature of case C2 (475 degC), K.
pub const T_REF_K: f64 = 748.15;
/// Lower end of the temperature bracket, degC.
pub const T_LO: f64 = 350.0;
/// Upper end of the temperature bracket, degC.
pub const T_HI: f64 = 900.0;
/// `(P, W, X)` targets in the Python order.
pub const TARGETS: [(f64, f64, f64); 8] = [
    (ATM, 100.0, 0.95),
    (ATM, 100.0, 0.99),
    (ATM, 1000.0, 0.95),
    (ATM, 1000.0, 0.99),
    (20.0, 100.0, 0.95),
    (20.0, 100.0, 0.99),
    (20.0, 1000.0, 0.95),
    (20.0, 1000.0, 0.99),
];
/// Parameter names in the draw order.
pub const KP_PARAMS: [&str; 4] = ["k0", "Ek", "K1", "K4"];

/// Python key `f"P{P:g}_W{W:g}_X{X:g}"`.
pub fn target_key(p: f64, w: f64, x: f64) -> String {
    format!("P{}_W{}_X{}", fmt_g(p, 6), fmt_g(w, 6), fmt_g(x, 6))
}

/// One parameter draw (`k0`, `Ek`, `K1`, `K4`).
pub type Draw = [f64; 4];

/// Outputs of `run_draw`.
#[derive(Debug, Clone, PartialEq)]
pub struct DrawOut {
    pub x_lab: [f64; 3],
    /// `(T_required_C or None, reason)` per target.
    pub t_req: Vec<(Option<f64>, String)>,
    pub m_frac99: Option<f64>,
    /// PFR solves done for this draw.
    pub n_pfr: usize,
    /// Solves that needed the stiff fallback.
    pub n_stiff: usize,
}

/// Fixed inputs of the propagation study.
pub struct KpSetup<'a> {
    pub reg: &'a KineticsRegistry,
    pub sopt: SolverOptions,
    /// `(nominal, half-width)` per catalyst, in `KP_PARAMS` order.
    pub nominal: Vec<(Draw, Draw)>,
    pub r_kin: f64,
}

fn feed100() -> BTreeMap<String, f64> {
    [("NH3".to_string(), 100.0)].into_iter().collect()
}

struct Counter {
    n: usize,
    stiff: usize,
}

impl<'a> KpSetup<'a> {
    /// Nominal values and published half-widths from the parsed `kinetics.yaml`.
    pub fn new(reg: &'a KineticsRegistry, kinetics_yaml: &OValue) -> Result<Self, EngineError> {
        let mut nominal = Vec::new();
        for (cid, ..) in KP_CATS {
            let mut node = kinetics_yaml.at(&["research_catalysts", cid, "parameters"]);
            if node.is_null() {
                node = kinetics_yaml.at(&["catalysts", cid, "parameters"]);
            }
            let mut nom = [0.0; 4];
            let mut unc = [0.0; 4];
            for (i, k) in KP_PARAMS.iter().enumerate() {
                nom[i] = node.num("kinetics.yaml", &[k, "value"])?;
                unc[i] = node.num("kinetics.yaml", &[k, "uncertainty"])?;
            }
            nominal.push((nom, unc));
        }
        Ok(KpSetup {
            reg,
            sopt: SolverOptions::default(),
            nominal,
            r_kin: reg.r_kin_j_mol_k,
        })
    }

    /// Python `draws(cid, case, n, rng_seed)`: C1 independent (lognormal k0, K1, K4; normal Ek),
    /// C2 centred at T_ref (ln k_ref independent of Ek).
    pub fn draws(&self, cat: usize, c2: bool, n: usize, seed: u64) -> Vec<Draw> {
        let (nom, unc) = self.nominal[cat];
        let mut rng = Pcg64::from_seed(u128::from(seed));
        let u = amcrax_numerics::qmc::latin_hypercube(n, 4, true, &mut rng);
        let s_rel = |i: usize| unc[i] / nom[i] / 1.96;
        let s_ek = unc[1] / 1.96;
        let rt = self.r_kin * T_REF_K;
        u.iter()
            .map(|row| {
                let z: Vec<f64> = row.iter().map(|x| norm_ppf(*x)).collect();
                let ek = nom[1] + s_ek * z[1];
                let k1 = (nom[2].ln() + s_rel(2) * z[2]).exp();
                let k4 = (nom[3].ln() + s_rel(3) * z[3]).exp();
                let k0 = if c2 {
                    let kref_nom = nom[0] * (-nom[1] * 1e3 / rt).exp();
                    let kref = (kref_nom.ln() + s_rel(0) * z[0]).exp();
                    kref * (ek * 1e3 / rt).exp()
                } else {
                    (nom[0].ln() + s_rel(0) * z[0]).exp()
                };
                [k0, ek, k1, k4]
            })
            .collect()
    }

    fn base(&self, cid: &str, ov: Option<&Draw>) -> PfrInput {
        let mut b = PfrInput::new(cid, 1.0);
        b.param_overrides = ov.map(|d| {
            KP_PARAMS
                .iter()
                .zip(d)
                .map(|(k, v)| (k.to_string(), *v))
                .collect()
        });
        b
    }

    fn solve(&self, inp: &PfrInput, c: &mut Counter) -> Result<f64, EngineError> {
        c.n += 1;
        let r = simulate_pfr(self.reg, inp, &self.sopt)?;
        if r.solver.method.starts_with("ROS2") {
            c.stiff += 1;
        }
        Ok(r.outlet.conversion)
    }

    /// Python `run_draw((cid, ov, skip_abs99))`; the absolute X = 0.99 mass is skipped because
    /// X_eq(600 degC, 20 bar) < 0.99 (as in the stored study).
    pub fn run_draw(&self, cat: usize, ov: Option<&Draw>) -> Result<DrawOut, EngineError> {
        let (cid, _, t_lab, _) = KP_CATS[cat];
        let mut c = Counter { n: 0, stiff: 0 };
        let n = 25.0 * 1e-3 * 60.0 / 22.414 / 1000.0;
        let lab_feed: BTreeMap<String, f64> = [
            ("NH3".to_string(), n / (1.0 + 1.2)),
            ("Ar".to_string(), n * 1.2 / (1.0 + 1.2)),
        ]
        .into_iter()
        .collect();
        let mut x_lab = [0.0; 3];
        for (j, t) in t_lab.iter().enumerate() {
            let mut inp = self.base(cid, ov);
            inp.w_kg = 1e-4;
            inp.t_in_c = *t;
            inp.p_in_bar = ATM;
            inp.feed_kmol_h = Some(lab_feed.clone());
            inp.pressure_drop = false;
            inp.n_points = 3;
            x_lab[j] = self.solve(&inp, &mut c)?;
        }
        let study_inp = |w: f64, t: f64, p: f64| -> PfrInput {
            let mut inp = self.base(cid, ov);
            inp.w_kg = w;
            inp.t_in_c = t;
            inp.p_in_bar = p;
            inp.feed_kmol_h = Some(feed100());
            inp.pressure_drop = false;
            inp.eps_b = 0.36;
            inp.rho_particle_kg_m3 = 1651.8;
            inp.n_points = 2;
            inp
        };
        let mut t_req: Vec<(Option<f64>, String)> = Vec::with_capacity(8);
        for (k, (p, w, xt)) in TARGETS.iter().copied().enumerate() {
            let mut lo = T_LO;
            if xt == 0.99
                && k > 0
                && let Some((Some(prev), _)) = t_req.get(k - 1)
            {
                lo = *prev;
            }
            let comp = [100.0, 0.0, 0.0, 0.0, 0.0];
            let xe = crate::thermo::equilibrium::ideal_conversion(T_HI + 273.15, p, &comp)?;
            if xe < xt {
                t_req.push((None, "X_eq below target at 900 degC".into()));
                continue;
            }
            let glo = self.solve(&study_inp(w, lo, p), &mut c).map(|x| x - xt);
            let ghi = self.solve(&study_inp(w, T_HI, p), &mut c).map(|x| x - xt);
            let (glo, ghi) = match (glo, ghi) {
                (Ok(a), Ok(b)) => (a, b),
                (Err(e), _) | (_, Err(e)) => {
                    t_req.push((None, format!("solver error {e}")));
                    continue;
                }
            };
            if glo >= 0.0 {
                t_req.push(if lo == T_LO {
                    (None, "target reached at 350 degC (below bracket)".into())
                } else {
                    (Some(lo), String::new())
                });
                continue;
            }
            if ghi < 0.0 {
                t_req.push((None, "target not reached between 350 and 900 degC".into()));
                continue;
            }
            let cell = std::cell::RefCell::new(&mut c);
            let g = |t: f64| -> Result<f64, EngineError> {
                let mut cc = cell.borrow_mut();
                self.solve(&study_inp(w, t, p), &mut **cc).map(|x| x - xt)
            };
            let r =
                brentq_try(g, lo, T_HI, BrentOptions::with_xtol(0.02)).map_err(|e| match e {
                    BrentError::Function(e) => e,
                    other => EngineError::Numerical(format!("brentq: {other}")),
                })?;
            t_req.push((Some(r.x), String::new()));
        }
        let mut mb = self.base(cid, ov);
        mb.t_in_c = 600.0;
        mb.p_in_bar = 20.0;
        mb.feed_kmol_h = Some(feed100());
        mb.pressure_drop = false;
        mb.eps_b = 0.36;
        mb.rho_particle_kg_m3 = 1651.8;
        let m = catalyst_mass_for_conversion(
            self.reg,
            &mb,
            Target::FractionOfEquilibrium(0.99),
            1e7,
            &self.sopt,
        )?;
        Ok(DrawOut {
            x_lab,
            t_req,
            m_frac99: if m.reachable { Some(m.w_kg) } else { None },
            n_pfr: c.n + m.n_pfr,
            n_stiff: c.stiff,
        })
    }

    /// `run_draw` over `draws` on `threads` threads (fixed contiguous chunks; each result goes to
    /// its own index, so the output does not depend on the thread count).
    pub fn run_all(
        &self,
        cat: usize,
        draws: &[Draw],
        threads: usize,
    ) -> Result<Vec<DrawOut>, EngineError> {
        if draws.is_empty() {
            return Ok(Vec::new());
        }
        let threads = threads.clamp(1, draws.len());
        let chunk = draws.len().div_ceil(threads);
        let mut out: Vec<Option<Result<DrawOut, EngineError>>> = vec![None; draws.len()];
        std::thread::scope(|sc| {
            for (dch, och) in draws.chunks(chunk).zip(out.chunks_mut(chunk)) {
                sc.spawn(move || {
                    for (d, o) in dch.iter().zip(och.iter_mut()) {
                        *o = Some(self.run_draw(cat, Some(d)));
                    }
                });
            }
        });
        out.into_iter()
            .map(|o| o.unwrap_or_else(|| Err(EngineError::Numerical("draw not run".into()))))
            .collect()
    }
}

/// Python `summ(vals)`: n, n_not_reached, mean, sd (ddof 1), p5, p50, p95 of the finite values.
pub fn summ(vals: &[Option<f64>]) -> Value {
    let v: Vec<f64> = vals
        .iter()
        .flatten()
        .copied()
        .filter(|x| x.is_finite())
        .collect();
    let n_nr = vals.len() - v.len();
    if v.is_empty() {
        return json!({"n": 0, "n_not_reached": n_nr});
    }
    let q = stats::quantiles(&v, &[0.05, 0.5, 0.95]);
    let sd = if v.len() > 1 { stats::std(&v, 1) } else { 0.0 };
    json!({"n": v.len(), "n_not_reached": n_nr, "mean": jf(stats::mean(&v)), "sd": jf(sd),
           "p5": jf(q[0]), "p50": jf(q[1]), "p95": jf(q[2])})
}

/// One case of one catalyst: name, draws, outputs.
pub type KpCase = (String, Vec<Draw>, Vec<DrawOut>);

/// One catalyst of the study: id, cases (C1, C2 and, if at least 2 % are accepted, C3 = the C1
/// draws whose three laboratory conversions lie within +/-10 % of Table 1), acceptance rate.
pub type KpCatalyst = (String, Vec<KpCase>, f64);

/// The propagation study (`n` draws per case, C1 and C2 of both catalysts; `limit` runs only the
/// first draws of each case, for timing: the Latin hypercube is still that of `n` draws).
pub fn kinetic_propagation(
    st: &KpSetup,
    n: usize,
    limit: Option<usize>,
    threads: usize,
) -> Result<Vec<KpCatalyst>, EngineError> {
    let mut res = Vec::new();
    let m = limit.unwrap_or(n).min(n);
    for (cat, (cid, _, _, xpub)) in KP_CATS.iter().enumerate() {
        let mut d1 = st.draws(cat, false, n, SEED);
        d1.truncate(m);
        let o1 = st.run_all(cat, &d1, threads)?;
        let mut d2 = st.draws(cat, true, n, SEED);
        d2.truncate(m);
        let o2 = st.run_all(cat, &d2, threads)?;
        let acc: Vec<bool> = o1
            .iter()
            .map(|o| {
                o.x_lab
                    .iter()
                    .zip(xpub)
                    .all(|(x, xo)| (x / xo - 1.0).abs() <= 0.10)
            })
            .collect();
        let rate = acc.iter().filter(|a| **a).count() as f64 / acc.len().max(1) as f64;
        let d3: Vec<Draw> = d1
            .iter()
            .zip(&acc)
            .filter(|(_, a)| **a)
            .map(|(d, _)| *d)
            .collect();
        let o3: Vec<DrawOut> = o1
            .iter()
            .zip(&acc)
            .filter(|(_, a)| **a)
            .map(|(o, _)| o.clone())
            .collect();
        let mut cases: Vec<KpCase> = vec![("C1".into(), d1, o1), ("C2".into(), d2, o2)];
        if rate >= 0.02 {
            cases.push(("C3".into(), d3, o3));
        }
        res.push((cid.to_string(), cases, rate));
    }
    Ok(res)
}

/// The per-case summaries of the stored JSON that depend only on the draws and the reactor
/// (`param_*`, `X_lab_*`, `T_required_C_*`, the frac-eq-0.99 catalyst mass).
pub fn case_summary(draws: &[Draw], outs: &[DrawOut], t_lab: &[f64; 3]) -> Value {
    let mut m = serde_json::Map::new();
    m.insert("n_draws".into(), json!(draws.len()));
    for (i, k) in KP_PARAMS.iter().enumerate() {
        let v: Vec<Option<f64>> = draws.iter().map(|d| Some(d[i])).collect();
        m.insert(format!("param_{k}"), summ(&v));
    }
    for (j, t) in t_lab.iter().enumerate() {
        let v: Vec<Option<f64>> = outs.iter().map(|o| Some(o.x_lab[j])).collect();
        m.insert(format!("X_lab_{}C", fmt_g(*t, 6)), summ(&v));
    }
    for (k, (p, w, x)) in TARGETS.iter().enumerate() {
        let v: Vec<Option<f64>> = outs.iter().map(|o| o.t_req[k].0).collect();
        m.insert(format!("T_required_C_{}", target_key(*p, *w, *x)), summ(&v));
    }
    let v: Vec<Option<f64>> = outs.iter().map(|o| o.m_frac99).collect();
    m.insert(
        "catalyst_mass_kg_per_100kmolh_frac_eq99_600C_20bar".into(),
        summ(&v),
    );
    Value::Object(m)
}
