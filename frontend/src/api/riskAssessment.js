const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function fetchRiskAssessment() {
  const url = `${API_BASE}/api/analytics/risk-assessment/`;

  const response = await fetch(url, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Unable to load risk assessment (${response.status})`);
  }

  return response.json();
}
