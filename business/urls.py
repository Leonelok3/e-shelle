from django.urls import path

from . import views

app_name = "business"

urlpatterns = [
    path("plans/", views.provider_plans, name="provider_plans"),
    path("partner/", views.partner, name="partner"),
    path("partner/dashboard/", views.partner_dashboard, name="partner_dashboard"),
    path("commercial/", views.commercial, name="commercial"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("payment/request/<int:business_id>/", views.payment_request, name="payment_request"),
    path("payment/success/<int:pk>/", views.payment_success, name="payment_success"),
    path("t/<uuid:public_id>/", views.track, name="track"),
]
