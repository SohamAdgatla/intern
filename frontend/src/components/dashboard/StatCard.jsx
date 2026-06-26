export default function StatCard({ label, value, subtext, accent = "clinical", icon }) {
  const accents = {
    clinical: "from-clinical-500 to-clinical-700",
    warm: "from-story-warm to-orange-600",
    calm: "from-story-calm to-amber-600",
    trust: "from-story-trust to-slate-800",
  };

  return (
    <article className="dashboard-card flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold text-story-trust">{value}</p>
          {subtext && <p className="mt-1 text-sm text-slate-500">{subtext}</p>}
        </div>
        {icon && (
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${accents[accent]} text-white shadow-md`}
            aria-hidden="true"
          >
            {icon}
          </div>
        )}
      </div>
    </article>
  );
}
