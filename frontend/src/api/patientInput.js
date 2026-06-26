import { apiFetch } from "./client";

export async function fetchMeasurementTypes() {
  const data = await apiFetch("/api/observations/measurement-types/");
  return data.measurement_types;
}

export async function submitHealthEntry({ loincCode, value, unit, note, imageFile, captureSource }) {
  const form = new FormData();
  form.append("loinc_code", loincCode);
  if (value !== "" && value != null) {
    form.append("value_quantity", String(value));
  }
  if (unit) form.append("value_unit", unit);
  if (note) form.append("note", note);
  form.append("capture_source", captureSource || "camera");
  if (imageFile) {
    form.append("image", imageFile, imageFile.name || "capture.jpg");
  }

  return apiFetch("/api/observations/submit/", {
    method: "POST",
    body: form,
  });
}
