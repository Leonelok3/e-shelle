from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "authentification"

urlpatterns = [

    # =========================
    # AUTH CORE
    # =========================
    path("", views.home, name="home"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.register, name="register"),
    path("email-sent/", views.email_sent, name="email_sent"),
    path(
        "activate/<uidb64>/<token>/",
        views.activate_account,
        name="activate_account",
    ),

    # =========================
    # RESEND ACTIVATION
    # =========================
    path(
        "resend-activation/",
        views.resend_activation,
        name="resend_activation",
    ),

    path(
    "resend-activation/",
    views.resend_activation_email,
    name="resend_activation_email"
),


    # =========================
    # PASSWORD RESET (ULTRA PREMIUM – CLEAN)
    # =========================
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
    template_name="authentification/password_reset.html",
    email_template_name="authentification/email/password_reset_email.html",
    subject_template_name="authentification/email/password_reset_subject.txt",
    success_url="/authentification/password-reset/done/",
),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="authentification/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    path(
    "reset/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="authentification/password_reset_confirm.html",
        success_url="/authentification/reset/done/",
    ),
    name="password_reset_confirm",
),


    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="authentification/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
