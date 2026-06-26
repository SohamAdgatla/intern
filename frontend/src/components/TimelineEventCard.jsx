import { formatDate } from "../utils/formatters";

const TYPE_STYLES = {
  observation: {
    ring: "ring-clinical-500",
    dot: "bg-clinical-500",
    badge: "bg-clinical-100 text-clinical-700",
    label: "Lab or vital",
  },
  condition: {
    ring: "ring-story-warm",
    dot: "bg-story-warm",
    badge: "bg-orange-100 text-orange-800",
    label: "Diagnosis",
  },
  medication: {
    ring: "ring-story-calm",
    dot: "bg-story-calm",
    badge: "bg-amber-100 text-amber-900",
    label: "Medication",
  },
};

export default function TimelineEventCard({ event, isExpanded, onToggle, isLast }) {
  const style = TYPE_STYLES[event.resource_type] || TYPE_STYLES.observation;
  const eventId = `timeline-event-${event.id}`;
  const panelId = `${eventId}-panel`;

  return (
    <li className="relative flex gap-4 pb-10 last:pb-0" role="listitem">
      {/* Vertical rail + node */}
      <div className="flex flex-col items-center" aria-hidden="true">
        <span
          className={`z-10 mt-1 h-4 w-4 shrink-0 rounded-full ring-4 ring-white ${style.dot}`}
        />
        {!isLast && <span className="timeline-rail mt-1 w-0.5 flex-1 rounded-full opacity-60" />}
      </div>

      {/* Event card */}
      <article
        className={`min-w-0 flex-1 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/80 transition-shadow hover:shadow-md ${style.ring} ring-0 hover:ring-1`}
        aria-labelledby={eventId}
      >
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-500">
              <time dateTime={event.sort_datetime}>{formatDate(event.sort_datetime)}</time>
            </p>
            <h3 id={eventId} className="mt-1 font-display text-xl font-semibold text-story-trust">
              {event.title}
            </h3>
            {event.subtitle && (
              <p className="mt-0.5 text-base text-slate-600">{event.subtitle}</p>
            )}
          </div>
          <span
            className={`inline-flex shrink-0 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${style.badge}`}
          >
            {style.label}
          </span>
        </header>

        <p className="mt-3 text-base leading-relaxed text-slate-700">{event.summary}</p>

        <button
          type="button"
          className="mt-4 text-sm font-semibold text-clinical-700 underline-offset-2 hover:underline"
          aria-expanded={isExpanded}
          aria-controls={panelId}
          onClick={onToggle}
        >
          {isExpanded ? "Hide details" : "View details"}
        </button>

        {isExpanded && (
          <div
            id={panelId}
            className="mt-4 rounded-xl bg-clinical-50 p-4 text-sm text-slate-700"
            role="region"
            aria-label={`Details for ${event.title}`}
          >
            <dl className="grid gap-2 sm:grid-cols-2">
              <DetailItem label="Status" value={event.status} />
              <DetailItem label="Category" value={event.category} />
              <DetailItem label="Recorded" value={formatDate(event.recorded_datetime)} />
              {event.details?.in_reference_range != null && (
                <DetailItem
                  label="Within expected range"
                  value={event.details.in_reference_range ? "Yes" : "No — discuss with your care team"}
                />
              )}
              {event.details?.adherence_percentage != null && (
                <DetailItem
                  label="Medication adherence"
                  value={`${event.details.adherence_percentage}%`}
                />
              )}
              {event.details?.frequency_text && (
                <DetailItem label="How to take" value={event.details.frequency_text} />
              )}
            </dl>
          </div>
        )}
      </article>
    </li>
  );
}

function DetailItem({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <dt className="font-semibold text-slate-500">{label}</dt>
      <dd className="mt-0.5">{value}</dd>
    </div>
  );
}
