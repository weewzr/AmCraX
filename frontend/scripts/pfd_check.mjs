// Interactive PFD check in Edge headless: node/edge selection, keyboard, overlays, FEHE-off case. Usage: node scripts/pfd_check.mjs [baseUrl]
import { chromium } from 'playwright-core'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const here = path.dirname(fileURLToPath(import.meta.url))
const base = process.argv[2] ?? 'http://127.0.0.1:5176'
const out = process.argv[3] ?? path.join(here, '..', '..', 'docs', 'screenshots')
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await (await browser.newContext({ viewport: { width: Number(process.env.W ?? 1440), height: Number(process.env.H ?? 900) } })).newPage()
const errs = []; page.on('pageerror', (e) => errs.push(e.message))
const ok = (c, m) => console.log((c ? 'PASS ' : 'FAIL ') + m)
await page.goto(`${base}/#/platform/pfd`); await page.waitForSelector('.react-flow__node[data-id="CRACKER"]'); await page.waitForTimeout(1200)
const ids = async (sel) => page.$$eval(sel, (els) => els.map((e) => e.getAttribute('data-id')))
let nodes = await ids('.react-flow__node'); let edges = await ids('.react-flow__edge')
ok(nodes.includes('FEHE') && edges.includes('S3') && edges.includes('S6'), 'baseline: FEHE, S3, S6 present')
// keyboard: focus a node, Enter opens panel, Escape closes
await page.focus('.react-flow__node[data-id="HEATER"]'); await page.keyboard.press('Enter')
ok(await page.locator('.pfd-side .panel-title').innerText().then((t) => t.startsWith('HEATER')), 'keyboard Enter opens HEATER panel')
await page.keyboard.press('Escape'); ok((await page.locator('.pfd-side').count()) === 0, 'Escape closes panel')
// list button
await page.click('text=S7 - PSA feed'); ok((await page.locator('.pfd-side .panel-title').innerText()).startsWith('S7'), 'list button opens stream panel')
await page.keyboard.press('Escape')
for (const l of ['T', 'P', 'Molar flow', 'Mass flow', 'Main composition']) await page.getByLabel(l, { exact: true }).check()
await page.waitForTimeout(500); await page.screenshot({ path: path.join(out, 'check_pfd_overlays.png') })
await page.selectOption('.case-select select', 'baseline_no_hi'); await page.waitForTimeout(1500)
nodes = await ids('.react-flow__node'); edges = await ids('.react-flow__edge')
ok(!nodes.includes('FEHE') && !edges.includes('S3') && !edges.includes('S6'), 'baseline_no_hi: FEHE, S3, S6 gone')
await page.screenshot({ path: path.join(out, 'check_pfd_no_hi.png') })
console.log('page errors:', errs.length ? errs : 'none')
await browser.close()
