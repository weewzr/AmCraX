import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import '@xyflow/react/dist/style.css'
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

