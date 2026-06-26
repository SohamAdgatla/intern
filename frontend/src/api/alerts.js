const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function fetchAlerts() {
  const response = await fetch(`${API_BASE}/api/alerts/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Unable to load alerts (${response.status})`);
  }
  return response.json();
}
