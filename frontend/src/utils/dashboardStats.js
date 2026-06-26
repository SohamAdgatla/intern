import { formatShortDate } from "./formatters";

export function buildDashboardStats(timeline, risk) {
  const events = timeline?.events || [];
  const counts = timeline?.counts_by_type || {};

  const observations = events.filter((e) => e.resource_type === "observation");
  const latestLab = [...observations]
    .sort((a, b) => new Date(b.sort_datetime) - new Date(a.sort_datetime))[0];

  const improvingHighlights =
    timeline?.events?.length && observations.length
      ? observations.filter((o) => o.details?.in_reference_range === true).length
      : 0;

  return {
    totalEvents: timeline?.total_events ?? 0,
    observationCount: counts.observation ?? 0,
    conditionCount: counts.condition ?? 0,
    medicationCount: counts.medication ?? 0,
    inRangeCount: improvingHighlights,
    latestLabTitle: latestLab?.title || "—",
    latestLabValue: latestLab?.subtitle || "—",
    latestLabDate: latestLab ? formatShortDate(latestLab.sort_datetime) : "—",
    riskPercentage: risk?.risk_percentage ?? null,
    riskLabel: risk?.risk_label ?? null,
    lastUpdated: timeline?.generated_at ? formatShortDate(timeline.generated_at) : "—",
    yearSpan: events.length
      ? (() => {
          const years = events.map((e) => new Date(e.sort_datetime).getFullYear());
          const min = Math.min(...years);
          const max = Math.max(...years);
          return min === max ? `${min}` : `${min}–${max}`;
        })()
      : "—",
  };
}
