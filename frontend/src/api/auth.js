import { apiFetch } from "./client";

export async function login(username, password) {
  return apiFetch("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logout() {
  return apiFetch("/api/auth/logout/", { method: "POST", body: "{}" });
}

export async function fetchCurrentUser() {
  return apiFetch("/api/auth/me/");
}
