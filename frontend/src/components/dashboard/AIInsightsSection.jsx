import RiskAssessmentCard from "./RiskAssessmentCard";

/**
 * AI Insights — combines risk assessment + health story highlights.
 */
export default function AIInsightsSection({ risk, healthStory, onSpeakStory }) {
  return (
    <section id="ai-insights" className="scroll-mt-24 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-story-trust dark:text-white">
            AI insights
          </h2>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            Plain-language explanations — no medical jargon required.
          </p>
        </div>
        {healthStory?.headline && onSpeakStory && (
          <button
            type="button"
            onClick={() =>
              onSpeakStory(
                [healthStory.headline, healthStory.overview, healthStory.encouragement]
                  .filter(Boolean)
                  .join(". ")
              )
            }
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-story-trust hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          >
            <span aria-hidden="true">🔊</span>
            Listen to summary
          </button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <article className="dashboard-card p-6">
          {healthStory?.overview ? (
            <>
              <h3 className="font-display text-lg font-semibold text-story-trust dark:text-white">
                {healthStory.headline}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-slate-700 dark:text-slate-200">
                {healthStory.overview}
              </p>
              {healthStory.encouragement && (
                <blockquote className="mt-4 border-l-4 border-clinical-400 pl-4 text-sm italic text-slate-600 dark:text-slate-300">
                  {healthStory.encouragement}
                </blockquote>
              )}
            </>
          ) : (
            <p className="text-slate-500">Health story insights loading…</p>
          )}
        </article>
        <RiskAssessmentCard
          data={risk.data}
          loading={risk.loading}
          error={risk.error}
          onRetry={risk.reload}
        />
      </div>
    </section>
  );
}
