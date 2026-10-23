import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import { AppProvider } from "./context/AppContext";
import Overview from "./pages/Overview";
import LiveTraining from "./pages/LiveTraining";
import HardwareMonitor from "./pages/HardwareMonitor";
import DatasetExplorer from "./pages/DatasetExplorer";
import DebugConsole from "./pages/DebugConsole";
import BuildHistory from "./pages/BuildHistory";
import Artifacts from "./pages/Artifacts";
import Settings from "./pages/Settings";

function LayoutWithWs({ children }: { children: React.ReactNode }) {
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <BrowserRouter>
          <LayoutWithWs>
            <Routes>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<Overview />} />
              <Route path="/training" element={<LiveTraining />} />
              <Route path="/hardware" element={<HardwareMonitor />} />
              <Route path="/datasets" element={<DatasetExplorer />} />
              <Route path="/debug" element={<DebugConsole />} />
              <Route path="/history" element={<BuildHistory />} />
              <Route path="/artifacts" element={<Artifacts />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </LayoutWithWs>
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  );
}
