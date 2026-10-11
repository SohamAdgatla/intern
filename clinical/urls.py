from django.urls import path

from clinical.views.alerts import SmartAlertsView
from clinical.views.analytics import RiskAssessmentView
from clinical.views.auth import CsrfTokenView, LoginView, LogoutView, MeView, ProfileView, SignupView
from clinical.views.health_story import HealthStoryView
from clinical.views.patient_input import MeasurementTypesView, ObservationSubmitView
from clinical.views.timeline import TimelineAggregatorView

urlpatterns = [
    path("auth/csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("observations/measurement-types/", MeasurementTypesView.as_view(), name="measurement-types"),
    path("observations/submit/", ObservationSubmitView.as_view(), name="observation-submit"),
    path("timeline/", TimelineAggregatorView.as_view(), name="timeline"),
    path("health-story/", HealthStoryView.as_view(), name="health-story"),
    path("alerts/", SmartAlertsView.as_view(), name="alerts"),
    path("analytics/risk-assessment/", RiskAssessmentView.as_view(), name="risk-assessment"),
]
