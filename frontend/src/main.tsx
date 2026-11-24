import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
// Self-hosted fonts (OFL 1.1, Fontsource): Latin subset of the weights the site uses; no request leaves the site's origin.
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/space-grotesk/latin-500.css'
import '@fontsource/space-grotesk/latin-600.css'
import '@fontsource/space-grotesk/latin-700.css'
import '@fontsource/jetbrains-mono/latin-400.css'
import '@fontsource/jetbrains-mono/latin-500.css'
import '@xyflow/react/dist/style.css'
import './tokens.core.css'
import './index.css'
import './pfd/pfd.css'
import './site/site.css'
import App from './App'
import { installFetchWrapper } from './api/client'
import { DataProvider } from './data/DataContext'

installFetchWrapper()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DataProvider>
      <HashRouter>
        <App />
      </HashRouter>
    </DataProvider>
  </StrictMode>,
)
