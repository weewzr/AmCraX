//! Stage 3 tests: economics, carbon pricing and the uncertainty-quantification estimators against
//! the tables of the Python reference (`rust/golden/generate_stage3_golden.py`) and the stored
//! research results.
#![cfg(feature = "yaml")]

use amcrax_engine::economics::reference::EconomicsData;
use amcrax_engine::verify::{Golden, stage3};
use std::path::{Path, PathBuf};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn golden() -> Golden {
    Golden::open(&root().join("rust").join("golden").join("stage3")).expect("stage 3 golden tables")
}

fn check(r: amcrax_engine::verify::Report) {
    print!("{}", r.render());
    assert!(r.passed(), "{} golden comparison failed", r.target);
}

#[test]
fn carbon_golden() {
    check(
        stage3::carbon(
            &golden(),
            EconomicsData::embedded(),
            amcrax_engine::carbon::embedded_factors(),
            Path::new(&root()),
        )
        .expect("carbon check runs"),
    );
}

#[test]
fn uq_estimators_golden() {
    check(stage3::uq(&golden()).expect("uq check runs"));
}

#[test]
fn monte_carlo_study_reproduces_stored_results() {
    let d = EconomicsData::embedded();
    let base: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root().join("results/simulations/baseline.json")).unwrap(),
    )
    .unwrap();
    let s = amcrax_engine::economics::singapore::Summary::extract(&base).unwrap();
    let (mc, grey) = amcrax_engine::studies::mc_singapore(d, &s, 5000).unwrap();
    check(stage3::studies(&golden(), d, Path::new(&root()), None, Some((&mc, &grey))).unwrap());
}

#[test]
fn stiff_reactor_cases_against_lsoda() {
    let r = stage3::stiff(
        &golden(),
        amcrax_engine::kinetics::KineticsRegistry::embedded(),
        &amcrax_engine::reactor::SolverOptions::default(),
    )
    .expect("stiff check runs");
    check(r);
}

#[test]
fn kinetic_propagation_first_draws_match_stored_samples() {
    use amcrax_engine::studies::kinetic::{KP_CATS, KpSetup, kinetic_propagation};
    let reg = amcrax_engine::kinetics::KineticsRegistry::embedded();
    let ky = amcrax_engine::odata::OValue::from_yaml(
        "kinetics.yaml",
        amcrax_engine::kinetics::EMBEDDED_YAML,
    )
    .unwrap();
    let st = KpSetup::new(reg, &ky).unwrap();
    let nominal: Vec<_> = (0..KP_CATS.len())
        .map(|k| st.run_draw(k, None).unwrap())
        .collect();
    let res = kinetic_propagation(&st, 4000, Some(3), 2).unwrap();
    // the result does not depend on the thread count
    let res1 = kinetic_propagation(&st, 4000, Some(3), 1).unwrap();
    assert_eq!(res[0].1[0].2, res1[0].1[0].2);
    check(stage3::kinetic(Path::new(&root()), &res, &nominal, false).unwrap());
}

#[test]
fn economics_golden() {
    check(
        stage3::economics(&golden(), EconomicsData::embedded(), Path::new(&root()))
            .expect("economics check runs"),
    );
}
