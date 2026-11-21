// Per-page diagnostics: console errors, failed requests, horizontal overflow, "pending" texts.
//   node frontend/scripts/diag_pages.mjs [--base http://127.0.0.1:5173] [--width 1440] [--shots <dir>] [--query ?mode=snapshot]
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']] : a), []))
const base = args.base ?? 'http://127.0.0.1:5173'
const W = Number(args.width ?? 1440)
const query = args.query ?? ''
const routes = ['/platform', '/platform/pfd', '/platform/simulation', '/platform/reactor', '/platform/heat', '/platform/sensitivity', '/platform/optimisation', '/platform/economics', '/platform/environment', '/platform/validation', '/platform/reports']
if (args.shots) mkdirSync(args.shots, { recursive: true })
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await (await browser.newContext({ viewport: { width: W, height: 1000 } })).newPage()
let cur = ''
const log = []
page.on('pageerror', (e) => log.push(`${cur} pageerror: ${e.message}`))
page.on('console', (m) => { if (m.type() === 'error') log.push(`${cur} console: ${m.text().slice(0, 220)}`) })
page.on('response', (r) => { if (r.status() >= 400) log.push(`${cur} HTTP ${r.status()} ${r.url().replace(base, '')}`) })
page.on('requestfailed', (r) => log.push(`${cur} reqfailed ${r.url().replace(base, '')}`))
await page.goto(`${base}/${query}#/platform`, { waitUntil: 'domcontentloaded' })
for (const r of routes) {
  cur = r
  await page.evaluate((x) => { window.location.hash = '#' + x }, r)
  await page.waitForFunction(() => !/Resolving data mode|Loading|Fetching|Running\.\.\./i.test(document.body.innerText) && document.querySelector('.shell'), null, { timeout: 30000 }).catch(() => log.push(`${r} settle timeout`))
  await page.waitForTimeout(1500)
  const info = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    pending: (document.body.innerText.match(/module pending|not available yet|\bundefined\b|\bNaN\b/g) ?? []).slice(0, 5),
    badge: document.querySelector('.topbar-right .pill')?.textContent?.trim(),
  }))
  console.log(r, JSON.stringify(info))
  if (args.shots) await page.screenshot({ path: path.join(args.shots, `${r.replace('/platform/', '').replace('/platform', 'overview')}.png`) })
}
console.log(log.length ? log.join('\n') : 'no console errors / failed requests')
await browser.close()

