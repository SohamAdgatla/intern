const RISK_STYLES = {
  lower: { ring: "ring-clinical-400", fill: "text-clinical-600", bg: "bg-clinical-50", label: "Lower" },
  moderate: { ring: "ring-story-calm", fill: "text-amber-700", bg: "bg-amber-50", label: "Moderate" },
  elevated: { ring: "ring-story-warm", fill: "text-orange-700", bg: "bg-orange-50", label: "Elevated" },
};

export default function RiskAssessmentCard({ data, loading, error, onRetry }) {
  if (loading) {
    return (
      <section className="dashboard-card h-full p-6" aria-busy="true">
        <div className="animate-pulse space-y-4">
          <div className="mx-auto h-28 w-28 rounded-full bg-slate-200" />
          <div className="h-4 w-2/3 rounded bg-slate-100" />
          <div className="h-16 rounded-xl bg-slate-100" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="dashboard-card h-full p-6" role="alert">
        <h3 className="font-display text-lg font-semibold text-story-trust">Wellness outlook</h3>
        <p className="mt-2 text-sm text-slate-600">{error}</p>
        <button type="button" onClick={onRetry} className="mt-4 text-sm font-semibold text-clinical-700 underline">
          Retry
        </button>
      </section>
    );
  }

  if (!data) return null;

  const style = RISK_STYLES[data.risk_label] || RISK_STYLES.moderate;
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (data.risk_percentage / 100) * circumference;

  return (
    <section className="dashboard-card flex h-full flex-col p-6" aria-labelledby="risk-card-heading">
      <h3 id="risk-card-heading" className="font-display text-lg font-semibold text-story-trust">
        Wellness outlook
      </h3>
      <p className="mt-1 text-sm text-slate-500">
        A gentle estimate based on your trends — not a diagnosis.
      </p>

      <div className="mt-6 flex flex-col items-center">
        <div className={`relative ${style.fill}`} role="img" aria-label={`${style.label} risk at ${data.risk_percentage} percent`}>
          <svg className="h-36 w-36 -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              stroke="currentColor"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-3xl font-bold">{data.risk_percentage}%</span>
            <span className="text-xs font-semibold uppercase tracking-wide">{style.label}</span>
          </div>
        </div>
      </div>

      {data.top_risk_drivers?.length > 0 && (
        <div className="mt-6 flex-1">
          <h4 className="text-sm font-semibold text-slate-600">What&apos;s influencing this</h4>
          <ul className="mt-3 space-y-2">
            {data.top_risk_drivers.map((driver) => (
              <li
                key={driver.feature}
                className={`rounded-xl px-3 py-2 text-sm ${style.bg} text-slate-700`}
              >
                {driver.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.preventative_suggestions?.length > 0 && (
        <div className="mt-5 border-t border-slate-100 pt-5">
          <h4 className="text-sm font-semibold text-slate-600">Gentle next steps</h4>
          <ul className="mt-2 space-y-2">
            {data.preventative_suggestions.map((tip, i) => (
              <li key={i} className="text-sm leading-relaxed text-slate-600">
                · {tip}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
