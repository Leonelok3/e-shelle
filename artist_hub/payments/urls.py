"""
artist_hub/payments/urls.py — Définition des routes du module payments.
Namespace : 'artist_hub:payments'
"""
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # Webhooks
    path("webhook/", views.webhook_view, name="webhook"),
    path("webhook/<str:provider_name>/", views.webhook_view, name="webhook_provider"),
    # API Polling
    path("api/status/<str:reference>/", views.payment_status_api, name="status_api"),
    # Pages de parcours
    path("waiting/<str:reference>/", views.PaymentWaitingView.as_view(), name="waiting"),
    path("success/<str:reference>/", views.PaymentSuccessView.as_view(), name="success"),
    path("failed/<str:reference>/", views.PaymentFailedView.as_view(), name="failed"),
    # Simulateur local (Mock)
    path("mock/<str:reference>/", views.MockPaymentSimulateView.as_view(), name="mock_simulate"),
]
