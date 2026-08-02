from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("rdv/<int:pk>/statut/", views.update_appointment_status, name="update_appointment_status"),
]
