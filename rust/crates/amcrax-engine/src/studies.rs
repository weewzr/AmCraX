//! Research studies ported from `scripts/research/` (stage 3): the Sobol' global sensitivity
//! analysis of the Singapore economics (`uq_gsa_sobol.py`) and the economics Monte Carlo
//! (`economics_singapore.py`, section 6). Each study returns the JSON block the Python script
//! writes, so the verifier can compare it with the stored file key by key.
//!
//! Random streams: the Sobol' base sample is SciPy's scrambled Sobol' (legacy `seed=` keyword,
//! `default_rng(seed)` without spawn), the bootstrap indices are `default_rng(seed).integers`, the
//! Monte Carlo draws are `default_rng(seed).uniform / triangular / random`; all are reproduced
//! bit for bit (`amcrax_numerics::random`, `amcrax_numerics::qmc`).

pub mod kinetic;

use crate::economics::jf;
use crate::economics::lcoh::EconAssumptions;
use crate::economics::reference::{EconomicsData, SINGAPORE_YAML};
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate_prepared, prepare};
use crate::error::EngineError;
use crate::pyops::fmt_g;
use crate::uq::{
    Matrix, SEED, ab_matrix, bootstrap_ci, clip, indices_from_outputs, lognorm_ppf, sobol_base,
    tri_ppf,
};
use amcrax_numerics::random::Pcg64;
use amcrax_numerics::roots::{BrentOptions, brentq};
use amcrax_numerics::stats;
use serde_json::{Map, Value, json};

/// Base sample size of the global sensitivity analysis (`N = 2 ** 13`).
pub const GSA_N: usize = 8192;
/// Bootstrap resamples (`N_BOOT`).
pub const GSA_N_BOOT: usize = 1000;
/// Outputs of the model (`OUTPUTS`).
pub const GSA_OUTPUTS: [&str; 3] = ["lcoh_USD_per_kg", "rec_USD_per_kg", "npv_USD"];
/// Scenarios of the analysis (`SCEN`).
pub const GSA_SCEN: [&str; 4] = ["grey", "blue", "green_current", "green_2030"];
/// Inputs (`INPUTS`), in column order.
pub const GSA_INPUTS: [&str; 10] = [
    "nh3_price_USD_per_t",
    "electricity_price_USD_per_kWh",
    "capex_multiplier",
    "capex_scaling_exponent",
    "catalyst_price_USD_per_kg",
    "catalyst_lifetime_yr",
    "discount_rate",
    "operating_hours_h_per_yr",
    "plant_life_yr",
    "psa_recovery",
];
/// Input groups (`GROUPS`), in order.
pub const GSA_GROUPS: [(&str, &[&str]); 4] = [
    ("feed", &["nh3_price_USD_per_t"]),
    (
        "capital",
        &[
            "capex_multiplier",
            "capex_scaling_exponent",
            "discount_rate",
            "plant_life_yr",
        ],
    ),
    (
        "operation",
        &[
            "operating_hours_h_per_yr",
            "electricity_price_USD_per_kWh",
            "psa_recovery",
        ],
    ),
    (
        "catalyst",
        &["catalyst_price_USD_per_kg", "catalyst_lifetime_yr"],
    ),
];

/// One input distribution (percent-point function of a uniform variate).
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Dist {
    Triangular(f64, f64, f64),
    Uniform(f64, f64),
    LogNormal(f64),
}

impl Dist {
    /// The PPF at `u` (the lambdas of `dists`).
    #[inline]
    pub fn ppf(&self, u: f64) -> f64 {
        match *self {
            Dist::Triangular(lo, md, hi) => tri_ppf(u, lo, md, hi),
            Dist::Uniform(lo, hi) => lo + u * (hi - lo),
            Dist::LogNormal(s) => lognorm_ppf(u, s, 1.0),
        }
    }
}

/// Distributions, their descriptions and the input names (Python `D, names`).
pub type DistSet = (Vec<Dist>, Vec<String>, Vec<String>);

/// The fixed inputs of the analysis (read from the data files and the stored tornado).
#[derive(Debug, Clone)]
pub struct GsaSetup<'a> {
    pub d: &'a EconomicsData,
    pub cat_price: f64,
    pub capx: (f64, f64),
    pub life: (f64, f64),
    pub psa: (f64, f64),
    pub ct: (f64, f64),
    pub sig_ln: f64,
    pub w_tri: f64,
    pub n: usize,
    pub n_boot: usize,
}

