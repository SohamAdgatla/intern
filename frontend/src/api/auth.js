import { apiFetch } from "./client";

export async function signup(username, password, givenName, familyName) {
  return apiFetch("/api/auth/signup/", {
    method: "POST",
    body: JSON.stringify({ username, password, given_name: givenName, family_name: familyName }),
  });
}

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
