# billing/urls.py
from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # Pages principales
    path("", views.pricing, name="pricing"),
    path("access/", views.access, name="access"),
    path("buy/", views.buy, name="buy"),
    path("redeem/", views.redeem, name="redeem"),
    path("wallet/", views.wallet_dashboard, name="wallet"),
    path("generate/", views.generate_code, name="generate_code"),
    
    # Nouveau : achat de plan
    path("buy/<slug:plan_slug>/", views.buy_plan, name="buy_plan"),
    path("payment/initiate/<int:transaction_id>/", views.initiate_payment, name="initiate_payment"),
]