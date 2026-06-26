import { useCallback, useEffect, useState } from "react";
import { fetchAlerts } from "../api/alerts";
import { DEMO_ALERTS } from "../fixtures/demoAlerts";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export function useAlerts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (DEMO_MODE) {
        await new Promise((r) => setTimeout(r, 250));
        setData(DEMO_ALERTS);
        return;
      }
      setData(await fetchAlerts());
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
