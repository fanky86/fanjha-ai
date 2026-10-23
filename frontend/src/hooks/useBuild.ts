import { useEffect, useState } from "react";
import { apiGetBuild, apiListBuilds } from "../api";
import type { Build } from "../types";

export function useActiveBuild() {
  const [build, setBuild] = useState<Build | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const list = await apiListBuilds();
      if (list.length === 0) {
        setBuild(null);
        setLoading(false);
        return;
      }
      const full = await apiGetBuild(list[0].id);
      setBuild(full);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { build, setBuild, loading, error, refresh };
}
