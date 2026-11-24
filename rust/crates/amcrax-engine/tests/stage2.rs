//! Stage 2 tests: rate laws, viscosity, plug-flow reactor and searches against the tables of the
//! Python reference (`rust/golden/generate_stage2_golden.py`), plus mass and energy balances and
//! input validation of the reactor.
#![cfg(feature = "yaml")]

use amcrax_engine::EngineError;
use amcrax_engine::kinetics::KineticsRegistry;
use amcrax_engine::reactor::{PfrInput, SolverOptions, simulate_pfr};
use amcrax_engine::thermo::reaction_enthalpy_kj_mol;
use amcrax_engine::verify::{Golden, stage2};
use std::path::PathBuf;

fn golden() -> Golden {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../golden/stage2");
    Golden::open(&p).expect("stage 2 golden tables")
}

#[test]
fn kinetics_and_viscosity_golden() {
    let r = stage2::kinetics(&golden(), KineticsRegistry::embedded()).expect("kinetics check runs");
    print!("{}", r.render());
    assert!(r.passed(), "kinetics golden comparison failed");
}

#[test]
fn reactor_and_searches_golden() {
    let r = stage2::reactor(
        &golden(),
        KineticsRegistry::embedded(),
        &SolverOptions::default(),
    )
    .expect("reactor check runs");
    print!("{}", r.render());
    assert!(r.passed(), "reactor golden comparison failed");
}

fn element_flows(f: &std::collections::BTreeMap<String, f64>) -> (f64, f64) {
    let g = |k: &str| f.get(k).copied().unwrap_or(0.0);
    let n = g("NH3") + 2.0 * g("N2");
    let h = 3.0 * g("NH3") + 2.0 * g("H2") + 2.0 * g("H2O");
    (n, h)
}

#[test]
fn element_balances_close() {
    let reg = KineticsRegistry::embedded();
    let s = SolverOptions::default();
    for cid in [
        "ni_takahashi_microkinetic",
        "ru_kum_temkin_pyzhev",
        "nire_ceo2_5ni1ru_lucentini_lhhw",
    ] {
        let mut inp = PfrInput::new(cid, 50.0);
        inp.n_tubes = 40;
        inp.feed_kmol_h = Some(
            [("NH3", 70.0), ("H2", 5.0), ("N2", 5.0), ("H2O", 1.0)]
                .into_iter()
                .map(|(k, v)| (k.to_string(), v))
                .collect(),
        );
        let r = simulate_pfr(reg, &inp, &s).unwrap();
        let fin = inp.feed_kmol_h.clone().unwrap();
        let (n_in, h_in) = element_flows(&fin);
        let (n_out, h_out) = element_flows(&r.outlet.flows_kmol_h);
        assert!(
            ((n_out - n_in) / n_in).abs() < 1e-12,
            "{cid}: N {n_in} -> {n_out}"
        );
        assert!(
            ((h_out - h_in) / h_in).abs() < 1e-12,
            "{cid}: H {h_in} -> {h_out}"
        );
    }
}

#[test]
fn adiabatic_energy_balance_closes() {
    let reg = KineticsRegistry::embedded();
    let s = SolverOptions::default();
    let mut inp = PfrInput::new("ru_takahashi_microkinetic", 100.0);
    inp.mode = "adiabatic".into();
    inp.n_tubes = 50;
    inp.t_in_c = 650.0;
    let r = simulate_pfr(reg, &inp, &s).unwrap();
    // heat input = H_out - H_in must vanish for an adiabatic bed (up to the integration error)
    let f0_kmol_h = 99.8;
    let scale = f0_kmol_h * r.outlet.conversion * reaction_enthalpy_kj_mol(923.15).unwrap() / 3.6;
    assert!(
        (r.outlet.heat_input_kw / scale).abs() < 1e-7,
        "adiabatic closure {} kW of {} kW reaction heat",
        r.outlet.heat_input_kw,
        scale
    );
    assert!(r.outlet.t_c < 650.0);
}

#[test]
fn invalid_inputs_return_typed_errors() {
    let reg = KineticsRegistry::embedded();
    let s = SolverOptions::default();
    let cases: Vec<Box<dyn Fn(&mut PfrInput)>> = vec![
        Box::new(|i| i.p_in_bar = -1.0),
        Box::new(|i| i.p_in_bar = f64::NAN),
        Box::new(|i| {
            i.t_in_c = 6000.0;
            i.pressure_drop = false;
        }),
        Box::new(|i| i.w_kg = 0.0),
        Box::new(|i| i.mode = "fired".into()),
        Box::new(|i| i.mode = "external".into()),
        Box::new(|i| i.eps_b = 1.0),
        Box::new(|i| i.n_points = 1),
        Box::new(|i| {
            i.feed_kmol_h = Some([("O2".to_string(), 1.0)].into_iter().collect());
        }),
        Box::new(|i| {
            i.feed_kmol_h = Some([("NH3".to_string(), -1.0)].into_iter().collect());
        }),
        Box::new(|i| i.keq_basis = "other".into()),
    ];
    for (k, f) in cases.iter().enumerate() {
        let mut inp = PfrInput::new("ru_takahashi_microkinetic", 10.0);
        f(&mut inp);
        match simulate_pfr(reg, &inp, &s) {
            Err(EngineError::Domain(_)) => {}
            other => panic!("case {k}: expected a domain error, got {other:?}"),
        }
    }
}

#[test]
fn eval_json_roundtrip() {
    let reg = KineticsRegistry::embedded();
    let case: PfrInput = serde_json::from_str(
        r#"{"catalyst_id": "ru_kum_temkin_pyzhev", "W_kg": 20.0, "T_in_C": 500.0,
            "P_in_bar": 1.01325, "pressure_drop": false, "n_points": 11}"#,
    )
    .unwrap();
    let r = simulate_pfr(reg, &case, &SolverOptions::default()).unwrap();
    // stored browser test vector pfr_kum_isothermal_T500_P1.01325_W20
    assert!((r.outlet.conversion - 0.815687).abs() < 1e-6);
    let text = serde_json::to_string(&r).unwrap();
    assert!(text.contains("\"W_reached_kg\""));
    assert!(
        serde_json::from_str::<PfrInput>(r#"{"catalyst_id": "x", "W_kg": 1, "rtol": 1e-8}"#)
            .is_err()
    );
}
