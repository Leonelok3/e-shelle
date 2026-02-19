# mediafiles/urls.py
from django.urls import path
from .views import protected_media, protected_media_probe

app_name = "mediafiles"

urlpatterns = [
    path("probe/<path:path>", protected_media_probe, name="protected_media_probe"),
    path("<path:path>", protected_media, name="protected_media"),
]
