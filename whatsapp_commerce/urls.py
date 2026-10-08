from django.urls import path

from . import views

app_name = "whatsapp_commerce"

urlpatterns = [
    path("business/<int:business_id>/", views.business_whatsapp_dashboard, name="business_dashboard"),
    path("business/<int:business_id>/connect/", views.start_business_connection, name="business_connect"),
    path("business/<int:business_id>/complete/", views.complete_business_connection, name="business_connect_complete"),
    path("business/<int:business_id>/retry/", views.retry_business_connection, name="business_connect_retry"),
    path("business/<int:business_id>/catalog/sync/", views.sync_business_catalog, name="business_catalog_sync"),
    path("business/<int:business_id>/templates/", views.business_approved_templates, name="business_approved_templates"),
    path("business/<int:business_id>/contacts/<int:contact_id>/update/", views.update_business_contact, name="business_contact_update"),
    path("business/<int:business_id>/contacts/<int:contact_id>/consent/", views.update_business_contact_consent, name="business_contact_consent"),
    path("business/<int:business_id>/contacts/<int:contact_id>/schedule/", views.schedule_business_template_follow_up, name="business_contact_schedule"),
    path("business/<int:business_id>/contacts/<int:contact_id>/scheduled/<int:scheduled_id>/cancel/", views.cancel_business_template_follow_up, name="business_contact_schedule_cancel"),
    path("business/<int:business_id>/contacts/<int:contact_id>/reply/", views.reply_to_business_contact, name="business_contact_reply"),
    path("click/<int:product_id>/", views.whatsapp_order_click, name="whatsapp_order_click"),
    path("view/<int:product_id>/", views.product_view_ping, name="product_view_ping"),
]
