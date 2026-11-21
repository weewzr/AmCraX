// End-to-end LIVE check of the Simulation page (Python engine only, never Aspen); deletes the case it created.
//   node frontend/scripts/e2e_sim_run.mjs [--base http://127.0.0.1:5173] [--api http://127.0.0.1:8000] [--out <dir>]
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1]]] : a), []))
const base = args.base ?? 'http://127.0.0.1:5173'
const api = args.api ?? 'http://127.0.0.1:8000'
const out = path.resolve(args.out ?? path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'docs', 'screenshots'))
const name = 'e2e_t650'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await (await browser.newContext({ viewport: { width: 1600, height: 1000 } })).newPage()
const errs = []
page.on('pageerror', (e) => errs.push(e.message))
await page.goto(`${base}/#/platform/simulation`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('text=Operating conditions', { timeout: 30000 })
await page.fill('input[value^="user_case"]', name).catch(async () => { await page.locator('label:has-text("Case name") input').fill(name) })
await page.getByRole('button', { name: 'Python model' }).first().click()
await page.locator('label:has-text("Cracker temperature") input').fill('650')
await page.getByRole('button', { name: /Run Python model/ }).click()
await page.waitForSelector(`text=Case ${name}`, { timeout: 60000 })
await page.waitForTimeout(1500)
const kpi = await page.evaluate(() => document.body.innerText.match(/NH3 conversion[\s\S]{0,40}/)?.[0])
console.log('KPI text:', JSON.stringify(kpi))
await page.evaluate(() => window.scrollTo(0, 650))
await page.screenshot({ path: path.join(out, 'dashboard_simulation_run.png') })
const caseInList = (await (await fetch(`${api}/api/cases`)).text()).includes(name)
console.log('case in store:', caseInList)
const r = await fetch(`${api}/api/cases/${name}`, { method: 'DELETE' })
console.log('DELETE', r.status, 'still listed:', (await (await fetch(`${api}/api/cases`)).text()).includes(name))
console.log('page errors:', errs.length ? errs : 'none')
await browser.close()

