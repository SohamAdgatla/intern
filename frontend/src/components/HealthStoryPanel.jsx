const TONE_STYLES = {
  positive: "border-l-clinical-500 bg-clinical-50",
  neutral: "border-l-slate-300 bg-slate-50",
  attentive: "border-l-story-warm bg-orange-50",
};

/**
 * Health Story Mode — displays plain-language narratives from the rule engine.
 */
export default function HealthStoryPanel({ story, loading, error, onRetry }) {
  if (loading) {
    return (
      <section
        className="rounded-3xl bg-gradient-to-br from-clinical-100 to-white p-8 shadow-sm ring-1 ring-clinical-200/60"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-2/3 rounded-lg bg-clinical-200" />
          <div className="h-4 w-full rounded bg-clinical-100" />
          <div className="h-20 w-full rounded-xl bg-white/60" />
        </div>
        <p className="sr-only">Loading your health story…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-3xl border border-red-200 bg-red-50 p-8" role="alert">
        <h2 className="font-display text-xl font-semibold text-red-900">Health story unavailable</h2>
        <p className="mt-2 text-red-800">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-xl bg-red-800 px-5 py-2.5 text-sm font-semibold text-white"
        >
          Try again
        </button>
      </section>
    );
  }

  if (!story) return null;

  return (
    <section
      className="dashboard-card bg-gradient-to-br from-clinical-100 via-white to-amber-50/40 p-6 sm:p-8"
      aria-labelledby="health-story-heading"
    >
      <p className="text-xs font-bold uppercase tracking-widest text-clinical-600">
        Health story
      </p>
      <h2 id="health-story-heading" className="mt-2 font-display text-2xl font-semibold text-story-trust sm:text-3xl">
        {story.headline}
      </h2>
      <p className="mt-4 max-w-3xl text-lg leading-relaxed text-slate-700">{story.overview}</p>

      {story.paragraphs?.length > 0 && (
        <div className="mt-6 space-y-4">
          {story.paragraphs.map((paragraph, index) => (
            <p key={index} className="text-base leading-relaxed text-slate-700">
              {paragraph}
            </p>
          ))}
        </div>
      )}

      {story.highlights?.length > 0 && (
        <ul className="mt-8 space-y-4" aria-label="Individual health highlights">
          {story.highlights
            .filter((h) => h.change || h.latest_value != null)
            .map((highlight) => (
              <li
                key={highlight.loinc_code}
                className={`rounded-2xl border-l-4 p-5 ${TONE_STYLES[highlight.tone] || TONE_STYLES.neutral}`}
              >
                <h3 className="font-semibold text-story-trust">{highlight.friendly_name}</h3>
                <p className="mt-2 text-base leading-relaxed text-slate-700">{highlight.narrative}</p>
                {highlight.change && (
                  <p className="mt-2 text-sm text-slate-500">
                    {highlight.change.direction === "improving" && "↑ Improving"}
                    {highlight.change.direction === "worsening" && "↓ Needs attention"}
                    {highlight.change.direction === "stable" && "→ Holding steady"}
                    {" · "}
                    {Math.abs(highlight.change.percent_change).toFixed(0)}% over{" "}
                    {Math.round(highlight.change.months_span)} months
                  </p>
                )}
              </li>
            ))}
        </ul>
      )}

      <blockquote className="mt-8 rounded-2xl border border-clinical-200 bg-white/80 p-6">
        <p className="font-display text-lg leading-relaxed text-story-trust">{story.encouragement}</p>
      </blockquote>
    </section>
  );
}
