import { useMemo, useState } from "react";
import { formatYearSpan } from "../utils/formatters";
import TimelineEventCard from "./TimelineEventCard";

const FILTER_OPTIONS = [
  { value: "all", label: "Everything" },
  { value: "observation", label: "Labs & vitals" },
  { value: "condition", label: "Diagnoses" },
  { value: "medication", label: "Medications" },
];

/**
 * Accessible vertical health timeline consuming the Timeline API payload.
 * Sorted oldest → newest per backend contract.
 */
export default function HealthTimeline({ events, loading, error, onRetry }) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);

  const filteredEvents = useMemo(() => {
    if (!events) return [];
    if (activeFilter === "all") return events;
    return events.filter((e) => e.resource_type === activeFilter);
  }, [events, activeFilter]);

  if (loading) {
    return (
      <section className="dashboard-card p-8" aria-busy="true" aria-live="polite">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 rounded-lg bg-slate-200" />
          <div className="h-4 w-full max-w-md rounded bg-slate-100" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4">
              <div className="h-4 w-4 rounded-full bg-clinical-200" />
              <div className="h-24 flex-1 rounded-2xl bg-slate-100" />
            </div>
          ))}
        </div>
        <p className="sr-only">Loading your health timeline…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section
        className="rounded-3xl border border-red-200 bg-red-50 p-8 text-red-900"
        role="alert"
      >
        <h2 className="font-display text-xl font-semibold">We couldn&apos;t load your timeline</h2>
        <p className="mt-2 text-base">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-xl bg-red-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-900"
        >
          Try again
        </button>
      </section>
    );
  }

  if (!filteredEvents.length) {
    return (
      <section className="dashboard-card p-8 text-center">
        <h2 className="font-display text-xl font-semibold text-story-trust">No events yet</h2>
        <p className="mt-2 text-slate-600">
          When your care team adds labs, diagnoses, or medications, they&apos;ll appear here in
          chronological order.
        </p>
      </section>
    );
  }

  const yearSpan = formatYearSpan(filteredEvents);

  return (
    <section className="dashboard-card p-6 sm:p-8" aria-labelledby="timeline-heading">
      <header className="mb-8 border-b border-slate-100 pb-6">
        <h2 id="timeline-heading" className="font-display text-2xl font-semibold text-story-trust sm:text-3xl">
          Your care timeline
        </h2>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          A gentle, chronological view of your health story
          {yearSpan ? ` from ${yearSpan}` : ""}. Oldest moments appear first — scroll down for more
          recent care.
        </p>

        <div
          className="mt-5 flex flex-wrap gap-2"
          role="group"
          aria-label="Filter timeline by type"
        >
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setActiveFilter(opt.value)}
              aria-pressed={activeFilter === opt.value}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                activeFilter === opt.value
                  ? "bg-clinical-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </header>

      <ol className="list-none" aria-label="Health events in chronological order">
        {filteredEvents.map((event, index) => (
          <TimelineEventCard
            key={event.id}
            event={event}
            isLast={index === filteredEvents.length - 1}
            isExpanded={expandedId === event.id}
            onToggle={() => setExpandedId((prev) => (prev === event.id ? null : event.id))}
          />
        ))}
      </ol>

      <p className="mt-6 text-center text-sm text-slate-500" aria-live="polite">
        Showing {filteredEvents.length} event{filteredEvents.length !== 1 ? "s" : ""}
      </p>
    </section>
  );
}
