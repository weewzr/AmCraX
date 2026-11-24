/**
 * Guided process tour (seven steps, manual stepping). Step text and value keys only: every number on a tour card is read from
 * the live case (unit facts of pfdData.unitViews or output rows of model.outputRows). A key that does not resolve shows
 * "not modelled". No timings: the tour never auto-advances unless the reader switches auto-advance on.
 */
export interface TourStep {
  id: string
  title: string
  /** unit selected (ring) while the step is shown */
  unit: string
  /** units and streams kept at full strength; the rest is dimmed */
  focus: string[]
  text: string
  /** output row keys (model.outputRows) quoted on the card, after the facts of the selected unit */
  rows: string[]
}

export const TOUR_STEPS: TourStep[] = [
  { id: 'feed', title: 'Feed and pump', unit: 'PUMP', focus: ['TANK', 'PUMP', 'FEED', 'S1'], rows: [],
    text: 'Liquid ammonia leaves storage and the pump raises it to the reactor pressure. Pumping a liquid takes little work compared with compressing a gas.' },
  { id: 'vap', title: 'Vaporiser and feed-effluent exchanger', unit: 'VAPORIZR', focus: ['VAPORIZR', 'FEHE', 'S2', 'S3', 'S5', 'S6'], rows: [],
    text: 'The vaporiser boils the ammonia. With heat integration on, the feed-effluent exchanger preheats the vapour with the hot cracked gas.' },
  { id: 'pre', title: 'Preheater', unit: 'HEATER', focus: ['HEATER', 'S3', 'S4'], rows: [],
    text: 'The preheater brings the feed to the set reactor inlet temperature.' },
  { id: 'rx', title: 'Reactor and conversion along the bed', unit: 'CRACKER', focus: ['CRACKER', 'S4', 'S5'], rows: ['eq_conversion_browser', 'eq_conversion_aspen'],
    text: 'Ammonia cracks to nitrogen and hydrogen (2 NH3 → N2 + 3 H2). The reaction takes heat. The bed colour follows the computed conversion from inlet (bottom) to outlet (top); graph 3 shows the same profile.' },
  { id: 'burn', title: 'Burner and heat balance', unit: 'BURNER', focus: ['BURNER', 'FLUEHX', 'TAILGAS', 'AIR', 'FLUE', 'STACK'], rows: [],
    text: 'The burner fires the tail gas with air. Any shortfall in heat is met by extra fuel (ammonia self-firing by default). Graph 7 shows the energy balance.' },
  { id: 'pur', title: 'Cooler and hydrogen purification', unit: 'PSA', focus: ['COOLER', 'PSA', 'S6', 'S7', 'H2PROD', 'TAILGAS'], rows: ['lhv_efficiency'],
    text: 'The cracked gas is cooled and purified. The PSA here is a reduced-order splitter: hydrogen recovery and nitrogen slip are assumed inputs, not an adsorption model.' },
  { id: 'cost', title: 'Cost and carbon', unit: 'CRACKER', focus: [], rows: ['lcoh_SGD', 'lcoh_USD', 'carbon_intensity', 'carbon_cost'],
    text: 'The hydrogen cost and the carbon intensity follow from the same steady-state solution. Graphs 6 and 8 show how they change with the inputs and the ammonia route.' },
]
