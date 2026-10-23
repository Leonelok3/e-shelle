from django.urls import path
from . import views

app_name = "facebook_agent"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("posts/publies/", views.published_posts, name="published_posts"),
    path("posts/planifies/", views.scheduled_posts, name="scheduled_posts"),
    path("posts/creer/", views.create_scheduled_post, name="create_scheduled_post"),
    path("posts/<uuid:scheduled_post_id>/approuver/", views.approve_scheduled_draft, name="approve_draft"),
    path("logs/", views.agent_logs, name="logs"),

    # Actions
    path("publier/", views.publish_now, name="publish_now"),

    # API AJAX
    path("api/publier/", views.publish_now_ajax, name="api_publish_now"),
    path("api/apercu/", views.preview_ai_content, name="api_preview"),
    path("api/apercu/business/", views.preview_business_created, name="api_preview_business"),
    path("api/apercu/marketing/", views.preview_marketing_draft, name="api_preview_marketing"),
    path("api/brouillon/enregistrer/", views.save_approved_draft, name="api_save_draft"),
    path("api/meta/verifier/", views.verify_meta_connection, name="api_verify_meta"),
    path("api/statut/", views.api_status, name="api_status"),
]
