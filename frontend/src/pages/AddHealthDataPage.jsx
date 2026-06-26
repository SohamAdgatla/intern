import { useEffect, useState } from "react";
import CameraCapture from "../components/CameraCapture";
import { login } from "../api/auth";
import { ensureCsrfCookie } from "../api/client";
import { fetchMeasurementTypes, submitHealthEntry } from "../api/patientInput";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

const FALLBACK_TYPES = [
  { loinc_code: "4548-4", display: "HbA1c", unit: "%", reference_low: 4.0, reference_high: 5.6 },
  { loinc_code: "8480-6", display: "Systolic blood pressure", unit: "mmHg", reference_low: 90, reference_high: 120 },
  { loinc_code: "1558-6", display: "Fasting blood glucose", unit: "mg/dL", reference_low: 70, reference_high: 99 },
];

export default function AddHealthDataPage({ onBack, onSuccess }) {
  const [types, setTypes] = useState(FALLBACK_TYPES);
  const [loincCode, setLoincCode] = useState(FALLBACK_TYPES[0].loinc_code);
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(DEMO_MODE);
  const [loginError, setLoginError] = useState(null);

  const selected = types.find((t) => t.loinc_code === loincCode) || types[0];

  useEffect(() => {
    if (DEMO_MODE) return;
    ensureCsrfCookie()
      .then(() => fetchMeasurementTypes())
      .then((data) => {
        setTypes(data);
        setLoincCode(data[0]?.loinc_code || FALLBACK_TYPES[0].loinc_code);
        setLoggedIn(true);
      })
      .catch(() => setLoggedIn(false));
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError(null);
    try {
      await ensureCsrfCookie();
      await login(username, password);
      const data = await fetchMeasurementTypes();
      setTypes(data);
      setLoggedIn(true);
    } catch (err) {
      setLoginError(err.message);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!value && !imageFile) {
      setError("Enter a value or capture a photo of your reading.");
      return;
    }

    setSubmitting(true);
    try {
      if (DEMO_MODE) {
        await new Promise((r) => setTimeout(r, 600));
        setSuccess("Saved (demo mode — connect to Django to persist data).");
        onSuccess?.();
        return;
      }

      const result = await submitHealthEntry({
        loincCode,
        value,
        unit: selected.unit,
        note,
        imageFile,
        captureSource: "camera",
      });
      setSuccess(result.message);
      setValue("");
      setNote("");
      setImageFile(null);
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!loggedIn && !DEMO_MODE) {
    return (
      <div className="min-h-screen bg-clinical-50 px-4 py-10 dark:bg-slate-900">
        <div className="mx-auto max-w-md dashboard-card p-8">
          <button type="button" onClick={onBack} className="text-sm font-semibold text-clinical-700">
            ← Back to dashboard
          </button>
          <h1 className="mt-4 font-display text-2xl font-semibold text-story-trust dark:text-white">
            Sign in to add health data
          </h1>
          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <label className="block text-sm font-semibold text-slate-600">
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-3"
                autoComplete="username"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-600">
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-3"
                autoComplete="current-password"
              />
            </label>
            {loginError && <p className="text-sm text-red-600">{loginError}</p>}
            <button type="submit" className="w-full rounded-xl bg-clinical-600 py-3 font-semibold text-white">
              Sign in
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-clinical-50 dark:bg-slate-900">
      <header className="border-b border-slate-200 bg-white px-4 py-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <button type="button" onClick={onBack} className="text-sm font-semibold text-clinical-700 dark:text-clinical-300">
            ← Dashboard
          </button>
          <h1 className="font-display text-xl font-semibold text-story-trust dark:text-white">Add health data</h1>
          <span className="w-16" />
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <form onSubmit={handleSubmit} className="dashboard-card space-y-6 p-6">
          <section aria-labelledby="measurement-heading">
            <h2 id="measurement-heading" className="font-display text-lg font-semibold text-story-trust dark:text-white">
              What did you measure?
            </h2>
            <select
              value={loincCode}
              onChange={(e) => setLoincCode(e.target.value)}
              className="mt-3 w-full rounded-xl border border-slate-200 px-4 py-3 text-base dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            >
              {types.map((t) => (
                <option key={t.loinc_code} value={t.loinc_code}>
                  {t.display}
                </option>
              ))}
            </select>
          </section>

          <section aria-labelledby="value-heading">
            <h2 id="value-heading" className="font-display text-lg font-semibold text-story-trust dark:text-white">
              Enter the number (optional if you upload a photo)
            </h2>
            <div className="mt-3 flex gap-3">
              <input
                type="number"
                step="any"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={`e.g. 6.2`}
                className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-lg dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                aria-describedby="range-hint"
              />
              <span className="flex items-center rounded-xl bg-slate-100 px-4 text-sm font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                {selected.unit}
              </span>
            </div>
            {selected.reference_low != null && (
              <p id="range-hint" className="mt-2 text-sm text-slate-500">
                Typical range: {selected.reference_low}–{selected.reference_high} {selected.unit}
              </p>
            )}
          </section>

          <section aria-labelledby="camera-heading">
            <h2 id="camera-heading" className="font-display text-lg font-semibold text-story-trust dark:text-white">
              Or capture from camera
            </h2>
            <div className="mt-3">
              <CameraCapture onCapture={setImageFile} disabled={submitting} />
            </div>
          </section>

          <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300">
            Notes (optional)
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              placeholder="e.g. Taken before breakfast"
            />
          </label>

          {error && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-xl bg-clinical-50 px-4 py-3 text-sm text-clinical-800 dark:bg-clinical-900/40 dark:text-clinical-100" role="status">
              {success}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-clinical-600 py-4 text-base font-bold text-white hover:bg-clinical-700 disabled:opacity-60"
          >
            {submitting ? "Saving…" : "Save to my health record"}
          </button>
        </form>
      </main>
    </div>
  );
}
