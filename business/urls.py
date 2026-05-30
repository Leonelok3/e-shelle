from django.urls import path

from . import views
from . import seo_geo

app_name = "business"

urlpatterns = [
    path("solutions/", views.solutions, name="solutions"),
    path("local/", seo_geo.geo_index, name="geo_index"),
    path("local/<slug:city_slug>/<slug:service_slug>/", seo_geo.geo_landing, name="geo_landing"),
    path("plans/", views.provider_plans, name="provider_plans"),
    path("application-personnalisee/", views.custom_app_offer, name="custom_app_offer"),
    path("partner/", views.partner, name="partner"),
    path("partner/dashboard/", views.partner_dashboard, name="partner_dashboard"),
    path("commercial/", views.commercial, name="commercial"),
    path("commercial/admin-dashboard/", views.commercial_admin_dashboard, name="commercial_admin_dashboard"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("@<slug:public_slug>/", views.public_profile, name="public_profile"),
    path("report/<int:business_id>/", views.performance_report, name="performance_report"),
    path("report/<int:business_id>/pdf/", views.performance_report_pdf, name="performance_report_pdf"),
    path("payment/request/<int:business_id>/", views.payment_request, name="payment_request"),
    path("payment/success/<int:pk>/", views.payment_success, name="payment_success"),
    path("t/<uuid:public_id>/", views.track, name="track"),
    path("go/<int:business_id>/<str:event_type>/", views.go_business, name="go_business"),
    path("slide/<int:slide_id>/", views.go_slide, name="go_slide"),
]
