import { useCallback, useMemo, useState } from "react";
import HealthStoryPanel from "../components/HealthStoryPanel";
import HealthTimeline from "../components/HealthTimeline";
import LabTrendChart from "../components/LabTrendChart";
import AIInsightsSection from "../components/dashboard/AIInsightsSection";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import MedicationTracker from "../components/dashboard/MedicationTracker";
import OverviewSection from "../components/dashboard/OverviewSection";
import { useAccessibility } from "../context/AccessibilityContext";
import { useAlerts } from "../hooks/useAlerts";
import { useHealthStory } from "../hooks/useHealthStory";
import { useRiskAssessment } from "../hooks/useRiskAssessment";
import { useTimeline } from "../hooks/useTimeline";
import { buildDashboardStats } from "../utils/dashboardStats";

export default function Dashboard({ onAddData }) {
  const timeline = useTimeline({ types: "observation,condition,medication" });
  const healthStory = useHealthStory(24);
  const risk = useRiskAssessment();
  const alerts = useAlerts();
  const { speak } = useAccessibility();
  const [refreshing, setRefreshing] = useState(false);

  const stats = useMemo(
    () => buildDashboardStats(timeline.data, risk.data),
    [timeline.data, risk.data]
  );

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([
      timeline.reload(),
      healthStory.reload(),
      risk.reload(),
      alerts.reload(),
    ]);
    setRefreshing(false);
  }, [timeline, healthStory, risk, alerts]);

  const isLoading = timeline.loading && !timeline.data;
  const events = timeline.data?.events || [];

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:shadow-lg"
      >
        Skip to main content
      </a>

      <DashboardLayout
        stats={stats}
        patientId={timeline.data?.patient_id}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onAddData={onAddData}
      >
        {({ scrollToSection }) => (
          <div className="mx-auto max-w-7xl space-y-10">
            <OverviewSection
              stats={stats}
              risk={risk}
              alerts={alerts}
              onNavigate={scrollToSection}
            />

            <section id="care-timeline" className="scroll-mt-24">
              <div className="mb-4">
                <h2 className="font-display text-2xl font-semibold text-story-trust dark:text-white">
                  Medical timeline
                </h2>
                <p className="mt-1 text-slate-600 dark:text-slate-300">
                  Your signature health story — diagnoses, labs, and medications in one place.
                </p>
              </div>
              <HealthTimeline
                events={events}
                loading={isLoading}
                error={timeline.error}
                onRetry={timeline.reload}
              />
            </section>

            <section id="lab-trends" className="scroll-mt-24">
              <LabTrendChart timelineEvents={events} />
            </section>

            <AIInsightsSection
              risk={risk}
              healthStory={healthStory.data}
              onSpeakStory={speak}
            />

            <section id="health-story" className="scroll-mt-24">
              <HealthStoryPanel
                story={healthStory.data}
                loading={healthStory.loading}
                error={healthStory.error}
                onRetry={healthStory.reload}
              />
            </section>

            <section id="medications" className="scroll-mt-24">
              <MedicationTracker events={events} />
            </section>
          </div>
        )}
      </DashboardLayout>
    </>
  );
}
