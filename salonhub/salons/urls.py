from django.urls import path
from . import views

app_name = "salons"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("s/<slug:slug>/", views.SalonDetailView.as_view(), name="detail"),
]
