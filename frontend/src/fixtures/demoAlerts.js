export const DEMO_ALERTS = {
  patient_id: 1,
  generated_at: new Date().toISOString(),
  alert_count: 2,
  alerts: [
    {
      id: "hba1c-improving",
      severity: "info",
      category: "labs",
      title: "Blood sugar control is improving",
      message:
        "Your HbA1c has been trending down — that's encouraging progress. Whatever you're doing, keep the conversation going with your care team.",
      action_hint: "Celebrate small wins and stay consistent.",
      detected_at: new Date().toISOString(),
      metadata: { trend: "dropping", latest: 5.8 },
    },
    {
      id: "adherence-pct-1",
      severity: "watch",
      category: "medication",
      title: "Medication routine could use a boost",
      message:
        "Your reported adherence for Metformin is around 85%. Small reminders can make a big difference.",
      action_hint: "Link your medication to a daily habit like breakfast.",
      detected_at: new Date().toISOString(),
      metadata: { medication: "Metformin", adherence_percentage: 85 },
    },
  ],
};
