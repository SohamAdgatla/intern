import { useEffect, useState } from "react";
import { fetchProfile, updateProfile } from "../api/profile";

export default function ProfilePage({ userName, currentUser, onBack, onProfileUpdated }) {
  const [profile, setProfile] = useState({
    username: currentUser?.username || userName || "",
    full_name: currentUser?.full_name || userName || "",
    given_name: currentUser?.given_name || "",
    family_name: currentUser?.family_name || "",
    email_contact: "",
    phone: "",
    birth_date: "",
    gender: "unknown",
    address_line: "",
    city: "",
    state: "",
    postal_code: "",
    country: "US",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let ignore = false;

    fetchProfile()
      .then((data) => {
        if (ignore) return;
        setProfile((current) => ({
          ...current,
          ...data,
          username: data.username || current.username,
          full_name: data.full_name || current.full_name,
        }));
      })
      .catch(() => {
        if (!ignore) {
          setProfile((current) => ({
            ...current,
            username: currentUser?.username || current.username,
            full_name: currentUser?.full_name || current.full_name,
          }));
        }
      });

    return () => {
      ignore = true;
    };
  }, [currentUser]);

  const handleChange = (field) => (event) => {
    setProfile((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updated = await updateProfile(profile);
      const nextUser = { ...currentUser, ...updated };
      setProfile((current) => ({ ...current, ...updated }));
      onProfileUpdated?.(nextUser);
      setSuccess("Profile updated successfully.");
    } catch (err) {
      setError(err.message || "Could not save the profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100/80 dark:bg-slate-900">
      <header className="border-b border-slate-200 bg-white/80 px-4 py-4 backdrop-blur-md dark:border-slate-700 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <button type="button" onClick={onBack} className="text-sm font-semibold text-clinical-700 dark:text-clinical-300">
            ← Back to dashboard
          </button>
          <h1 className="font-display text-xl font-semibold text-story-trust dark:text-white">Profile settings</h1>
          <div className="w-20" />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <aside className="dashboard-card rounded-3xl p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-clinical-600 text-2xl font-bold text-white shadow-lg shadow-clinical-600/20">
                {(profile.full_name || userName || "P").charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Patient</p>
                <h2 className="mt-1 font-display text-2xl font-semibold text-story-trust dark:text-white">
                  {profile.full_name || userName || "Patient profile"}
                </h2>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Username</p>
                <p className="mt-2 text-base font-semibold text-story-trust dark:text-white">{profile.username || "Patient"}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Status</p>
                <p className="mt-2 text-base font-semibold text-emerald-600">Active account</p>
              </div>
            </div>
          </aside>

          <section className="dashboard-card rounded-3xl p-6 sm:p-8">
            <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-clinical-600">Account details</p>
                <h2 className="mt-2 font-display text-3xl font-semibold text-story-trust dark:text-white">
                  Personal information
                </h2>
              </div>
              <p className="text-sm text-slate-500">Keep your record up to date</p>
            </div>

            <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                First name
                <input
                  value={profile.given_name || ""}
                  onChange={handleChange("given_name")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Last name
                <input
                  value={profile.family_name || ""}
                  onChange={handleChange("family_name")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Username
                <input
                  value={profile.username || ""}
                  disabled
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-100 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Phone
                <input
                  value={profile.phone || ""}
                  onChange={handleChange("phone")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300 md:col-span-2">
                Email
                <input
                  type="email"
                  value={profile.email_contact || ""}
                  onChange={handleChange("email_contact")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Date of birth
                <input
                  type="date"
                  value={profile.birth_date || ""}
                  onChange={handleChange("birth_date")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Gender
                <select
                  value={profile.gender || "unknown"}
                  onChange={handleChange("gender")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                >
                  <option value="unknown">Unknown</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other</option>
                </select>
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300 md:col-span-2">
                Address
                <input
                  value={profile.address_line || ""}
                  onChange={handleChange("address_line")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                City
                <input
                  value={profile.city || ""}
                  onChange={handleChange("city")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                State
                <input
                  value={profile.state || ""}
                  onChange={handleChange("state")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Postal code
                <input
                  value={profile.postal_code || ""}
                  onChange={handleChange("postal_code")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <label className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Country
                <input
                  value={profile.country || "US"}
                  onChange={handleChange("country")}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                />
              </label>

              <div className="md:col-span-2 flex items-center justify-between gap-3 pt-2">
                <div>
                  {error && <p className="text-sm text-red-600">{error}</p>}
                  {success && <p className="text-sm text-green-600">{success}</p>}
                </div>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-xl bg-clinical-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-clinical-600/20 hover:bg-clinical-700 disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Save profile"}
                </button>
              </div>
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}
