from django.urls import path, include
from django.contrib import admin
urlpatterns = [path("admin/", admin.site.urls), path("artist-hub/", include("artist_hub.urls", namespace="artist_hub"))]
