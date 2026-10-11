export default function DashboardHeader({ stats, patientId, userName, onMenuClick, onRefresh, refreshing, onAddData, onLogout }) {
  const today = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date());

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur-md dark:border-slate-700 dark:bg-slate-900/90">
      <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="rounded-lg p-2 text-story-trust hover:bg-slate-100 lg:hidden"
            aria-label="Open navigation menu"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <p className="text-sm text-slate-500">{today}</p>
            <h2 className="font-display text-xl font-semibold text-story-trust sm:text-2xl">
              {userName ? `Welcome back, ${userName}` : "Welcome back"}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {onAddData && (
            <button
              type="button"
              onClick={onAddData}
              className="hidden rounded-xl border border-clinical-600 px-4 py-2.5 text-sm font-semibold text-clinical-700 hover:bg-clinical-50 sm:inline-flex dark:border-clinical-400 dark:text-clinical-300"
            >
              + Add data
            </button>
          )}
          {onLogout && (
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Log out
            </button>
          )}
          {stats?.lastUpdated && stats.lastUpdated !== "—" && (
            <p className="hidden text-sm text-slate-500 sm:block">
              Updated {stats.lastUpdated}
              {patientId ? ` · Record #${patientId}` : ""}
            </p>
          )}
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-xl bg-clinical-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-clinical-700 disabled:opacity-60"
          >
            <svg
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>
    </header>
  );
}