fn tb_range(tornado: &Value, key: &str) -> Result<(f64, f64), EngineError> {
    let bar = tornado["bars"]
        .as_array()
        .and_then(|b| b.iter().find(|x| x["parameter"] == key))
        .ok_or_else(|| EngineError::data("tornado.json", format!("bar {key}")))?;
    let lo = bar["low_input"].as_f64().unwrap_or(f64::NAN);
    let hi = bar["high_input"].as_f64().unwrap_or(f64::NAN);
    Ok(if hi < lo { (hi, lo) } else { (lo, hi) })
}

impl<'a> GsaSetup<'a> {
    /// Module-level constants of `uq_gsa_sobol.py` (`tornado`: results/research/singapore/tornado.json).
    pub fn new(d: &'a EconomicsData, tornado: &Value) -> Result<Self, EngineError> {
        let cat_price = EconAssumptions::defaults(d)?.resolved_catalyst_price_usd_per_kg()?;
        let capx = tb_range(tornado, "capex_multiplier")?;
        let w_tri = tri_ppf(0.95, capx.0, 1.0, capx.1) - tri_ppf(0.05, capx.0, 1.0, capx.1);
        let z = 1.6448536269514722;
        let sig = brentq(
            |s: f64| (z * s).exp() - (-z * s).exp() - w_tri,
            1e-6,
            3.0,
            BrentOptions::default(),
        )
        .map_err(|e| EngineError::Numerical(format!("lognormal sigma: {e}")))?
        .x;
        Ok(GsaSetup {
            d,
            cat_price,
            capx,
            life: tb_range(tornado, "catalyst_lifetime_yr")?,
            psa: tb_range(tornado, "psa_recovery")?,
            ct: tb_range(tornado, "carbon_tax_SGD_per_t")?,
            sig_ln: sig,
            w_tri,
            n: GSA_N,
            n_boot: GSA_N_BOOT,
        })
    }

    /// Python `dists(scen, capex_shape, dummy)`: distributions, their descriptions, input names.
    pub fn dists(&self, scen: &str, lognormal: bool, dummy: bool) -> Result<DistSet, EngineError> {
        let r = &self.d.reference;
        let sd = |k: &str| {
            self.d
                .singapore
                .num(SINGAPORE_YAML, &["nh3_price_scenarios_USD_per_t", scen, k])
        };
        let (lo, md, hi) = (sd("low")?, r.nh3_price(scen)?, sd("high")?);
        let e = r.sens("electricity_USD_per_kWh")?;
        let x = r.sens("capex_scaling_exponent")?;
        let dr = r.sens("discount_rate")?;
        let oh = r.sens("operating_hours_h_per_yr")?;
        let pl = r.sens("plant_life_yr")?;
        let g = |v: f64| fmt_g(v, 6);
        let (capx, capx_desc) = if lognormal {
            (
                Dist::LogNormal(self.sig_ln),
                format!(
                    "lognormal(median 1, sigma {:.4}; same 5-95 % width {:.4} as the triangular) \
                     assumption: right-skewed CAPEX, shape after Stewart and Shirvan 2023, no chemical-plant data",
                    self.sig_ln, self.w_tri
                ),
            )
        } else {
            (
                Dist::Triangular(self.capx.0, 1.0, self.capx.1),
                format!(
                    "triangular({}, 1, {}) Cho 2026 Table 8",
                    g(self.capx.0),
                    g(self.capx.1)
                ),
            )
        };
        let c = self.cat_price;
        let mut dd = vec![
            (
                Dist::Triangular(lo, md, hi),
                format!(
                    "triangular({}, {}, {}) data/singapore.yaml range, reference-scenario base",
                    g(lo),
                    g(md),
                    g(hi)
                ),
            ),
            (
                Dist::Uniform(e.0, e.1),
                format!(
                    "uniform({}, {}) REF.sens electricity_USD_per_kWh",
                    g(e.0),
                    g(e.1)
                ),
            ),
            (capx, capx_desc),
            (
                Dist::Uniform(x.0, x.1),
                format!(
                    "uniform({}, {}) REF.sens capex_scaling_exponent",
                    g(x.0),
                    g(x.1)
                ),
            ),
            (
                Dist::Triangular(0.5 * c, c, 2.0 * c),
                format!("triangular(0.5x, 1x, 2x of {}) Cho 2026 Table 8", g(c)),
            ),
            (
                Dist::Uniform(self.life.0, self.life.1),
                format!(
                    "uniform({}, {}) Cho 2026 Table 8",
                    g(self.life.0),
                    g(self.life.1)
                ),
            ),
            (
                Dist::Uniform(dr.0, dr.1),
                format!("uniform({}, {}) REF.sens discount_rate", g(dr.0), g(dr.1)),
            ),
            (
                Dist::Uniform(oh.0, oh.1),
                format!(
                    "uniform({}, {}) REF.sens operating_hours_h_per_yr",
                    g(oh.0),
                    g(oh.1)
                ),
            ),
            (
                Dist::Uniform(pl.0, pl.1),
                format!(
                    "uniform({}, {}) REF.sens plant_life_yr (NPV: int(round) step)",
                    g(pl.0),
                    g(pl.1)
                ),
            ),
            (
                Dist::Uniform(self.psa.0, self.psa.1),
                format!(
                    "uniform({}, {}) Cho 2026 0.756; AmCraX tornado bound 0.95",
                    g(self.psa.0),
                    g(self.psa.1)
                ),
            ),
        ];
        let mut names: Vec<String> = GSA_INPUTS.iter().map(|s| s.to_string()).collect();
        if dummy {
            dd.push((
                Dist::Uniform(self.ct.0, self.ct.1),
                format!(
                    "uniform({}, {}) tornado range (dummy: ammonia heat, no direct CO2)",
                    g(self.ct.0),
                    g(self.ct.1)
                ),
            ));
            names.push("carbon_tax_SGD_per_t".into());
        }
        let (dist, desc) = dd.into_iter().unzip();
        Ok((dist, desc, names))
    }
}

