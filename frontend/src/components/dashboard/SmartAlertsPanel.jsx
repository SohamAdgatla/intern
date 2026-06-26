const SEVERITY_STYLES = {
  info: "border-l-clinical-500 bg-clinical-50 dark:bg-clinical-900/30",
  watch: "border-l-story-calm bg-amber-50 dark:bg-amber-900/20",
  attention: "border-l-story-warm bg-orange-50 dark:bg-orange-900/20",
};

const SEVERITY_LABELS = {
  info: "Good news",
  watch: "Keep an eye on",
  attention: "Needs attention",
};

export default function SmartAlertsPanel({ data, loading, error, onRetry }) {
  if (loading) {
    return (
      <section className="dashboard-card p-6" aria-busy="true">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-32 rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-16 rounded-xl bg-slate-100 dark:bg-slate-800" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="dashboard-card p-6" role="alert">
        <p className="text-sm text-slate-600 dark:text-slate-300">{error}</p>
        <button type="button" onClick={onRetry} className="mt-2 text-sm font-semibold text-clinical-700">
          Retry
        </button>
      </section>
    );
  }

  const alerts = data?.alerts || [];

  return (
    <section className="dashboard-card p-6" aria-labelledby="alerts-heading">
      <div className="flex items-center justify-between gap-4">
        <h3 id="alerts-heading" className="font-display text-lg font-semibold text-story-trust dark:text-white">
          Smart alerts
        </h3>
        {alerts.length > 0 && (
          <span className="rounded-full bg-clinical-100 px-3 py-1 text-xs font-bold text-clinical-700 dark:bg-clinical-800 dark:text-clinical-100">
            {alerts.length}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Gentle notices based on patterns in your data — not emergencies.
      </p>

      {alerts.length === 0 ? (
        <p className="mt-6 rounded-xl bg-clinical-50 p-4 text-sm text-slate-600 dark:bg-clinical-900/20 dark:text-slate-300">
          No alerts right now. That&apos;s a peaceful place to be.
        </p>
      ) : (
        <ul className="mt-5 space-y-3" aria-label="Health alerts">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className={`rounded-xl border-l-4 p-4 ${SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.info}`}
            >
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {SEVERITY_LABELS[alert.severity] || alert.severity}
              </p>
              <h4 className="mt-1 font-semibold text-story-trust dark:text-white">{alert.title}</h4>
              <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-200">{alert.message}</p>
              <p className="mt-2 text-sm font-medium text-clinical-700 dark:text-clinical-300">
                Tip: {alert.action_hint}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
