import { useCallback, useEffect, useState } from "react";
import { fetchRiskAssessment } from "../api/riskAssessment";
import { DEMO_RISK_ASSESSMENT } from "../fixtures/demoRiskAssessment";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export function useRiskAssessment() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (DEMO_MODE) {
        await new Promise((r) => setTimeout(r, 350));
        setData(DEMO_RISK_ASSESSMENT);
        return;
      }
      const payload = await fetchRiskAssessment();
      setData(payload);
    } catch (err) {
      setError(err.message || "Risk assessment unavailable.");
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
