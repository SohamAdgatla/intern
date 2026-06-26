import { useCallback, useEffect, useState } from "react";
import { fetchHealthStory } from "../api/healthStory";
import { DEMO_HEALTH_STORY } from "../fixtures/demoHealthStory";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export function useHealthStory(lookbackMonths = 24) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (DEMO_MODE) {
        await new Promise((r) => setTimeout(r, 300));
        setData(DEMO_HEALTH_STORY);
        return;
      }
      const payload = await fetchHealthStory({ lookback_months: lookbackMonths });
      setData(payload);
    } catch (err) {
      setError(err.message || "Something went wrong loading your health story.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [lookbackMonths]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
