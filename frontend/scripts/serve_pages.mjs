// Serve frontend/dist the way GitHub Pages serves a project site: under /AmCraX/ only, 404 everywhere else, no API.
//
//   node scripts/serve_pages.mjs [--port 4180] [--dir dist] [--prefix /AmCraX/]
//
// Mirrors Pages behaviour: "/AmCraX" redirects to "/AmCraX/", "/" is a 404, unknown files under the prefix return 404.html
// (copy of index.html) with status 404, files are served with proper content types, nothing else is reachable (no /api).
import { createReadStream, existsSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1]]] : a), []))
const port = Number(args.port ?? 4180)
const root = path.resolve(args.dir ?? path.join(here, '..', 'dist'))
let prefix = args.prefix ?? '/AmCraX/'
if (!prefix.endsWith('/')) prefix += '/'

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon',
  '.pdf': 'application/pdf', '.md': 'text/markdown; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.woff2': 'font/woff2',
}

const server = createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost')
  let p = decodeURIComponent(url.pathname)
  if (p === prefix.slice(0, -1)) { res.writeHead(301, { Location: prefix }); res.end(); return }
  if (!p.startsWith(prefix)) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('404 (outside the project site path)'); return }
  let rel = p.slice(prefix.length)
  if (rel === '' || rel.endsWith('/')) rel += 'index.html'
  const file = path.resolve(root, rel)
  if (!file.startsWith(root + path.sep) && file !== root) { res.writeHead(403); res.end(); return }
  if (existsSync(file) && statSync(file).isFile()) {
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] ?? 'application/octet-stream', 'Content-Length': statSync(file).size, 'Cache-Control': 'no-cache' })
    if (req.method === 'HEAD') res.end(); else createReadStream(file).pipe(res)
    return
  }
  const nf = path.join(root, '404.html')
  if (existsSync(nf)) { res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' }); createReadStream(nf).pipe(res); return }
  res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('404')
})
server.listen(port, '127.0.0.1', () => console.log(`serving ${root} at http://127.0.0.1:${port}${prefix} (404 elsewhere, no API)`))