/// Python `to_x(U, D)`: clip to [1e-12, 1 - 1e-12] and apply each PPF.
pub fn to_x(u: &[Vec<f64>], dists: &[Dist]) -> Matrix {
    let hi = 1.0 - 1e-12;
    u.iter()
        .map(|row| {
            row.iter()
                .zip(dists)
                .map(|(x, d)| d.ppf(clip(*x, 1e-12, hi)))
                .collect()
        })
        .collect()
}

/// Evaluate `lcoh`, `rec` and `npv` for one row (`evaluate(S, x[0], {names[i]: x[i]})`), the
/// typed path of `evaluate` (same arithmetic).
pub fn eval_row(
    d: &EconomicsData,
    s: &Summary,
    names: &[String],
    x: &[f64],
    keep: Option<&[usize]>,
) -> Result<[f64; 3], EngineError> {
    let mut o = Overrides::new();
    for (i, (k, v)) in names.iter().zip(x).enumerate() {
        if k == "nh3_price_USD_per_t" || keep.is_some_and(|kp| !kp.contains(&i)) {
            continue;
        }
        o.insert(k.clone(), jf(*v));
    }
    let pr = prepare(d, &Scenario::Price(x[0]), &o)?;
    let r = evaluate_prepared(d, s, &pr.a, &pr.p, false)?;
    Ok([r.lcoh_usd_per_kg, r.rec_usd_per_kg, r.npv_usd])
}

/// Python `model(X, names, S)`: `(rows, 3)` outputs.
pub fn model(
    d: &EconomicsData,
    s: &Summary,
    x: &[Vec<f64>],
    names: &[String],
) -> Result<Vec<[f64; 3]>, EngineError> {
    x.iter().map(|r| eval_row(d, s, names, r, None)).collect()
}

fn col(m: &[[f64; 3]], j: usize) -> Vec<f64> {
    m.iter().map(|r| r[j]).collect()
}

fn ci_json(c: &[f64; 2]) -> Value {
    json!([jf(c[0]), jf(c[1])])
}

