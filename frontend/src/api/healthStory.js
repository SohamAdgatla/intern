const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function fetchHealthStory(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });

  const query = search.toString();
  const url = `${API_BASE}/api/health-story/${query ? `?${query}` : ""}`;

  const response = await fetch(url, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Unable to load your health story (${response.status})`);
  }

  return response.json();
}
