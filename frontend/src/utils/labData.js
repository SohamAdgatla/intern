/**
 * Curated LOINC codes for the lab trend chart selector.
 * Labels are patient-friendly; codes align with the Django backend.
 */
export const LAB_OPTIONS = [
  { code: "4548-4", label: "HbA1c", unit: "%", defaultLow: 4.0, defaultHigh: 5.6 },
  { code: "8480-6", label: "Systolic blood pressure", unit: "mmHg", defaultLow: 90, defaultHigh: 120 },
  { code: "8462-4", label: "Diastolic blood pressure", unit: "mmHg", defaultLow: 60, defaultHigh: 80 },
  { code: "1558-6", label: "Fasting glucose", unit: "mg/dL", defaultLow: 70, defaultHigh: 99 },
  { code: "13457-7", label: "LDL cholesterol", unit: "mg/dL", defaultLow: 0, defaultHigh: 100 },
];

/**
 * Extract chart-ready observation points from the Timeline API payload.
 */
export function extractLabSeries(timelineEvents, loincCode) {
  const observations = (timelineEvents || []).filter(
    (event) =>
      event.resource_type === "observation" &&
      event.coding?.code === loincCode &&
      event.details?.value_quantity != null
  );

  if (!observations.length) {
    return { points: [], referenceLow: null, referenceHigh: null, unit: "" };
  }

  const points = observations
    .map((event) => ({
      date: event.sort_datetime,
      label: formatChartLabel(event.sort_datetime),
      value: Number(event.details.value_quantity),
      inRange: event.details.in_reference_range,
      summary: event.summary,
    }))
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  const first = observations[0];
  const referenceLow =
    first.details.reference_low ?? LAB_OPTIONS.find((o) => o.code === loincCode)?.defaultLow ?? null;
  const referenceHigh =
    first.details.reference_high ?? LAB_OPTIONS.find((o) => o.code === loincCode)?.defaultHigh ?? null;
  const unit = first.details.value_unit || first.subtitle?.split(" ").pop() || "";

  return { points, referenceLow, referenceHigh, unit };
}

function formatChartLabel(isoString) {
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short" }).format(
    new Date(isoString)
  );
}

export function getAvailableLabs(timelineEvents) {
  const codes = new Set(
    (timelineEvents || [])
      .filter((e) => e.resource_type === "observation" && e.coding?.code)
      .map((e) => e.coding.code)
  );
  const available = LAB_OPTIONS.filter((opt) => codes.has(opt.code));
  return available.length ? available : LAB_OPTIONS.slice(0, 2);
}