/// Python `analyse(S, scen, capex_shape, dummy)`.
pub fn analyse(
    st: &GsaSetup,
    s: &Summary,
    scen: &str,
    lognormal: bool,
    dummy: bool,
) -> Result<Value, EngineError> {
    let d = st.d;
    let n = st.n;
    let (dists, desc, names) = st.dists(scen, lognormal, dummy)?;
    let dim = dists.len();
    let (a, b) = sobol_base(n, dim, SEED)?;
    let mut sets: Vec<Vec<usize>> = (0..dim).map(|i| vec![i]).collect();
    for (_, members) in GSA_GROUPS {
        sets.push(
            members
                .iter()
                .map(|m| names.iter().position(|x| x == m).unwrap_or(usize::MAX))
                .collect(),
        );
    }
    let mut set_names: Vec<String> = names.clone();
    set_names.extend(GSA_GROUPS.iter().map(|g| format!("group:{}", g.0)));
    let fa = model(d, s, &to_x(&a, &dists), &names)?;
    let fb = model(d, s, &to_x(&b, &dists), &names)?;
    let mut fab = Vec::with_capacity(sets.len());
    for set in &sets {
        fab.push(model(d, s, &to_x(&ab_matrix(&a, &b, set), &dists), &names)?);
    }
    let mut outputs = Map::new();
    for (j, o) in GSA_OUTPUTS.iter().enumerate() {
        let fa_j = col(&fa, j);
        let fb_j = col(&fb, j);
        let fab_j: Vec<Vec<f64>> = fab.iter().map(|m| col(m, j)).collect();
        let (sx, stx, v) = indices_from_outputs(&fa_j, &fb_j, &fab_j);
        let ci = bootstrap_ci(&fa_j, &fb_j, &fab_j, st.n_boot, SEED, 0.95);
        let mut conv = Map::new();
        for m in [11u32, 12, 13] {
            let nn = 1usize << m;
            let pre: Vec<Vec<f64>> = fab_j.iter().map(|r| r[..nn].to_vec()).collect();
            let (s_, t_, _) = indices_from_outputs(&fa_j[..nn], &fb_j[..nn], &pre);
            let mk = |v: &[f64]| -> Value {
                Value::Object(
                    set_names[..dim]
                        .iter()
                        .zip(v)
                        .map(|(k, x)| (k.clone(), jf(*x)))
                        .collect(),
                )
            };
            conv.insert(
                format!("N={nn}"),
                json!({"S1": mk(&s_[..dim]), "ST": mk(&t_[..dim])}),
            );
        }
        let mut cat = fa_j.clone();
        cat.extend_from_slice(&fb_j);
        let mut ix = Map::new();
        for (i, nm) in set_names[..dim].iter().enumerate() {
            ix.insert(
                nm.clone(),
                json!({"S1": jf(sx[i]), "S1_ci": ci_json(&ci.s[i]), "ST": jf(stx[i]), "ST_ci": ci_json(&ci.st[i])}),
            );
        }
        let mut gr = Map::new();
        for (g, (gname, members)) in GSA_GROUPS.iter().enumerate() {
            let k = dim + g;
            gr.insert(
                format!("group:{gname}"),
                json!({"S1": jf(sx[k]), "S1_ci": ci_json(&ci.s[k]), "ST": jf(stx[k]),
                       "ST_ci": ci_json(&ci.st[k]), "members": members}),
            );
        }
        let q = stats::quantiles(&cat, &[0.05, 0.95]);
        outputs.insert(
            o.to_string(),
            json!({"V": jf(v), "mean": jf(stats::mean(&cat)), "sd": jf(stats::std(&cat, 1)),
                   "p5": jf(q[0]), "p95": jf(q[1]), "indices": ix, "groups": gr, "convergence": conv}),
        );
    }
    let mut res = json!({
        "distributions": Value::Object(names.iter().cloned().zip(desc.into_iter().map(Value::String)).collect()),
        "N": n, "seed": SEED, "d": dim, "n_evaluations": n * (dim + 2 + GSA_GROUPS.len()),
        "outputs": outputs,
    });
    if !dummy && !lognormal {
        let x = to_x(&a, &dists);
        let keep: Vec<usize> = names
            .iter()
            .enumerate()
            .filter(|(_, k)| *k != "psa_recovery" && *k != "capex_scaling_exponent")
            .map(|(i, _)| i)
            .collect();
        let mut vals = Vec::with_capacity(n);
        for r in &x {
            vals.push(eval_row(d, s, &names, r, Some(&keep))?[0]);
        }
        if let Some(m) = res.as_object_mut() {
            m.insert("lcoh_mean_mc_comparable".into(), jf(stats::mean(&vals)));
        }
    }
    Ok(res)
}

/// The study of `uq_gsa_sobol.py` (`cases` and `dummy_run_grey_HIon`). `summaries`:
/// `[("heat_integration_on", S_HI), ("heat_integration_off", S_NOHI)]`.
pub fn gsa_study(st: &GsaSetup, summaries: &[(String, Summary)]) -> Result<Value, EngineError> {
    let mut cases = Map::new();
    for (hi, s) in summaries {
        for sc in GSA_SCEN {
            cases.insert(format!("{sc}|{hi}"), analyse(st, s, sc, false, false)?);
            cases.insert(
                format!("{sc}|{hi}|capex_lognormal"),
                analyse(st, s, sc, true, false)?,
            );
        }
    }
    let s_hi = &summaries
        .first()
        .ok_or_else(|| EngineError::Domain("no summary".into()))?
        .1;
    let dummy = analyse(st, s_hi, "grey", false, true)?;
    Ok(
        json!({"source_type": "rust", "N": st.n, "n_boot": st.n_boot, "seed": SEED,
              "lognormal_sigma": jf(st.sig_ln), "triangular_5_95_width": jf(st.w_tri),
              "cases": cases, "dummy_run_grey_HIon": dummy}),
    )
}

