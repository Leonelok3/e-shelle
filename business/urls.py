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
    path("partner/packs/", views.business_key_packs, name="business_key_packs"),
    path("partner/comment-gagner/", views.business_key_how_to_earn, name="business_key_how_to_earn"),
    path("partner/recrutement/", views.business_key_recruit, name="business_key_recruit"),
    path("partner/academy/", views.business_key_academy, name="business_key_academy"),
    path("partner/kit/", views.business_key_kit, name="business_key_kit"),
    path("partner/catalogue/", views.catalogue_commissions, name="catalogue_commissions"),
    path("partner/crm/", views.business_key_crm, name="business_key_crm"),
    path("partner/crm/opportunites/", views.business_key_crm_opportunities, name="business_key_crm_opportunities"),
    path("partner/crm/campagne/", views.business_key_crm_create_campaign, name="business_key_crm_create_campaign"),
    path("partner/crm/<int:pk>/demo/", views.business_key_crm_demo, name="business_key_crm_demo"),
    path("partner/crm/<int:pk>/update/", views.business_key_crm_update, name="business_key_crm_update"),
    path("partner/payment-request/", views.business_key_payment_request, name="business_key_payment_request"),
    path("partner/admin/", views.business_key_admin, name="business_key_admin"),
    path("partner/admin/<int:pk>/<str:action>/", views.business_key_admin_action, name="business_key_admin_action"),
    path("partner/dashboard/", views.partner_dashboard, name="partner_dashboard"),
    path("commercial/", views.commercial, name="commercial"),
    path("commercial/admin-dashboard/", views.commercial_admin_dashboard, name="commercial_admin_dashboard"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("catalogue/<int:business_id>/", views.catalog_manage, name="catalog_manage"),
    path("catalogue/<int:business_id>/item/<int:item_id>/", views.catalog_item_action, name="catalog_item_action"),
    path("@<slug:public_slug>/", views.public_profile, name="public_profile"),
    path("report/<int:business_id>/", views.performance_report, name="performance_report"),
    path("report/<int:business_id>/pdf/", views.performance_report_pdf, name="performance_report_pdf"),
    path("payment/request/<int:business_id>/", views.payment_request, name="payment_request"),
    path("payment/success/<int:pk>/", views.payment_success, name="payment_success"),
    path("t/<uuid:public_id>/", views.track, name="track"),
    path("go/<int:business_id>/<str:event_type>/", views.go_business, name="go_business"),
    path("slide/<int:slide_id>/", views.go_slide, name="go_slide"),
]
