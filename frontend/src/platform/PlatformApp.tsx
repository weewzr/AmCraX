import { Route, Routes } from 'react-router-dom'
import { Shell } from '../components/Shell'
import Overview from '../pages/Overview'
import PfdPage from '../pages/PfdPage'
import Pending from '../pages/Pending'
import SimulationPage from '../pages/SimulationPage'
import ReactorPage from '../pages/ReactorPage'
import HeatPage from '../pages/HeatPage'
import SensitivityPage from '../pages/SensitivityPage'
import OptimisationPage from '../pages/OptimisationPage'
import EconomicsPage from '../pages/EconomicsPage'
import EnvironmentPage from '../pages/EnvironmentPage'
import ValidationPage from '../pages/ValidationPage'
import ReportsPage from '../pages/ReportsPage'

/** The engineering dashboard (all eleven pages), mounted under /platform by App.tsx. Paths here are relative to /platform. */
export default function PlatformApp() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Overview />} />
        <Route path="pfd" element={<PfdPage />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="reactor" element={<ReactorPage />} />
        <Route path="heat" element={<HeatPage />} />
        <Route path="sensitivity" element={<SensitivityPage />} />
        <Route path="optimisation" element={<OptimisationPage />} />
        <Route path="economics" element={<EconomicsPage />} />
        <Route path="environment" element={<EnvironmentPage />} />
        <Route path="validation" element={<ValidationPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="*" element={<Pending title="Not found" description="This platform page does not exist." />} />
      </Route>
    </Routes>
  )
}
