const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function ensureCsrfCookie() {
  await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: "include" });
}

export function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.method && options.method !== "GET") {
    if (!getCsrfToken()) {
      await ensureCsrfCookie();
    }
    headers["X-CSRFToken"] = getCsrfToken();
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return body;
}
