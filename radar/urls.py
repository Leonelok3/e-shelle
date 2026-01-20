from django.urls import path
from .views import health

app_name = "radar"

urlpatterns = [
    path("", health, name="health"),
]
