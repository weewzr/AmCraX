import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const API_PROXY = {
  '/api': 'http://localhost:8000',
  '/figures': 'http://localhost:8000',
  '/files': 'http://localhost:8000',
  '/aspen-screenshots': 'http://localhost:8000',
  '/dashboard-screenshots': 'http://localhost:8000',
}

/**
 * Two builds:
 *  - default (dev, `npm run build`): base "/", LIVE when the API answers; dev/preview proxy API paths to FastAPI on port 8000.
 *  - `vite build --mode pages` (`npm run build:pages`): the static GitHub Pages site, base "/AmCraX/". The app never contacts an API
 *    in this mode (see src/api/url.ts IS_PAGES) and reads the bundled snapshot instead.
 */
export default defineConfig(({ mode }) => ({
  base: mode === 'pages' ? '/AmCraX/' : '/',
  plugins: [react()],
  server: { port: 5173, proxy: API_PROXY },
  preview: { port: 4173, proxy: API_PROXY },
  test: { environment: 'node', include: ['src/**/*.test.{ts,tsx}'] },
}))
