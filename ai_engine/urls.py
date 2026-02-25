from django.urls import path

from ai_engine.api_views import generate_content_api

urlpatterns = [
    path("generate/", generate_content_api, name="ai_generate_content"),
]