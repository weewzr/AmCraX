//! End-use pathways (Python `enduse/pathways.py`, `enduse/params.py`). Stage 5.

use crate::lca;

/// `lca.FACTORS["grid_ef_singapore_2024"]["value"]`, kg CO2/kWh (EMA 2024 average grid factor).
pub const GRID_EF_SINGAPORE_2024: f64 = 0.402;

/// Python `Activity` (per functional unit; `nh3_kg` includes NH3 burnt for heat).
#[derive(Debug, Clone, PartialEq)]
pub struct Activity {
    pub id: String,
    pub label: String,
    pub product: String,
    pub functional_unit: String,
    pub nh3_kg: f64,
    pub aux_kwh: f64,
    pub efficiency: f64,
    pub n2o_kgco2e: f64,
    pub no_kg: Option<f64>,
    pub cracker_h2_kg_h: f64,
    pub capex_kind: String,
    pub h2_fraction_vol: Option<f64>,
    pub cracked_share: Option<f64>,
    pub purity_note: String,
    pub heat_mode: String,
    pub cracker_nh3_kg_h: f64,
}

impl Activity {
    /// `Activity(id, label, product, functional_unit, nh3_kg, aux_kWh, efficiency)` with the
    /// dataclass defaults for the other fields.
    pub fn new(
        id: &str,
        label: &str,
        product: &str,
        fu: &str,
        nh3_kg: f64,
        aux_kwh: f64,
        efficiency: f64,
    ) -> Activity {
        Activity {
            id: id.into(),
            label: label.into(),
            product: product.into(),
            functional_unit: fu.into(),
            nh3_kg,
            aux_kwh,
            efficiency,
            n2o_kgco2e: 0.0,
            no_kg: None,
            cracker_h2_kg_h: 0.0,
            capex_kind: "none".into(),
            h2_fraction_vol: None,
            cracked_share: None,
            purity_note: String::new(),
            heat_mode: String::new(),
            cracker_nh3_kg_h: 0.0,
        }
    }
}

/// `carbon_intensity(a, route_ef, distance_km, grid, boil_off, ship_ef)`: kg CO2e per
/// functional unit as (upstream_ammonia, shipping, electricity, direct_n2o, total).
pub fn carbon_intensity(
    a: &Activity,
    route_ef: f64,
    distance_km: f64,
    grid: Option<f64>,
    boil_off: Option<f64>,
    ship_ef: Option<f64>,
) -> [f64; 5] {
    let g = grid.unwrap_or(GRID_EF_SINGAPORE_2024);
    let ship = lca::ship_kg_per_kg_nh3(distance_km, ship_ef);
    let bo = boil_off.unwrap_or(lca::BOIL_OFF_FRACTION);
    let up = a.nh3_kg * route_ef / (1.0 - bo);
    let tr = a.nh3_kg * ship / (1.0 - bo);
    let el = a.aux_kwh * g;
    let tot = up + tr + el + a.n2o_kgco2e;
    [up, tr, el, a.n2o_kgco2e, tot]
}
