from django.contrib.auth import views as auth_views
from django.urls import path

from .views import OwnerSignUpView

app_name = "salonhub_accounts"

urlpatterns = [
    path("connexion/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(next_page="salons:home"), name="logout"),
    path("devenir-partenaire/", OwnerSignUpView.as_view(), name="signup_owner"),
]
