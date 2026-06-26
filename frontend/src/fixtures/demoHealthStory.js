export const DEMO_HEALTH_STORY = {
  patient_id: 1,
  headline: "Your health numbers are moving in an encouraging direction",
  overview:
    "Over the past about 2 years, we've looked at how your key health numbers have changed. 1 area shows improvement.",
  paragraphs: [
    "Your HbA1c has come down by about 18% over the past about 2 years (from 7.1 % to 5.8 %). That's a meaningful shift, and it shows your steady efforts may be paying off.",
    "Your LDL cholesterol has come down by about 15% over the past about 6 months (from 120 mg/dL to 102 mg/dL). That's a meaningful shift, and it shows your steady efforts may be paying off.",
  ],
  highlights: [
    {
      loinc_code: "4548-4",
      friendly_name: "HbA1c",
      narrative:
        "Your HbA1c has come down by about 18% over the past about 2 years (from 7.1 % to 5.8 %). That's a meaningful shift, and it shows your steady efforts may be paying off.",
      tone: "positive",
      trend_label: "dropping",
      latest_value: 5.8,
      in_reference_range: false,
      change: { start_value: 7.1, end_value: 5.8, percent_change: -18.3, months_span: 24, direction: "improving" },
    },
    {
      loinc_code: "13457-7",
      friendly_name: "LDL cholesterol",
      narrative:
        "Your LDL cholesterol has come down by about 15% over the past about 6 months (from 120 mg/dL to 102 mg/dL). That's a meaningful shift, and it shows your steady efforts may be paying off.",
      tone: "positive",
      trend_label: "dropping",
      latest_value: 102,
      in_reference_range: false,
      change: { start_value: 120, end_value: 102, percent_change: -15, months_span: 6, direction: "improving" },
    },
  ],
  encouragement:
    "Changes in HbA1c, LDL cholesterol didn't happen overnight — they reflect the care you're putting into yourself. Celebrate the progress, and bring questions to your next visit. You don't have to figure this out alone.",
  lookback_months: 24,
  generated_at: new Date().toISOString(),
};
