import { useAccessibility } from "../../context/AccessibilityContext";

function Toggle({ label, checked, onChange, description }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800">
      <span>
        <span className="block text-sm font-semibold text-story-trust dark:text-slate-100">{label}</span>
        {description && <span className="block text-xs text-slate-500 dark:text-slate-400">{description}</span>}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 rounded border-slate-300 text-clinical-600 focus:ring-clinical-500"
      />
    </label>
  );
}

export default function AccessibilityToolbar() {
  const a11y = useAccessibility();

  return (
    <section
      className="dashboard-card p-4"
      aria-labelledby="a11y-toolbar-heading"
    >
      <h3 id="a11y-toolbar-heading" className="text-sm font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Accessibility
      </h3>
      <div className="mt-2 space-y-1">
        <Toggle label="Dark mode" checked={a11y.darkMode} onChange={a11y.setDarkMode} />
        <Toggle label="Large text" checked={a11y.largeText} onChange={a11y.setLargeText} description="Easier reading for low vision" />
        <Toggle label="High contrast" checked={a11y.highContrast} onChange={a11y.setHighContrast} />
        <Toggle label="Reduce motion" checked={a11y.reducedMotion} onChange={a11y.setReducedMotion} />
      </div>
    </section>
  );
}
