import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { extractLabSeries, getAvailableLabs, LAB_OPTIONS } from "../utils/labData";

/**
 * Multi-year lab trend chart with a shaded "normal range" band to reduce anxiety.
 * Uses Recharts ReferenceArea for the expected range and a calm color palette.
 */
export default function LabTrendChart({ timelineEvents }) {
  const availableLabs = useMemo(() => getAvailableLabs(timelineEvents), [timelineEvents]);
  const [selectedCode, setSelectedCode] = useState(availableLabs[0]?.code || LAB_OPTIONS[0].code);

  const selectedMeta = availableLabs.find((l) => l.code === selectedCode) || LAB_OPTIONS[0];
  const { points, referenceLow, referenceHigh, unit } = useMemo(
    () => extractLabSeries(timelineEvents, selectedCode),
    [timelineEvents, selectedCode]
  );

  const yDomain = useMemo(() => {
    if (!points.length) return [0, 10];
    const values = points.map((p) => p.value);
    const all = [...values];
    if (referenceLow != null) all.push(referenceLow);
    if (referenceHigh != null) all.push(referenceHigh);
    const min = Math.min(...all);
    const max = Math.max(...all);
    const padding = (max - min) * 0.15 || 1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [points, referenceLow, referenceHigh]);

  const hasRange = referenceLow != null && referenceHigh != null;

  return (
    <section
      className="dashboard-card p-6 sm:p-8"
      aria-labelledby="lab-chart-heading"
    >
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="lab-chart-heading" className="font-display text-2xl font-semibold text-story-trust">
            How your numbers are trending
          </h2>
          <p className="mt-2 max-w-xl text-base text-slate-600">
            The green band shows the typical expected range. Your personal targets may differ —
            always follow guidance from your care team.
          </p>
        </div>

        <label className="flex flex-col gap-1 text-sm font-semibold text-slate-600">
          Choose a measurement
          <select
            value={selectedCode}
            onChange={(e) => setSelectedCode(e.target.value)}
            className="min-w-[12rem] rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-base font-medium text-story-trust shadow-sm"
          >
            {availableLabs.map((lab) => (
              <option key={lab.code} value={lab.code}>
                {lab.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      {points.length < 2 ? (
        <div
          className="flex min-h-[280px] items-center justify-center rounded-2xl bg-clinical-50 p-8 text-center"
          role="status"
        >
          <p className="max-w-md text-slate-600">
            We need at least two <strong>{selectedMeta.label}</strong> results over time to show a
            trend. As more results are added, your chart will appear here.
          </p>
        </div>
      ) : (
        <>
          <div
            className="h-[320px] w-full sm:h-[360px]"
            role="img"
            aria-label={`Line chart of ${selectedMeta.label} over time with expected range band`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={points} margin={{ top: 12, right: 16, left: 4, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />

                {hasRange && (
                  <ReferenceArea
                    y1={referenceLow}
                    y2={referenceHigh}
                    fill="#2a9d8f"
                    fillOpacity={0.12}
                    strokeOpacity={0}
                    ifOverflow="extendDomain"
                  />
                )}

                <XAxis
                  dataKey="label"
                  tick={{ fill: "#475569", fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: "#cbd5e1" }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fill: "#475569", fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: "#cbd5e1" }}
                  unit={unit ? ` ${unit}` : ""}
                  width={56}
                />

                <Tooltip content={<CalmTooltip unit={unit} referenceLow={referenceLow} referenceHigh={referenceHigh} />} />

                <Line
                  type="monotone"
                  dataKey="value"
                  name={selectedMeta.label}
                  stroke="#264653"
                  strokeWidth={3}
                  dot={{ r: 5, fill: "#2a9d8f", stroke: "#fff", strokeWidth: 2 }}
                  activeDot={{ r: 7, fill: "#238b7f" }}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {hasRange && (
            <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-600">
              <span className="inline-flex items-center gap-2">
                <span
                  className="inline-block h-3 w-8 rounded-sm bg-clinical-500/20 ring-1 ring-clinical-500/30"
                  aria-hidden="true"
                />
                Expected range: {referenceLow}–{referenceHigh} {unit}
              </span>
              <span className="inline-flex items-center gap-2">
                <span
                  className="inline-block h-0.5 w-8 bg-story-trust"
                  aria-hidden="true"
                />
                Your results
              </span>
            </div>
          )}

          {/* Screen-reader accessible data table fallback */}
          <table className="sr-only">
            <caption>{selectedMeta.label} results over time</caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.date}>
                  <td>{p.label}</td>
                  <td>
                    {p.value} {unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function CalmTooltip({ active, payload, unit, referenceLow, referenceHigh }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const inRange =
    referenceLow != null && referenceHigh != null
      ? point.value >= referenceLow && point.value <= referenceHigh
      : null;

  return (
    <div className="max-w-xs rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-lg">
      <p className="text-sm font-semibold text-story-trust">{point.label}</p>
      <p className="mt-1 text-lg font-bold text-clinical-700">
        {point.value}
        {unit ? ` ${unit}` : ""}
      </p>
      {inRange != null && (
        <p className={`mt-1 text-sm ${inRange ? "text-clinical-700" : "text-amber-800"}`}>
          {inRange
            ? "Within the typical expected range"
            : "Outside the typical range — your clinician can help interpret this"}
        </p>
      )}
      {point.summary && <p className="mt-2 text-xs leading-relaxed text-slate-500">{point.summary}</p>}
    </div>
  );
}
