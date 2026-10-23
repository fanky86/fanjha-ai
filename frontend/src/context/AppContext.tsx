import { createContext, useContext, useEffect, useState } from "react";
import { apiCreateBuild, apiGetBuild, apiListBuilds, apiStartBuild } from "../api";
import type { Build } from "../types";

interface AppState {
  build: Build | null;
  loading: boolean;
  error: string | null;
  startBuild: () => Promise<void>;
  refresh: () => Promise<void>;
  setBuild: (b: Build | null) => void;
}

const Ctx = createContext<AppState>({
  build: null,
  loading: true,
  error: null,
  startBuild: async () => {},
  refresh: async () => {},
  setBuild: () => {},
});

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [build, setBuild] = useState<Build | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const list = await apiListBuilds();
      if (list.length === 0) {
        setBuild(null);
      } else {
        const full = await apiGetBuild(list[0].id);
        setBuild(full);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const startBuild = async () => {
    try {
      const { build_id } = await apiCreateBuild();
      await apiStartBuild(build_id);
      const full = await apiGetBuild(build_id);
      setBuild(full);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <Ctx.Provider value={{ build, loading, error, startBuild, refresh, setBuild }}>
      {children}
    </Ctx.Provider>
  );
}

export const useApp = () => useContext(Ctx);
