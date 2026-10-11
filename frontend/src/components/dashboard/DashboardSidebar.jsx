const ICONS = {
  profile: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zm-8 10a4 4 0 014-4h0a4 4 0 014 4v1H8v-1z" />
    </svg>
  ),
  overview: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
    </svg>
  ),
  "health-story": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  ),
  "lab-trends": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
    </svg>
  ),
  "care-timeline": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  "ai-insights": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  ),
  medications: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
    </svg>
  ),
};

export default function DashboardSidebar({ sections, activeSection, onNavigate, onAddData, onOpenProfile, open }) {
  return (
    <aside
      className={`dashboard-sidebar fixed inset-y-0 left-0 z-40 w-64 transform border-r border-clinical-700/20 bg-story-trust text-white transition-transform duration-200 lg:translate-x-0 ${
        open ? "translate-x-0" : "-translate-x-full"
      }`}
      aria-label="Dashboard navigation"
    >
      <div className="flex h-full flex-col">
        <div className="border-b border-white/10 px-5 py-6">
          <p className="text-xs font-bold uppercase tracking-widest text-clinical-200">Health portal</p>
          <h1 className="mt-1 font-display text-xl font-semibold">My Dashboard</h1>
          <p className="mt-1 text-sm text-clinical-100/80">Your private health story</p>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {onOpenProfile && (
            <button
              type="button"
              onClick={onOpenProfile}
              className="mb-2 flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold text-clinical-100 transition-colors hover:bg-white/10"
            >
              {ICONS.profile}
              Profile
            </button>
          )}

          {sections.map((section) => {
            const isActive = activeSection === section.id;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => onNavigate(section.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold transition-colors ${
                  isActive
                    ? "bg-clinical-600 text-white shadow-lg shadow-clinical-900/20"
                    : "text-clinical-100 hover:bg-white/10"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                {ICONS[section.id]}
                {section.label}
              </button>
            );
          })}
        </nav>

        {onAddData && (
          <div className="px-3 pb-3">
            <button
              type="button"
              onClick={onAddData}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-clinical-500 px-4 py-3 text-sm font-bold text-white shadow-lg hover:bg-clinical-400"
            >
              + Add health data
            </button>
          </div>
        )}

        <div className="border-t border-white/10 px-5 py-4 text-xs text-clinical-200/90">
          <p>HIPAA-minded secure view</p>
          <p className="mt-1">Data visible only to you</p>
        </div>
      </div>
    </aside>
  );
}
