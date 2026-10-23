import { NavLink } from "react-router-dom";
import {
  Activity, Cpu, Database, Terminal, History, Package,
  Settings as SettingsIcon, Play, Zap,
} from "lucide-react";
import { useState } from "react";
import { useApp } from "../context/AppContext";
import StatusBadge from "./StatusBadge";
import ConnectionStatus from "./ConnectionStatus";
import ConfirmDialog from "./ConfirmDialog";
import type { WSState } from "../hooks/useWebSocket";

const NAV = [
  { to: "/overview", label: "Overview", icon: Activity },
  { to: "/training", label: "Live Training", icon: Play },
  { to: "/hardware", label: "Hardware", icon: Cpu },
  { to: "/datasets", label: "Datasets", icon: Database },
  { to: "/debug", label: "Debug Console", icon: Terminal },
  { to: "/history", label: "Build History", icon: History },
  { to: "/artifacts", label: "Artifacts", icon: Package },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Layout({
  children, wsState,
}: { children: React.ReactNode; wsState?: WSState }) {
  const { build, startBuild, error } = useApp();
  const [starting, setStarting] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const canStart =
    !build ||
    ["IDLE", "FAILED", "CANCELLED", "SUCCESS", "WARNING"].includes(build.status);

  const handleStart = async () => {
    setStarting(true);
    try {
      await startBuild();
      setToast("Build started");
    } catch (e) {
      setToast(`Failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setStarting(false);
      setConfirm(false);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const requestStart = () => {
    if (build && ["FAILED", "CANCELLED", "SUCCESS", "WARNING"].includes(build.status)) {
      setConfirm(true);
    } else {
      handleStart();
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <Zap size={22} /> FANJHA <span>AI</span>
        </div>
        <nav>
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => (isActive ? "nav active" : "nav")}
            >
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {build && (
            <div className="build-info">
              <StatusBadge status={build.status} />
              <div className="build-id">#{build.id.slice(0, 8)}</div>
            </div>
          )}
          {wsState && <ConnectionStatus state={wsState} />}
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            {build && (
              <>
                <span className="build-correlation">
                  correlation: {build.correlation_id.slice(0, 8)}
                </span>
                {build.error_summary && (
                  <span className="topbar-error" title={build.error_summary}>
                    ⚠ {build.error_summary.slice(0, 60)}
                  </span>
                )}
              </>
            )}
            {error && <span className="topbar-error">API error: {error}</span>}
          </div>
          <button
            className="btn primary"
            onClick={requestStart}
            disabled={starting || !canStart}
            title={canStart ? "Create and start a new build" : "A build is currently running"}
          >
            <Play size={16} /> {starting ? "Starting…" : "START FULL BUILD"}
          </button>
        </header>
        <div className="content">{children}</div>
      </main>
      {confirm && (
        <ConfirmDialog
          title="Start a new build?"
          message="An existing build with the same output directory will be overwritten. Continue?"
          onCancel={() => setConfirm(false)}
          onConfirm={handleStart}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
