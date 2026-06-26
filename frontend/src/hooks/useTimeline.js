import { useCallback, useEffect, useState } from "react";
import { fetchTimeline } from "../api/timeline";
import { DEMO_TIMELINE } from "../fixtures/demoTimeline";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

/**
 * Loads and refreshes the Timeline API payload for the authenticated patient.
 */
export function useTimeline(filters = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const filterKey = JSON.stringify(filters);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (DEMO_MODE) {
        await new Promise((r) => setTimeout(r, 400));
        setData(DEMO_TIMELINE);
        return;
      }
      const payload = await fetchTimeline(filters);
      setData(payload);
    } catch (err) {
      setError(err.message || "Something went wrong loading your timeline.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filterKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
