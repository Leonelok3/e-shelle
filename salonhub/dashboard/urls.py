from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("rdv/<int:pk>/statut/", views.update_appointment_status, name="update_appointment_status"),
    path("salons/nouveau/", views.salon_create, name="salon_create"),
    path("salons/<int:pk>/modifier/", views.salon_edit, name="salon_edit"),
    path("salons/<int:salon_id>/prestations/", views.salon_services, name="salon_services"),
    path("prestations/<int:pk>/supprimer/", views.service_delete, name="service_delete"),
]
