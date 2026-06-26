import { useMemo } from "react";
import { formatShortDate } from "../../utils/formatters";

export default function MedicationTracker({ events }) {
  const medications = useMemo(
    () =>
      (events || [])
        .filter((e) => e.resource_type === "medication")
        .sort((a, b) => new Date(b.sort_datetime) - new Date(a.sort_datetime)),
    [events]
  );

  return (
    <section className="dashboard-card p-6" aria-labelledby="meds-heading">
      <h3 id="meds-heading" className="font-display text-lg font-semibold text-story-trust dark:text-white">
        Medication tracker
      </h3>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Your medicines, dosages, and adherence over time.
      </p>

      {medications.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">No medications recorded yet.</p>
      ) : (
        <ul className="mt-5 space-y-3">
          {medications.map((med) => {
            const adherence = med.details?.adherence_percentage;
            const isActive = med.details?.is_active;
            return (
              <li
                key={med.id}
                className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-800/50"
              >
                <div>
                  <p className="font-semibold text-story-trust dark:text-white">{med.title}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300">{med.subtitle}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Started {formatShortDate(med.sort_datetime)}
                    {med.details?.frequency_text ? ` · ${med.details.frequency_text}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block rounded-full px-3 py-1 text-xs font-bold uppercase ${
                      isActive
                        ? "bg-clinical-100 text-clinical-800 dark:bg-clinical-900 dark:text-clinical-100"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {med.status}
                  </span>
                  {adherence != null && (
                    <p className="mt-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
                      {adherence}% adherence
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
