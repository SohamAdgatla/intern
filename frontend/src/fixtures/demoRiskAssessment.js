export const DEMO_RISK_ASSESSMENT = {
  patient_id: 1,
  risk_probability: 0.38,
  risk_percentage: 38.0,
  risk_label: "moderate",
  model_version: "bootstrap-v1.0.0",
  assessed_at: new Date().toISOString(),
  features: {
    age_years: 62,
    systolic_bp_avg: 128,
    bmi_avg: 27.2,
    fasting_glucose_avg: 102,
    hba1c_avg: 5.9,
  },
  trend_details: {},
  top_risk_drivers: [
    { feature: "bmi_slope_12m", label: "BMI trend (12 months) (rising)", impact_score: 0.18 },
    { feature: "systolic_bp_avg", label: "Average systolic blood pressure", impact_score: 0.14 },
  ],
  preventative_suggestions: [
    "Your weight trend is rising — consider discussing nutrition goals with your clinician.",
    "Track blood pressure at home and share readings with your care team.",
  ],
};
