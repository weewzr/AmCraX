// Browser verification of the static site, as served by scripts/serve_pages.mjs under /AmCraX/ (Edge via playwright-core).
//
//   node scripts/serve_pages.mjs --port 4180        (in another shell, after `npm run build:pages`)
//   node scripts/site_check.mjs [--base http://127.0.0.1:4180/AmCraX/] [--shots <dir>] [--viewports 390x844,820x1180,1440x900,1920x1080]
//                               [--routes why,results,platform/pfd] [--no-shots] [--fullpage]
//
// For every viewport and every route it checks: renders (one h1 / platform title), no console errors, no failed or 4xx/5xx requests,
// no request outside the base path (so no API call and no absolute "/..." URL), no horizontal overflow. Plus interaction checks
// (mobile menu, nav reaches ten sections, PFD equipment + stream panels on site and platform, calculator, anchors, downloads).
// Screenshots: full-page site routes at the desktop viewport go to <shots>/site_<page>_desktop.png (default docs/screenshots); every other
// viewport and the platform / calculator captures go to <shots>/qa/ (git-ignored QA captures). Exit code 1 when a check fails.
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']] : a), []))
const base = (args.base ?? 'http://127.0.0.1:4180/AmCraX/').replace(/\/?$/, '/')
const origin = new URL(base).origin
const prefix = new URL(base).pathname
const shots = path.resolve(args.shots ?? path.join(here, '..', '..', 'docs', 'screenshots'))
const VIEWPORTS = (args.viewports ?? '390x844,820x1180,1440x900,1920x1080').split(',').map((s) => { const [w, h] = s.split('x').map(Number); return { w, h, label: w === 390 ? 'phone' : w === 820 ? 'tablet' : w === 1440 ? 'desktop' : w === 1920 ? 'fullhd' : `${w}x${h}` } })
const HYP = ['hypotheses', 'hypotheses/catalyst', 'hypotheses/economics', 'hypotheses/purification', 'hypotheses/end-use', 'hypotheses/validation', 'hypotheses/aspen-evidence']
const SITE = ['', 'overview', 'why', 'pfd', 'methodology', 'results', 'architecture', 'research', 'docs', 'about', ...HYP]
const PLATFORM = ['platform', 'platform/pfd', 'platform/simulation', 'platform/reactor', 'platform/heat', 'platform/sensitivity', 'platform/optimisation', 'platform/economics', 'platform/environment', 'platform/validation', 'platform/reports']
const only = args.routes ? new Set(args.routes.split(',')) : null
const ROUTES = [...SITE, ...PLATFORM].filter((r) => !only || only.has(r === '' ? 'home' : r))
const name = (r) => (r === '' ? 'home' : r === 'hypotheses' ? 'research_matrix' : r.startsWith('hypotheses/') ? `research_${r.slice(11).replace(/-/g, '_')}` : r.replace('platform/', 'platform_').replace(/\//g, '_'))
const qaDir = path.join(shots, 'qa')
if (args['no-shots'] !== 'true') { mkdirSync(shots, { recursive: true }); mkdirSync(qaDir, { recursive: true }) }
/** Published set: desktop captures of the site routes only; everything else is a QA capture. */
const shotPath = (route, label, isPlat, kind = 'page') => path.join((label === 'desktop' && !isPlat && kind === 'page') || (kind.startsWith('simulator') && (label === 'desktop' || label === 'phone')) ? shots : qaDir, `site_${kind === 'page' ? name(route) : kind}_${label}.png`)

const results = []
const record = (vp, id, ok, detail = '') => { results.push({ vp, id, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} [${vp}] ${id}${detail ? ' - ' + detail : ''}`) }
const external = /^https:\/\/(fonts\.googleapis\.com|fonts\.gstatic\.com)\//

const LEGACY = ['overview', 'results', 'methodology', 'research']
/** Same text as the site's fmt(): en-US grouping, fixed digits. */
const loc = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : 'n/a')
const snapCache = new Map()
/** A snapshot JSON file as served (null when missing); used so that expected numbers are read, never typed here. */
async function snap(rel) {
  if (!snapCache.has(rel)) snapCache.set(rel, fetch(`${base}snapshot/${rel}`).then((r) => (r.ok ? r.json() : null)).catch(() => null))
  return snapCache.get(rel)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const notes404 = new Set()

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, hasTouch: vp.w < 900 })
  const page = await ctx.newPage()
  let cur = 'boot'
  const problems = []
  const pushP = (m) => problems.push(`[${cur}] ${m}`)
  page.on('pageerror', (e) => pushP(`pageerror: ${e.message}`))
  page.on('console', (m) => { if (m.type() === 'error') pushP(`console.error: ${m.text().slice(0, 200)}`) })
  page.on('requestfailed', (r) => { if (!external.test(r.url())) pushP(`request failed: ${r.url()} (${r.failure()?.errorText})`) })
  page.on('response', (r) => {
    const u = r.url()
    if (external.test(u)) return
    if (r.status() >= 400) { pushP(`HTTP ${r.status()} ${u}`); notes404.add(`${r.status()} ${u}`) }
  })
  page.on('request', (r) => {
    const u = new URL(r.url())
    if (external.test(r.url()) || u.protocol === 'data:' || u.protocol === 'blob:') return
    if (u.origin !== origin || !u.pathname.startsWith(prefix)) pushP(`request outside ${prefix}: ${r.url()}`)
    if (u.pathname.startsWith(`${prefix}api/`)) pushP(`API request: ${r.url()}`)
  })

  async function settle(route) {
    await page.waitForFunction(() => {
      const t = document.body.innerText
      return !/Resolving data mode|Loading [^\n]{3,90} \.\.\.|Loading (the )?(platform|diagram|flowsheet|data|Aspen|Python|stored|Separation|Validation|Reference|Equilibrium|Plug|Techno|Optimisation|LCOH|Carbon|Single|Deliverables|Figures|Model|case)/i.test(t) && document.querySelector('.site, .shell')
    }, null, { timeout: 60000 }).catch(() => pushP('settle timeout (loading text still present)'))
    if (route === 'pfd' || route === 'platform/pfd') await page.waitForSelector('.react-flow__node', { timeout: 20000 }).catch(() => pushP('no PFD nodes'))
    if (route === '') {
      await page.waitForSelector('.sim-pfd', { timeout: 30000 }).catch(() => pushP('no simulator diagram'))
      // the eight graphs are a lazy chunk with debounced sweeps: wait until every card has data marks
      await page.waitForFunction(() => {
        const cards = [...document.querySelectorAll('.sim-graphs .sim-chart')]
        return cards.length === 8 && cards.every((c) => c.querySelector('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg path.recharts-curve, svg .recharts-rectangle'))
      }, null, { timeout: 30000 }).catch(() => pushP('simulator graphs did not finish'))
    }
    await page.waitForTimeout(route === 'results' ? 2500 : 1200)
  }
  async function go(route) {
    cur = route === '' ? 'home' : route
    await page.evaluate((r) => { window.location.hash = `#/${r}` }, route)
    await settle(route)
  }
  const tid = (t) => page.locator(`[data-testid="${t}"]`).first().innerText().catch(() => '')

  /** Phase 2 content of the research pages: key numbers read from the snapshot must appear, the controls must work. */
  async function phase2Checks(route, id, body) {
    record(vp.label, `${id}: no single "validated" percentage, no "experimentally validated"`, !/\d+(\.\d+)?\s?% validated|experimentally validated/i.test(body))
    // plain answers (reading aid): above the formal-verdict material, every claim and answer from the matrix file, the
    // formal verdict printed in the same block before the first answer
    const PLAIN_FOR = { hypotheses: ['H1', 'H2', 'H3', 'H4'], 'hypotheses/catalyst': ['H3'], 'hypotheses/economics': ['H2'], 'hypotheses/purification': ['H4'], 'hypotheses/end-use': ['H1'] }
    if (PLAIN_FOR[route]) {
      const emp = await snap('research/evidence_matrix.json')
      const want = (emp?.hypotheses ?? []).filter((h) => PLAIN_FOR[route].includes(h.id))
      const res = await Promise.all(want.map(async (h) => {
        const t = await tid(`plain-answers-${h.id}`)
        const order = await page.evaluate((hid) => {
          const b = document.querySelector(`[data-testid="plain-answers-${hid}"]`)
          const v = b?.querySelector('.verdict-chip'), a = b?.querySelector('.answer-chip')
          return !!(v && a && (v.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING))
        }, h.id)
        const okClaims = (h.plain_answers ?? []).every((a) => t.includes(a.claim) && t.includes(a.answer))
        return okClaims && order && t.toUpperCase().includes(String(h.verdict).toUpperCase()) && (h.components ?? []).every((c) => t.includes(c.id))
      }))
      const answers = await page.$$eval('[data-testid="plain-answers"] .answer-chip[data-answer]', (cs) => cs.map((c) => c.getAttribute('data-answer')))
      record(vp.label, `${id}: plain answers from the matrix, formal verdict and components printed before them`, want.length === PLAIN_FOR[route].length && res.every(Boolean) && answers.length > 0 && answers.every((a) => ['Yes', 'No', 'Not established'].includes(a)), want.map((h, i) => `${h.id} ${res[i] ? 'ok' : 'MISMATCH'}`).join(', '))
      const above = await page.evaluate(() => {
        const p = document.querySelector('#plain-answers'); if (!p) return false
        const after = [...document.querySelectorAll('main section[id]')].filter((s) => s.id !== 'plain-answers')
        return after.length > 0 && after.every((s) => s.getBoundingClientRect().top >= p.getBoundingClientRect().bottom - 1)
      })
      record(vp.label, `${id}: plain answers placed above the formal-verdict material`, above && /reading aid/.test(await tid('plain-answers-lead')))
    }
    if (route === 'hypotheses') {
      const chips = await page.$$eval('.verdict-chip', (cs) => cs.map((c) => c.getAttribute('data-verdict') ?? ''))
      const words = /^(SUPPORTED|CONTRADICTED|MIXED|PARTIALLY SUPPORTED|INCONCLUSIVE)\b/
      const em = await snap('research/evidence_matrix.json')
      const want = (em?.hypotheses ?? []).map((h) => String(h.verdict ?? '').toUpperCase().replace(/_/g, ' '))
      const tiles = await Promise.all(['H1', 'H2', 'H3', 'H4'].map((h) => tid(`verdict-${h}`)))
      record(vp.label, `${id}: verdict chips render (v2 vocabulary) and match the matrix file`, chips.length >= 4 && chips.every((c) => words.test(c)) && want.every((w, i) => tiles[i]?.toUpperCase().includes(w)), `${chips.length} chips; ${want.join(', ')}`)
      record(vp.label, `${id}: methodology document linked`, /verdict_methodology_v2\.md/.test(await tid('matrix-version')))
      // Phase 2 fix pass: component chips beside every hypothesis verdict, the matrix's own qualifier for PARTIALLY SUPPORTED,
      // v1 verdicts, the provenance disclosures near the top, and the thresholds of the rows that moved (all read from the matrix file)
      const hs = em?.hypotheses ?? []
      const compOk = await Promise.all(hs.map(async (h) => {
        const t = await tid(`components-${h.id}`)
        return (h.components ?? []).every((c) => t.includes(c.id) && t.toUpperCase().includes(String(c.verdict).toUpperCase()))
      }))
      record(vp.label, `${id}: component verdict chips beside each hypothesis verdict match the matrix file`, hs.length > 0 && compOk.every(Boolean), hs.map((h, i) => `${h.id} ${compOk[i] ? 'ok' : 'MISMATCH'}`).join(', '))
      const part = hs.filter((h) => String(h.verdict).toUpperCase() === 'PARTIALLY SUPPORTED')
      const qs = await Promise.all(part.map((h) => tid(`qualifier-${h.id}`)))
      record(vp.label, `${id}: PARTIALLY SUPPORTED hypotheses carry the matrix's qualifier text`, qs.every((q, i) => q.length > 20 && String(part[i].summary ?? '').startsWith(q.replace(/^Qualifier \(from the matrix\)\.\s*/, '').slice(0, 40))), qs.map((q) => q.slice(0, 90)).join(' | '))
      const v1ok = hs.every((h, i) => !h.verdict_v1 || tiles[i]?.includes(`Version 1 verdict: ${h.verdict_v1}`))
      record(vp.label, `${id}: version 1 verdicts shown beside the v2 verdicts`, v1ok)
      const disc = await tid('matrix-disclosures')
      const dl = em?.provenance?.disclosures ?? []
      const pos = await page.evaluate(() => { const d = document.querySelector('[data-testid="matrix-disclosures"]'); const t = document.querySelector('[data-testid="verdict-H1"]'); return d && t ? d.getBoundingClientRect().top < t.getBoundingClientRect().top : false })
      record(vp.label, `${id}: matrix provenance disclosures rendered above the verdict tiles`, dl.length > 0 && dl.every((x) => disc.includes(x.slice(0, 80))) && pos && /three rows/i.test(disc), `${dl.length} disclosures, above tiles: ${pos}`)
      const moved = hs.flatMap((h) => (h.rows ?? []).filter((r) => r.verdict_v1 && r.verdict_v1 !== r.verdict))
      const mt = await Promise.all(moved.map((r) => tid(`threshold-${r.row_id}`)))
      record(vp.label, `${id}: rows that moved show their threshold as the finding`, moved.length > 0 && mt.every((t, i) => t.includes(moved[i].row_id) && /Threshold:/.test(t) && t.includes(String(moved[i].verdict))), moved.map((r) => r.row_id).join(', '))
      record(vp.label, `${id}: no claim that the whole methodology was fixed before the analysis`, !/fixed before the Phase 2 analysis/i.test(body))
    }
    if (route === 'hypotheses/economics') {
      const bl = await snap('research/reference_scenario/baseline.json.json')
      const k = await tid('baseline-kpis')
      record(vp.label, `${id}: unified baseline numbers from the snapshot (USD and SGD)`, !!bl && k.includes(loc(bl.lcoh_USD_per_kg, 3)) && k.includes(loc(bl.lcoh_SGD_per_kg, 3)) && k.includes(String(bl.fx_date)), k.replace(/\n/g, ' ').slice(0, 200))
      record(vp.label, `${id}: superseded baselines noted`, /superseded|history/i.test(await tid('superseded-note')))
      const fe = await tid('fuel-envelope')
      const fcs = bl?.fuel_efficiency_sensitivity?.cases ?? []
      record(vp.label, `${id}: fuel-efficiency envelope table from the snapshot (reference labelled optimistic)`, fcs.length >= 3 && fcs.every((c) => fe.includes(loc(c.lcoh_USD_per_kg, 3))) && /optimistic/i.test(fe), fcs.map((c) => `${c.fuel_efficiency}:${loc(c.lcoh_USD_per_kg, 3)}`).join(' '))
      const ci = await snap('research/carbon_pricing/carbon_intensity.json.json')
      const gn = await tid('green-ci-note')
      record(vp.label, `${id}: both green-ammonia carbon intensities labelled with their boundary`, !!ci && gn.includes(loc(ci.routes?.green?.ci_kgCO2e_per_kgH2?.central, 2)) && gn.includes(loc(ci.routes?.green_lee?.ci_kgCO2e_per_kgH2?.central, 2)) && /embedded/.test(gn) && /renewable electricity as zero/.test(gn), gn.slice(0, 120))
      const fd = await snap('research/carbon_pricing/feed_dominance.json.json')
      record(vp.label, `${id}: adverse H2 finding with the break-even price`, !!fd && (await tid('adverse-h2')).includes(loc(fd.breakeven_nh3_USD_per_t?.ne_asia_smr_production_cost, 0)))
      // carbon control: Mode A default, Mode B hypothetical with a user price, values = interpolation of the stored sweep
      const ctl = page.locator('[data-testid="carbon-control"]')
      record(vp.label, `${id}: carbon control defaults to Mode A (actual Singapore boundary)`, (await ctl.getAttribute('data-mode')) === 'actual_sg' && /not law/.test(await tid('mode-a-text')))
      const a45 = await tid('lcoh-green_current')
      await page.locator('[data-testid="mode-b"]').click(); await page.waitForTimeout(250)
      const bText = await tid('mode-b-text')
      record(vp.label, `${id}: Mode B is labelled hypothetical, not Singapore law, and as interpolation of stored Python results`, (await ctl.getAttribute('data-mode')) === 'hypothetical_lca' && /not Singapore law/i.test(bText) && /interpolation of stored Python results/i.test(bText), bText.slice(0, 160))
      const num = page.locator('input[aria-label="Hypothetical carbon price in SGD per tonne CO2e"]')
      await num.fill('303'); await page.waitForTimeout(250)
      const sweep = await snap('research/carbon_pricing/price_sweep.csv.json')
      const rows = sweep?.rows ?? []
      const r300 = rows.find((r) => r.price_SGD_per_tCO2e === 300), r305 = rows.find((r) => r.price_SGD_per_tCO2e === 305)
      const yk = 'lcoh_green_current_central_USD_per_kg'
      const exp = r300 && r305 ? r300[yk] + ((r305[yk] - r300[yk]) * 3) / 5 : null
      const b303 = await tid('lcoh-green_current')
      record(vp.label, `${id}: Mode B at 303 SGD/tCO2e shows the green LCOH interpolated between the stored 300 and 305 points`, exp !== null && b303 === loc(exp, 3) && b303 !== a45, `${a45} -> ${b303}, expected ${exp === null ? 'n/a' : loc(exp, 3)}`)
      const ss = await snap('research/carbon_pricing/site_summary.json.json')
      record(vp.label, `${id}: crossover threshold blue over grey shown`, !!ss && (await tid('th-blue_over_grey')) === loc(ss.thresholds_SGD_per_tCO2e?.blue_over_grey?.central, 1))
      await page.locator('[data-testid="mode-a"]').click(); await page.waitForTimeout(250)
      record(vp.label, `${id}: switching back to Mode A restores the actual-boundary LCOH`, (await tid('lcoh-green_current')) === a45)
    }
    if (route === 'hypotheses/catalyst') {
      record(vp.label, `${id}: kinetic validity statement and derived-price label`, /20 bar/.test(await tid('validity-statement')) && /no supplier quotation exists/i.test(body) && /unmodelled, no performance figures/i.test(body))
      record(vp.label, `${id}: equal-conversion correction shown`, (await tid('equal-conversion')).length > 40)
    }
    if (route === 'hypotheses/purification') {
      const nus = await tid('nus-wording')
      record(vp.label, `${id}: NUS wording and parity threshold`, /none of their verified publications covers cracked-ammonia purification/i.test(nus) && /no specific result is attributed to them/i.test(nus) && (await tid('h4-parity')).length > 40)
    }
    if (route === 'hypotheses/end-use') {
      const w = await tid('h1-wording')
      const tc = await snap('research/enduse/turbine_threshold.csv.json')
      const ref = (tc?.rows ?? []).find((r) => r.pathway === 'full_purified' && r.basis === 'reference')
      record(vp.label, `${id}: required H1 wording with the equal-efficiency assumption`, /direct ammonia combustion produces electricity at a lower cost/.test(w) && /49\.64 %/.test(w) && /fuel-specific turbine performance/.test(w), w.slice(0, 120))
      record(vp.label, `${id}: turbine threshold from the snapshot and the exhaust-heated finding`, !!ref && (await tid('thr-full_purified')) === loc(ref.threshold_delta_pp, 2) && /cheaper than direct ammonia/.test(await tid('exhaust-finding')))
      record(vp.label, `${id}: Environmental Analysis reachable (carbon intensity by route)`, (await page.locator('#carbon-intensity table').count()) > 0 && (await page.locator('#lca').count()) > 0)
      const tt = await snap('research/enduse/turbine_threshold.json.json')
      const fs = tt?.cracker_heat_fuel_efficiency_sensitivity?.cases ?? []
      const he = await tid('h1-fuel-envelope')
      record(vp.label, `${id}: H1 thresholds with their fuel-efficiency sensitivity from the snapshot`, fs.length >= 3 && fs.every((c) => he.includes(loc(c.full_fired?.threshold_delta_fuel_pp_vs_direct_turbine, 2)) && he.includes(loc(c.full_purified?.threshold_delta_fuel_pp_vs_direct_turbine, 2))), fs.map((c) => loc(c.full_fired?.threshold_delta_fuel_pp_vs_direct_turbine, 2)).join(' / '))
      const ci = await snap('research/carbon_pricing/carbon_intensity.json.json')
      const gn = await tid('green-ci-note')
      record(vp.label, `${id}: both green-ammonia carbon intensities labelled with their boundary`, !!ci && gn.includes(loc(ci.routes?.green?.ci_kgCO2e_per_kgH2?.central, 2)) && gn.includes(loc(ci.routes?.green_lee?.ci_kgCO2e_per_kgH2?.central, 2)), gn.slice(0, 120))
    }
    if (route === 'hypotheses/validation') {
      const kinds = await Promise.all(['numerical_verification', 'python_vs_aspen', 'literature_comparison', 'experimental_validation'].map((k) => tid(`kind-${k}`)))
      const bk = await snap('research/validation/by_kind.json')
      record(vp.label, `${id}: four evidence-kind blocks with counts from the snapshot`, kinds.every((t) => t.length > 0) && !!bk && ['numerical_verification', 'python_vs_aspen', 'literature_comparison', 'experimental_validation'].every((k, i) => kinds[i].includes(`${bk.kinds[k]?.total ?? 0}`)), kinds.map((t) => t.split('\n')[1] ?? '').join(' | '))
      record(vp.label, `${id}: no independent experimental validation stated`, /no independent experimental validation/i.test(await tid('no-experimental')))
    }
  }

  // ---- boot ----
  await page.goto(base, { waitUntil: 'domcontentloaded' })
  await settle('')

  for (const route of ROUTES) {
    const id = route === '' ? 'home' : route
    if (route !== '') await go(route); else { cur = 'home'; await page.evaluate(() => { window.location.hash = '#/' }); await settle('') }
    const before = problems.length
    const info = await page.evaluate((isPlatform) => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      h1: document.querySelectorAll('h1').length,
      main: !!document.querySelector('main'),
      bodyText: document.body.innerText,
      charts: document.querySelectorAll('.chart-card').length,
      emptyCharts: [...document.querySelectorAll('.chart-box')].filter((b) => !b.querySelector('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg .recharts-scatter, svg path.recharts-curve, svg .recharts-rectangle')).length,
      badge: isPlatform ? document.querySelector('.topbar-right .pill')?.textContent?.trim() : null,
      banner: isPlatform ? document.querySelector('.snapshot-banner')?.textContent?.trim().slice(0, 80) : null,
      noteBar: document.querySelector('.static-notice')?.textContent?.trim() ?? null,
    }), route.startsWith('platform'))
    const isPlat = route.startsWith('platform')
    record(vp.label, `${id}: no horizontal overflow`, info.overflow <= 1, `overflow ${info.overflow}px`)
    record(vp.label, `${id}: renders (main landmark, ${isPlat ? 'h1 present' : 'exactly one h1'})`, info.main && (isPlat ? info.h1 >= 1 : info.h1 === 1), `h1=${info.h1}`)
    if (isPlat) record(vp.label, `${id}: SNAPSHOT mode badge + static-site banner`, /PUBLISHED RESULTS/.test(info.badge ?? '') && /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.banner ?? '') || /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.bodyText), `${info.badge} | ${info.banner}`)
    else record(vp.label, `${id}: header notice says static site`, /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.noteBar ?? ''), info.noteBar ?? '')
    record(vp.label, `${id}: no "undefined"/"NaN"/"[object" text`, !/\bundefined\b|\bNaN\b|\[object /.test(info.bodyText))
    if (route === 'results') record(vp.label, `${id}: charts drawn (${info.charts} cards, ${info.emptyCharts} without data marks)`, info.charts >= 9 && info.emptyCharts === 0)
    if (route.startsWith('hypotheses')) {
      const hy = await page.evaluate(() => ({
        badges: document.querySelectorAll('.badge').length,
        stored: /does not run Aspen Plus/.test(document.body.innerText),
        tables: document.querySelectorAll('table.data').length,
        brokenImgs: [...document.querySelectorAll('img')].filter((i) => i.complete && i.naturalWidth === 0).length,
        notAvail: /Data not available yet|Could not load|Not in the SNAPSHOT/.test(document.body.innerText),
        subnav: document.querySelectorAll('.chip-nav a').length,
      }))
      record(vp.label, `${id}: stored-results statement, sub-navigation, source badges`, hy.stored && hy.subnav === 7 && (route === 'hypotheses' || route === 'hypotheses/validation' || hy.badges >= 4), JSON.stringify(hy))
      record(vp.label, `${id}: no missing-data notice and no broken images`, !hy.notAvail && hy.brokenImgs === 0, JSON.stringify(hy))
      if (['hypotheses/catalyst', 'hypotheses/economics', 'hypotheses/purification', 'hypotheses/end-use'].includes(route)) record(vp.label, `${id}: charts drawn (${info.charts} cards, ${info.emptyCharts} without data marks)`, info.charts >= 4 && info.emptyCharts === 0)
      await phase2Checks(route, id, info.bodyText)
    }
    if (LEGACY.includes(route)) {
      const bl = await snap('research/reference_scenario/baseline.json.json')
      const t = await page.locator('[data-testid="legacy-banner"]').innerText().catch(() => '')
      record(vp.label, `${id}: legacy banner names the unified baseline`, /legacy core result, superseded for research outputs by the unified baseline/i.test(t) && (!bl || t.includes(loc(bl.lcoh_USD_per_kg, 3))), t.slice(0, 160))
      const fc = bl?.fuel_efficiency_sensitivity?.cases ?? []
      record(vp.label, `${id}: legacy banner gives the fuel-efficiency envelope of the baseline`, fc.length >= 3 && /optimistic/.test(t) && fc.slice(1).every((c) => t.includes(loc(c.lcoh_USD_per_kg, 3))), t.slice(160, 360))
    }
    record(vp.label, `${id}: no console errors / failed or 4xx requests / requests outside base`, problems.length === before, problems.slice(before).join(' | ').slice(0, 400))
    if (args['no-shots'] !== 'true') {
      if (args.fullpage !== 'false' && !isPlat) await page.evaluate(async () => { const h = document.documentElement.scrollHeight; for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)) } })  // trigger lazy images
      await page.waitForTimeout(400)
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.screenshot({ path: shotPath(route, vp.label, isPlat), fullPage: args.fullpage !== 'false' && !isPlat })
    }
  }

  // ---- simulator (landing page) ----
  if (!only || only.has('home')) {
    cur = 'simulator'
    await go('')
    const kpi = (k) => page.locator(`[data-kpi="${k}"] .sim-kpi-v`).innerText()
    const outv = (k) => page.locator(`[data-out="${k}"]`).first().innerText()
    const sim = await page.evaluate(() => {
      const r = (s) => document.querySelector(s)?.getBoundingClientRect() ?? null
      return { h1: document.querySelector('h1')?.textContent ?? '', pfd: r('.sim-pfd'), controls: r('.sim-col-controls'), out: r('.sim-kpis'), grid: r('.sim-grid'),
        graphs: r('.sim-graphs'), units: document.querySelectorAll('.sim-pfd [data-unit]').length, streams: document.querySelectorAll('.sim-pfd [data-stream]').length,
        badges: document.querySelectorAll('.sim-col-out .sim-badge').length, overflowPfd: (() => { const b = document.querySelector('.sim-pfd-box'); return b ? b.scrollWidth - b.clientWidth : -1 })() }
    })
    record(vp.label, 'simulator: the site root shows the simulator (h1, diagram, units, streams, labelled outputs)', /process simulator/i.test(sim.h1) && !!sim.pfd && sim.units >= 10 && sim.streams >= 12 && sim.badges >= 10, JSON.stringify({ h1: sim.h1, units: sim.units, streams: sim.streams, badges: sim.badges }))
    if (vp.w >= 1440) record(vp.label, 'simulator: diagram (whole), controls and live results above the fold; diagram not scrolled sideways', sim.pfd.bottom <= vp.h && sim.controls.top < vp.h - 150 && sim.out.top < vp.h - 150 && sim.overflowPfd <= 1, `pfd ${Math.round(sim.pfd.top)}-${Math.round(sim.pfd.bottom)}, controls ${Math.round(sim.controls.top)}, live results ${Math.round(sim.out.top)}`)
    else record(vp.label, 'simulator: diagram starts above the fold', sim.pfd.top < vp.h - 100, `pfd ${Math.round(sim.pfd.top)}`)
    record(vp.label, 'simulator: graphs sit directly below the diagram block', sim.graphs && sim.graphs.top >= sim.grid.bottom - 1 && sim.graphs.top - sim.grid.bottom < 120, `grid bottom ${Math.round(sim.grid.bottom)}, graphs top ${Math.round(sim.graphs?.top)}`)
    const g8 = await page.evaluate(() => [...document.querySelectorAll('.sim-graphs .sim-chart')].map((c) => ({ n: c.getAttribute('data-graph'), marks: c.querySelectorAll('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg path.recharts-curve, svg .recharts-rectangle').length, axes: c.querySelectorAll('.recharts-label').length, note: /Limitation/.test(c.textContent ?? '') })))
    record(vp.label, 'simulator: eight graph cards with data marks, axis titles and a limitation note', g8.length === 8 && g8.every((g) => g.marks > 0 && g.axes >= (g.n === '7' ? 1 : 2) && g.note), JSON.stringify(g8))
    // play / pause
    const play = page.locator('button.sim-play')
    const p0 = await play.getAttribute('aria-pressed')
    const parts0 = await page.locator('.sim-pfd .pfd-particle').count()
    await page.waitForTimeout(400)
    const pos1 = await page.locator('.sim-pfd .pfd-particle').first().getAttribute('cx').catch(() => null)
    await page.waitForTimeout(400)
    const pos2 = await page.locator('.sim-pfd .pfd-particle').first().getAttribute('cx').catch(() => null)
    record(vp.label, 'simulator: playing on load (no reduced motion), particles exist and move', p0 === 'true' && parts0 > 20 && pos1 !== pos2, `aria-pressed=${p0}, particles=${parts0}, cx ${pos1} -> ${pos2}`)
    if (args['no-shots'] !== 'true') await page.screenshot({ path: shotPath('', vp.label, false, 'simulator_playing') })
    await play.click(); await page.waitForTimeout(250)
    const p1 = await play.getAttribute('aria-pressed'); const t1 = await play.innerText(); const parts1 = await page.locator('.sim-pfd .pfd-particle').count()
    record(vp.label, 'simulator: Play/Pause toggles to Play (aria-pressed=false, no particles)', p1 === 'false' && /Play/.test(t1) && parts1 === 0, `aria-pressed=${p1}, text=${t1.trim()}, particles=${parts1}`)
    if (args['no-shots'] !== 'true') await page.screenshot({ path: shotPath('', vp.label, false, 'simulator_paused') })
    await play.focus(); await page.keyboard.press('Enter'); await page.waitForTimeout(250)
    record(vp.label, 'simulator: keyboard Enter toggles back to Pause (aria-pressed=true)', (await play.getAttribute('aria-pressed')) === 'true' && (await page.locator('.sim-pfd .pfd-particle').count()) > 0)
    // temperature control changes the conversion
    const c0 = await kpi('conversion')
    const tBox = page.locator('[data-ctl="T_C"] input[type=number]')
    await tBox.fill('520'); await tBox.press('Enter'); await page.waitForTimeout(400)
    const c1 = await kpi('conversion')
    record(vp.label, 'simulator: changing the temperature changes the displayed conversion', c0 !== c1 && /%/.test(c1), `${c0} -> ${c1}`)
    // catalyst changes it (kinetic mode)
    await page.selectOption('#sim-mode', 'isothermal'); await page.waitForTimeout(400)
    const k0 = await kpi('conversion')
    await page.selectOption('#sim-cat', 'ni_takahashi_microkinetic'); await page.waitForTimeout(400)
    const k1 = await kpi('conversion')
    record(vp.label, 'simulator: switching the catalyst changes the conversion', k0 !== k1, `${k0} -> ${k1}`)
    // a zero actual-mode carbon cost is the statutory result, not an extrapolation (also after the switch to an extrapolated law)
    const ccK = await outv('carbon_cost')
    record(vp.label, 'simulator: zero actual-mode carbon cost after a catalyst switch is labelled as the statutory result', /Statutory result/.test(ccK) && !/Extrapolation/.test(ccK), ccK.replace(/\n/g, ' '))
    // carbon mode
    await page.locator('details.sim-sec:has-text("Ammonia and carbon pricing") > summary').evaluate((s) => { const d = s.parentElement; if (d && !d.open) d.open = true })
    const cc0 = await outv('carbon_cost')
    await page.locator('label:has-text("HYPOTHETICAL life-cycle price")').click(); await page.waitForTimeout(400)
    const cc1 = await outv('carbon_cost')
    const hypoNote = await page.locator('.sim-hypo').count()
    record(vp.label, 'simulator: carbon mode toggle shows HYPOTHETICAL and changes the carbon cost', /HYPOTHETICAL/.test(cc1) && hypoNote === 1 && cc0.replace(/Carbon cost.*\n?/, '') !== cc1.replace(/Carbon cost.*\n?/, ''), `${cc0.replace(/\n/g, ' ')} -> ${cc1.replace(/\n/g, ' ')}`)
    // heat integration off bypasses the FEHE
    await page.locator('details.sim-sec:has-text("Feed and heat recovery") > summary').evaluate((s) => { const d = s.parentElement; if (d && !d.open) d.open = true })
    await page.locator('.sim-switch input').uncheck(); await page.waitForTimeout(300)
    const byp = await page.locator('.sim-pfd [data-unit="FEHE"].is-bypassed').count()
    record(vp.label, 'simulator: heat integration off shows the FEHE as bypassed', byp === 1)
    await page.locator('.sim-switch input').check(); await page.waitForTimeout(200)
    // unit panel
    await page.locator('.sim-pfd [data-unit="PSA"]').click(); await page.waitForTimeout(200)
    const panel = await page.locator('.sim-panel h3').innerText()
    record(vp.label, 'simulator: clicking a unit opens its panel with values and source labels', /PSA|adsorption/.test(panel) && (await page.locator('.sim-panel .sim-badge').count()) > 0, panel)
    // compare
    await page.locator('button:has-text("Compare: pin as case A")').click()
    await tBox.fill('560'); await tBox.press('Enter'); await page.waitForTimeout(500)
    const cmp = await page.evaluate(() => ({ heads: [...document.querySelectorAll('.sim-cmp thead th')].map((t) => t.textContent), rows: document.querySelectorAll('.sim-cmp tbody tr').length }))
    record(vp.label, 'simulator: compare shows case A and case B columns and the difference', cmp.heads.some((h) => /Case A/.test(h)) && cmp.heads.some((h) => /Case B/.test(h)) && cmp.rows >= 10, JSON.stringify(cmp))
    // export
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), page.locator('button:has-text("Export CSV")').click()])
    const dlPath = await dl.path().catch(() => null)
    const csv = dlPath ? (await import('node:fs')).readFileSync(dlPath, 'utf-8') : ''
    record(vp.label, 'simulator: Export CSV downloads inputs and outputs of cases A and B with source labels', /\.csv$/.test(dl.suggestedFilename()) && /^case,section,key,label,value,unit,source,note/.test(csv) && /\nA,output,/.test(csv) && /\nB,output,/.test(csv), `${dl.suggestedFilename()} ${csv.length} bytes`)
    const [dj] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), page.locator('button:has-text("Export JSON")').click()])
    record(vp.label, 'simulator: Export JSON downloads a file', /\.json$/.test(dj.suggestedFilename()))
    await page.locator('button:has-text("Stop comparing")').click()
    await page.locator('button:has-text("Reset to baseline")').click(); await page.waitForTimeout(400)
    const base = await page.locator('[data-kpi="conversion"] .badge').innerText()
    record(vp.label, 'simulator: Reset returns to the Aspen baseline (Aspen Plus V15 label)', /Aspen Plus V15/.test(base), base)
    // fix pass: fuel-efficiency envelope beside the baseline cost, statutory carbon cost, FLUEHX label, green carbon intensities
    const blS = await snap('research/reference_scenario/baseline.json.json')
    const envT = await tid('sim-fuel-envelope')
    const envC = blS?.fuel_efficiency_sensitivity?.cases ?? []
    record(vp.label, 'simulator: fuel-efficiency envelope of the baseline cost shown from the snapshot', envC.length >= 3 && envC.every((c) => envT.includes(c.lcoh_USD_per_kg.toFixed(3))) && /optimistic/.test(envT), envT.replace(/\n/g, ' ').slice(0, 160))
    record(vp.label, 'simulator: baseline carbon cost (zero by statute) carries the statutory label', /Statutory result/.test(await outv('carbon_cost')))
    if (vp.w > 700) {
      const fl = await page.locator('.sim-pfd [data-unit="FLUEHX"]').first().textContent().catch(() => '')
      record(vp.label, 'simulator: FLUEHX diagram value is labelled as burner heat credited (not an exchanger duty)', /\d+ kW[\s\S]*burner heat credited/.test(fl ?? ''), (fl ?? '').replace(/\s+/g, ' '))
    }
    await page.locator('details.sim-sec:has-text("Ammonia and carbon pricing") > summary').evaluate((s) => { const d = s.parentElement; if (d && !d.open) d.open = true })
    await page.locator('input[name="sim-route"][value="green"]').check({ force: true }); await page.waitForTimeout(500)
    const gEmb = await outv('carbon_intensity'), gZero = await outv('carbon_intensity_zero_boundary').catch(() => '')
    const g8n = await tid('g8-green-ci')
    record(vp.label, 'simulator: green route shows both carbon intensities with their boundary (outputs and graph 8)', /embedded/.test(gEmb) && /renewable electricity as zero/.test(gZero) && /embedded/.test(g8n) && /renewable electricity as zero/.test(g8n), `${gEmb.replace(/\n/g, ' ')} | ${gZero.replace(/\n/g, ' ')} | ${g8n}`)
    await page.locator('button:has-text("Reset to baseline")').click(); await page.waitForTimeout(400)
    record(vp.label, 'simulator: no "undefined"/"NaN" text after the interactions', !/\bundefined\b|\bNaN\b|\[object /.test(await page.evaluate(() => document.body.innerText)))
  }

  if (!only || only.has('home') || only.has('overview')) {
    cur = 'interaction'
    await go('')
    // nav: eleven primary items in the top bar (desktop) or the menu (smaller screens), the other pages under "More pages"
    const wide = vp.w >= 1200
    if (!wide) { await page.click('.nav-toggle'); await page.waitForTimeout(300) }
    const links = await page.$$eval('.site-nav a', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).map((a) => a.textContent))
    record(vp.label, `nav: ${wide ? 'top bar shows the eleven primary items' : 'mobile menu shows the eleven items and the eight further pages'}`, links.length === (wide ? 11 : 19) && links[0] === 'Simulator', links.join(', '))
    if (wide) {
      await page.click('.nav-more-btn'); await page.waitForTimeout(200)
      const more = await page.$$eval('.nav-more-list a', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).map((a) => a.textContent))
      record(vp.label, 'nav: "More pages" menu lists Overview and the other seven pages', more.length === 8 && more[0] === 'Overview' && (await page.getAttribute('.nav-more-btn', 'aria-expanded')) === 'true', more.join(', '))
      await page.click('.nav-more-list a:has-text("Overview")'); await page.waitForTimeout(600)
      record(vp.label, 'nav: "Overview" opens /overview', page.url().endsWith('#/overview'), page.url())
    } else {
      const expanded = await page.getAttribute('.nav-toggle', 'aria-expanded')
      record(vp.label, 'mobile menu: toggle has aria-expanded=true when open', expanded === 'true')
      await page.click('.site-nav a:text-is("Results")'); await page.waitForTimeout(600)
      record(vp.label, 'mobile menu: link navigates and menu closes', page.url().endsWith('#/results') && !(await page.$eval('.site-nav', (n) => n.classList.contains('open'))), page.url())
    }
    await go('overview')
    // calculator
    await page.locator('#try').scrollIntoViewIfNeeded()
    const before = await page.locator('.res-main dd').first().innerText()
    const slider = page.locator('.calc input[type=range]').first()
    await slider.focus(); await page.keyboard.press('Home')
    await page.waitForTimeout(300)
    const low = await page.locator('.res-main dd').first().innerText()
    await page.keyboard.press('End'); await page.waitForTimeout(300)
    const high = await page.locator('.res-main dd').first().innerText()
    record(vp.label, 'calculator responds to the temperature slider', low !== high && /%/.test(low), `600C/20bar ${before}; 250C ${low}; 900C ${high}`)
    const lab = await page.locator('.calc .badge-browser').first().innerText()
    record(vp.label, 'calculator is labelled "calculated in your browser (ideal gas)"', /calculated in your browser \(ideal gas\)/.test(lab), lab)
    const chip = await page.locator('.calc .chip', { hasText: '20 bar' }).count()
    record(vp.label, 'calculator offers the stored Aspen pressures', chip === 1)
    await page.screenshot({ path: shotPath('', vp.label, false, 'calculator') }).catch(() => {})
    // headline facts come from the snapshot
    const facts = await page.locator('.fact-value').allInnerTexts()
    record(vp.label, 'overview: four headline facts with values', facts.length === 4 && facts.every((f) => /\d/.test(f)), facts.join(' | '))
  }

  if (!only || only.has('pfd')) {
    await go('pfd')
    cur = 'pfd-interaction'
    await page.locator('.react-flow__node[data-id="CRACKER"]').click()
    await page.waitForSelector('.pfd-side .panel', { timeout: 5000 }).catch(() => pushP('equipment panel did not open'))
    const t1 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'site PFD: equipment panel opens (CRACKER)', /CRACKER/.test(t1), t1)
    await page.keyboard.press('Escape')
    await page.locator('.lists button', { hasText: /^S5 - / }).click()
    const t2 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'site PFD: stream panel opens (S5) from the list', /^S5/.test(t2), t2)
    await page.keyboard.press('Escape')
    // real click on a drawn stream line
    await page.locator('.pfd-canvas').scrollIntoViewIfNeeded()
    const pt = await page.evaluate(() => {
      const p = document.querySelector('.react-flow__edge[data-id="S5"] path.stream-core'); if (!p) return null
      const L = p.getTotalLength(); const q = p.getPointAtLength(L * 0.55); const m = p.getScreenCTM(); return { x: m.a * q.x + m.c * q.y + m.e, y: m.b * q.x + m.d * q.y + m.f }
    })
    if (pt && pt.x > 0 && pt.y > 0 && pt.x < vp.w && pt.y < vp.h) { await page.mouse.click(pt.x, pt.y); await page.waitForTimeout(400); const t3 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => ''); record(vp.label, 'site PFD: clicking the drawn S5 line opens its panel', /^S5/.test(t3), t3); await page.keyboard.press('Escape') }
    else record(vp.label, 'site PFD: drawn S5 line is inside the viewport for a real click (skipped on small screens, list button used)', true, `pt=${JSON.stringify(pt)}`)
    // heat integration switch
    await page.getByRole('button', { name: 'Without exchanger' }).click(); await page.waitForTimeout(1200)
    const ids = await page.$$eval('.react-flow__node', (e) => e.map((x) => x.getAttribute('data-id')))
    record(vp.label, 'site PFD: "Without exchanger" removes FEHE from the diagram', !ids.includes('FEHE'), ids.length + ' nodes')
    await page.getByRole('button', { name: 'With feed/effluent exchanger' }).click(); await page.waitForTimeout(800)
  }

  if (!only || only.has('platform/pfd')) {
    await go('platform/pfd')
    cur = 'platform-pfd-interaction'
    await page.locator('.react-flow__node[data-id="HEATER"]').click()
    await page.waitForSelector('.pfd-side .panel', { timeout: 5000 }).catch(() => pushP('platform equipment panel did not open'))
    const t1 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'platform PFD: equipment panel opens (HEATER)', /HEATER/.test(t1), t1)
    await page.keyboard.press('Escape')
    await page.locator('.lists button', { hasText: /^S7 - / }).click()
    const t2 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'platform PFD: stream panel opens (S7)', /^S7/.test(t2), t2)
    await page.keyboard.press('Escape')
  }

  if (!only || only.has('anchors')) {
    cur = 'anchors'
    await page.evaluate(() => { window.location.hash = '#/results#economics' })
    await page.waitForTimeout(2500)
    const top = await page.evaluate(() => document.getElementById('economics')?.getBoundingClientRect().top ?? 9999)
    record(vp.label, 'anchor #/results#economics scrolls the section into view', top >= -5 && top < 160, `top=${Math.round(top)}`)
    await page.evaluate(() => { window.location.hash = '#/research#ref-cechetto2023membrane' })
    await page.waitForTimeout(2500)
    const t2 = await page.evaluate(() => document.getElementById('ref-cechetto2023membrane')?.getBoundingClientRect().top ?? 9999)
    record(vp.label, 'citation anchor #/research#ref-cechetto2023membrane scrolls to the reference', t2 >= -5 && t2 < 200, `top=${Math.round(t2)}`)
  }

  if (vp.w === 1440 && (!only || only.has('downloads'))) {
    cur = 'downloads'
    for (const f of ['AmCraX_Technical_Report.pdf', 'AmCraX_Technical_Report_2026-11-23.pdf','AmCraX_Technical_Report.docx', 'AmCraX_Pitch_Deck.pdf', 'AmCraX_Pitch_Deck.pptx', 'speaker_script.md', 'validation_matrix.md', 'discrepancy_analysis.md']) {
      const r = await page.request.get(`${base}downloads/${f}`)
      const len = (await r.body()).length
      record(vp.label, `download ${f}`, r.status() === 200 && len > 2000, `HTTP ${r.status()}, ${(len / 1024).toFixed(0)} kB`)
    }
    // every file prepare_site.mjs copied (paper, executive summary, research notes when they exist at build time)
    const idx = await page.request.get(`${base}downloads/index.json`)
    const listed = idx.status() === 200 ? ((await idx.json()).files ?? []) : []
    record(vp.label, 'downloads/index.json lists the copied files', idx.status() === 200 && listed.length >= 8, `HTTP ${idx.status()}, ${listed.length} files`)
    for (const f of listed) {
      const r = await page.request.get(`${base}downloads/${f.file}`)
      record(vp.label, `listed download ${f.file}`, r.status() === 200 && (await r.body()).length > 0, `HTTP ${r.status()}`)
    }
    for (const u of ['og-image.png', 'favicon.svg', 'img/pfd_baseline.png', 'snapshot/manifest.json', 'snapshot/aspen-screenshots/01_flowsheet.png', 'snapshot/simulator/model.json', 'snapshot/simulator/aspen_anchors.json', 'snapshot/simulator/parity_report.json',
      'snapshot/research/phase2_index.json', 'snapshot/research/validation/by_kind.json', 'snapshot/research/reference_scenario/baseline.json.json', 'snapshot/research/carbon_pricing/price_sweep.csv.json']) {
      const r = await page.request.get(`${base}${u}`)
      record(vp.label, `asset ${u}`, r.status() === 200, `HTTP ${r.status()}`)
    }
    const r404 = await page.request.get(`${origin}/api/health`)
    record(vp.label, 'server answers 404 outside the base path (no API)', r404.status() === 404, `HTTP ${r404.status()}`)
  }

  record(vp.label, 'overall: no console errors / failed requests during the whole session', problems.length === 0, problems.slice(0, 8).join(' | '))
  await ctx.close()
}
await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`)
if (notes404.size) console.log('HTTP >= 400 responses seen:\n  ' + [...notes404].join('\n  '))
else console.log('no HTTP >= 400 responses')
for (const f of failed) console.log(`FAILED [${f.vp}] ${f.id} - ${f.detail}`)
process.exitCode = failed.length ? 1 : 0
