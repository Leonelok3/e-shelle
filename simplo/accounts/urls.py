from django.urls import path

from . import views

app_name = "simplo_accounts"

urlpatterns = [
    path("connexion/", views.login_view, name="login"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("prestataire/", views.prestataire_dashboard, name="prestataire_dashboard"),
    path("prestataire/statut/", views.toggle_status, name="toggle_status"),
]
