from django.urls import path

from . import views
from . import business_campaigns

app_name = "whatsapp_commerce"

urlpatterns = [
    path("provider-referral/", views.provider_referral_click, name="provider_referral_click"),
    path("campaigns/", business_campaigns.campaigns_home, name="campaigns_home"),
    path("campaigns/<int:business_id>/", business_campaigns.business_campaigns, name="business_campaigns"),
    path(
        "campaigns/<int:business_id>/import/",
        business_campaigns.import_business_campaign_contacts,
        name="business_campaign_import",
    ),
    path(
        "campaigns/<int:business_id>/create/",
        business_campaigns.create_business_campaign,
        name="business_campaign_create",
    ),
    path(
        "campaigns/<int:business_id>/<int:campaign_id>/",
        business_campaigns.business_campaign_detail,
        name="business_campaign_detail",
    ),
    path(
        "campaigns/<int:business_id>/<int:campaign_id>/launch/",
        business_campaigns.launch_business_campaign,
        name="business_campaign_launch",
    ),
    path("tech-provider/", views.tech_provider_dashboard, name="tech_provider_dashboard"),
    path("tech-provider/<int:connection_id>/refresh/", views.tech_provider_refresh, name="tech_provider_refresh"),
    path("tech-provider/<int:connection_id>/resubscribe/", views.tech_provider_resubscribe, name="tech_provider_resubscribe"),
    path("tech-provider/<int:connection_id>/deregister/", views.tech_provider_deregister, name="tech_provider_deregister"),
    path("inbox/", views.business_whatsapp_inbox, name="inbox"),
    path("business/<int:business_id>/", views.business_whatsapp_dashboard, name="business_dashboard"),
    path("business/<int:business_id>/connect/", views.start_business_connection, name="business_connect"),
    path(
        "business/<int:business_id>/sync-existing/",
        views.sync_existing_waba_for_business,
        name="business_sync_existing_waba",
    ),
    path("business/<int:business_id>/complete/", views.complete_business_connection, name="business_connect_complete"),
    path("business/<int:business_id>/retry/", views.retry_business_connection, name="business_connect_retry"),
    path("business/<int:business_id>/catalog/sync/", views.sync_business_catalog, name="business_catalog_sync"),
    path("business/<int:business_id>/agent/configure/", views.configure_sales_agent, name="business_agent_configure"),
    path("business/<int:business_id>/draft-orders/<int:draft_id>/", views.update_whatsapp_draft_order, name="draft_order_update"),
    path("business/<int:business_id>/templates/", views.business_approved_templates, name="business_approved_templates"),
    path("business/<int:business_id>/contacts/<int:contact_id>/update/", views.update_business_contact, name="business_contact_update"),
    path("business/<int:business_id>/contacts/<int:contact_id>/consent/", views.update_business_contact_consent, name="business_contact_consent"),
    path("business/<int:business_id>/contacts/<int:contact_id>/schedule/", views.schedule_business_template_follow_up, name="business_contact_schedule"),
    path("business/<int:business_id>/contacts/<int:contact_id>/scheduled/<int:scheduled_id>/cancel/", views.cancel_business_template_follow_up, name="business_contact_schedule_cancel"),
    path("business/<int:business_id>/contacts/<int:contact_id>/reply/", views.reply_to_business_contact, name="business_contact_reply"),
    path("click/<int:product_id>/", views.whatsapp_order_click, name="whatsapp_order_click"),
    path("view/<int:product_id>/", views.product_view_ping, name="product_view_ping"),
]
