import AccessibilityToolbar from "./AccessibilityToolbar";
import RiskAssessmentCard from "./RiskAssessmentCard";
import SmartAlertsPanel from "./SmartAlertsPanel";
import StatCard from "./StatCard";

export default function OverviewSection({ stats, risk, alerts, onNavigate }) {
  return (
    <section id="overview" className="scroll-mt-24 space-y-6">
      <div>
        <h2 className="font-display text-2xl font-semibold text-story-trust">Overview</h2>
        <p className="mt-1 text-slate-600">
          A calm snapshot of your care across {stats.yearSpan !== "—" ? stats.yearSpan : "your records"}.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Care events"
          value={stats.totalEvents}
          subtext="Labs, diagnoses & medications"
          accent="clinical"
          icon={<span className="text-lg font-bold">Σ</span>}
        />
        <StatCard
          label="Labs & vitals"
          value={stats.observationCount}
          subtext={`Latest: ${stats.latestLabTitle}`}
          accent="trust"
          icon={<span className="text-lg">◉</span>}
        />
        <StatCard
          label="Medications"
          value={stats.medicationCount}
          subtext={`${stats.conditionCount} active diagnosis${stats.conditionCount !== 1 ? "es" : ""}`}
          accent="calm"
          icon={<span className="text-lg">✚</span>}
        />
        <StatCard
          label="Wellness outlook"
          value={stats.riskPercentage != null ? `${stats.riskPercentage}%` : "—"}
          subtext={stats.riskLabel ? `${stats.riskLabel} estimated risk` : "Loading…"}
          accent="warm"
          icon={<span className="text-lg">◎</span>}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <article className="dashboard-card lg:col-span-2 p-6">
          <h3 className="font-display text-lg font-semibold text-story-trust">Latest reading</h3>
          <div className="mt-4 flex flex-wrap items-end gap-4">
            <div>
              <p className="text-sm text-slate-500">{stats.latestLabTitle}</p>
              <p className="font-display text-4xl font-semibold text-clinical-700">{stats.latestLabValue}</p>
            </div>
            <p className="text-sm text-slate-500">Recorded {stats.latestLabDate}</p>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onNavigate("lab-trends")}
              className="rounded-xl bg-clinical-600 px-4 py-2 text-sm font-semibold text-white hover:bg-clinical-700"
            >
              View trends
            </button>
            <button
              type="button"
              onClick={() => onNavigate("health-story")}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-story-trust hover:bg-slate-50"
            >
              Read your story
            </button>
          </div>
        </article>

        <RiskAssessmentCard
          data={risk.data}
          loading={risk.loading}
          error={risk.error}
          onRetry={risk.reload}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SmartAlertsPanel
            data={alerts.data}
            loading={alerts.loading}
            error={alerts.error}
            onRetry={alerts.reload}
          />
        </div>
        <AccessibilityToolbar />
      </div>
    </section>
  );
}
