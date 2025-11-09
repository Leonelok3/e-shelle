from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("access/", views.access, name="access"),
    path("buy/", views.buy, name="buy"),
    path("redeem/", views.redeem, name="redeem"),
    path("wallet/", views.wallet_dashboard, name="wallet"),
    path("generate/", views.generate_code, name="generate_code"),  # <-- ajouté
]
