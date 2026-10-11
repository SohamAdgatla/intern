import { useState } from "react";
import DashboardHeader from "./DashboardHeader";
import DashboardSidebar from "./DashboardSidebar";

const SECTIONS = [
  { id: "profile", label: "Profile" },
  { id: "overview", label: "Overview" },
  { id: "care-timeline", label: "Medical Timeline" },
  { id: "lab-trends", label: "Lab Analytics" },
  { id: "ai-insights", label: "AI Insights" },
  { id: "health-story", label: "Health Story" },
  { id: "medications", label: "Medications" },
];

export default function DashboardLayout({
  children,
  stats,
  onRefresh,
  refreshing,
  patientId,
  userName,
  onAddData,
  onOpenProfile,
  onLogout,
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");

  const scrollToSection = (id) => {
    setActiveSection(id);
    setSidebarOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-h-screen bg-slate-100/80 dark:bg-slate-900 lg:flex">
      <DashboardSidebar
        sections={SECTIONS}
        activeSection={activeSection}
        onNavigate={scrollToSection}
        onAddData={onAddData}
        onOpenProfile={onOpenProfile}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-story-trust/40 lg:hidden"
          aria-label="Close navigation menu"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex min-h-screen min-w-0 flex-1 flex-col lg:pl-64">
        <DashboardHeader
          stats={stats}
          patientId={patientId}
          userName={userName}
          onMenuClick={() => setSidebarOpen(true)}
          onRefresh={onRefresh}
          refreshing={refreshing}
          onAddData={onAddData}
          onLogout={onLogout}
        />

        <main id="main-content" className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children({ scrollToSection })}
        </main>

        <footer className="border-t border-slate-200 bg-white px-6 py-4 text-center text-sm text-slate-500">
          For your personal understanding only — not a substitute for medical advice.
        </footer>
      </div>
    </div>
  );
}
