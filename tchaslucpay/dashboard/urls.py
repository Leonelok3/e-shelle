from django.urls import path

from . import views

app_name = "tchaslucpay_dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", views.admin_dashboard, name="admin"),
    path("collecteur/", views.collecteur_dashboard, name="collecteur"),
    path("collecteur/action/", views.collecteur_action, name="collecteur_action"),
    path("collecteur/transactions/nouvelle/", views.nouvelle_transaction, name="nouvelle_transaction"),
    path("rapport-agence/", views.rapport_agence, name="rapport_agence"),
    path("rapport-agence/pdf/", views.rapport_agence_pdf, name="rapport_agence_pdf"),
    path("transactions/<int:transaction_id>/recu.pdf", views.receipt_pdf, name="receipt_pdf"),
    path("client/", views.client_dashboard, name="client"),
]
