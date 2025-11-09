# authentification/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from authentification import views

app_name = "authentification"

urlpatterns = [
    # 🏠 Page d'accueil
    path("", views.home, name="home"),

    # 📝 Inscription + email de confirmation
    path("register/", views.register, name="register"),

    # 🔐 Connexion/Déconnexion
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),

    # 📩 Activation de compte via email
    path("activate/<uidb64>/<token>/", views.activate_account, name="activate_account"),
    path("email-sent/", views.email_sent, name="email_sent"),
    path("resend-activation/", views.resend_activation_email, name="resend_activation"),

    # 🔑 Réinitialisation de mot de passe (4 étapes)
    path("password-reset/", 
         auth_views.PasswordResetView.as_view(
             template_name='authentification/password_reset.html',
             email_template_name='authentification/password_reset_email.html',
             subject_template_name='authentification/password_reset_subject.txt',
             success_url='/authentification/password-reset/done/'
         ), 
         name="password_reset"),
    
    path("password-reset/done/", 
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentification/password_reset_done.html'
         ), 
         name="password_reset_done"),
    
    path("password-reset-confirm/<uidb64>/<token>/", 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentification/password_reset_confirm.html',
             success_url='/authentification/password-reset-complete/'
         ), 
         name="password_reset_confirm"),
    
    path("password-reset-complete/", 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentification/password_reset_complete.html'
         ), 
         name="password_reset_complete"),
]