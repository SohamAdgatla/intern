import { apiFetch } from "./client";

export async function fetchProfile() {
  return apiFetch("/api/auth/profile/");
}

export async function updateProfile(profile) {
  return apiFetch("/api/auth/profile/", {
    method: "PATCH",
    body: JSON.stringify(profile),
  });
}
