from django.urls import path
from . import views

app_name = "resources"

urlpatterns = [
    path("", views.library, name="library"),
    path("<int:pk>/", views.resource_detail, name="detail"),
    path("<int:pk>/<slug:slug>/", views.resource_detail, name="detail_slug"),
    path("<int:pk>/download/", views.download, name="download"),
]
