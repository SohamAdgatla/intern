const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "long",
  day: "numeric",
});

const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

const monthYearFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
});

export function formatDate(isoString) {
  if (!isoString) return "";
  return dateFormatter.format(new Date(isoString));
}

export function formatShortDate(isoString) {
  if (!isoString) return "";
  return shortDateFormatter.format(new Date(isoString));
}

export function formatMonthYear(isoString) {
  if (!isoString) return "";
  return monthYearFormatter.format(new Date(isoString));
}

export function formatYearSpan(events) {
  if (!events?.length) return "";
  const years = events.map((e) => new Date(e.sort_datetime).getFullYear());
  const min = Math.min(...years);
  const max = Math.max(...years);
  return min === max ? `${min}` : `${min} – ${max}`;
}
