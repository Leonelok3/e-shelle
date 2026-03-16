from django.urls import path
from . import views

app_name = "resources"

urlpatterns = [
    path("", views.library, name="library"),
    path("<int:pk>/download/", views.download, name="download"),
]