/// The Monte Carlo of `economics_singapore.py` section 6: `(monte_carlo.json results block, grey
/// LCOH samples)`. Heat integration on, `default_rng(20261123)`, 5000 draws.
pub fn mc_singapore(
    d: &EconomicsData,
    s_hi: &Summary,
    n: usize,
) -> Result<(Value, Vec<f64>), EngineError> {
    let r = &d.reference;
    let (elo, ehi) = r.sens("electricity_USD_per_kWh")?;
    let (dlo, dhi) = r.sens("discount_rate")?;
    let (plo, phi) = r.sens("plant_life_yr")?;
    let (olo, ohi) = r.sens("operating_hours_h_per_yr")?;
    let mut rng = Pcg64::from_seed(u128::from(SEED));
    let elec: Vec<f64> = (0..n).map(|_| rng.uniform(elo, ehi)).collect();
    let cat: Vec<f64> = (0..n).map(|_| rng.triangular(16.7, 33.4, 66.8)).collect();
    let life: Vec<f64> = (0..n).map(|_| rng.uniform(1.0, 4.0)).collect();
    let capx: Vec<f64> = (0..n).map(|_| rng.triangular(0.5, 1.0, 1.5)).collect();
    let dr: Vec<f64> = (0..n).map(|_| rng.uniform(dlo, dhi)).collect();
    let oh: Vec<f64> = (0..n).map(|_| rng.uniform(olo, ohi)).collect();
    let pl: Vec<f64> = (0..n).map(|_| rng.uniform(plo, phi)).collect();
    let u_nh3: Vec<f64> = (0..n).map(|_| rng.random()).collect();
    let mut out = Map::new();
    let mut grey = Vec::new();
    for sc in GSA_SCEN {
        let v = |k: &str| {
            d.singapore
                .num(SINGAPORE_YAML, &["nh3_price_scenarios_USD_per_t", sc, k])
        };
        let (lo, md, hi) = (v("low")?, v("value")?, v("high")?);
        let fc = (md - lo) / (hi - lo);
        let mut lv = Vec::with_capacity(n);
        let mut rv = Vec::with_capacity(n);
        for i in 0..n {
            let u = u_nh3[i];
            let price = if u < fc {
                lo + (u * (hi - lo) * (md - lo)).sqrt()
            } else {
                hi - ((1.0 - u) * (hi - lo) * (hi - md)).sqrt()
            };
            let mut o = Overrides::new();
            for (k, x) in [
                ("electricity_price_USD_per_kWh", elec[i]),
                ("catalyst_price_USD_per_kg", cat[i]),
                ("catalyst_lifetime_yr", life[i]),
                ("capex_multiplier", capx[i]),
                ("discount_rate", dr[i]),
                ("operating_hours_h_per_yr", oh[i]),
                ("plant_life_yr", pl[i]),
            ] {
                o.insert(k.into(), jf(x));
            }
            let pr = prepare(d, &Scenario::Price(price), &o)?;
            let e = evaluate_prepared(d, s_hi, &pr.a, &pr.p, false)?;
            lv.push(e.lcoh_usd_per_kg);
            rv.push(e.rec_usd_per_kg);
        }
        let ql = stats::quantiles(&lv, &[0.05, 0.5, 0.95]);
        let qr = stats::quantiles(&rv, &[0.05, 0.5, 0.95]);
        out.insert(
            sc.to_string(),
            json!({"lcoh_p5": jf(ql[0]), "lcoh_p50": jf(ql[1]), "lcoh_p95": jf(ql[2]),
                   "lcoh_mean": jf(stats::mean(&lv)), "rec_p5": jf(qr[0]), "rec_p50": jf(qr[1]),
                   "rec_p95": jf(qr[2]), "n": n, "seed": SEED}),
        );
        if sc == "grey" {
            grey = lv;
        }
    }
    Ok((Value::Object(out), grey))
}
