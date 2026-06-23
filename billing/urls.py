from django.urls import path
from . import views
from . import views_affiliate
from . import views_reseller

app_name = "billing"

urlpatterns = [
    path("", views.pricing, name="pricing"),
    path("access/", views.access, name="access"),
    path("buy/", views.buy, name="buy"),
    path("redeem/", views.redeem, name="redeem"),
    path("wallet/", views.wallet_dashboard, name="wallet"),
    path("wallet/reload/", views.reload_wallet, name="reload"),
    path("generate/", views.generate_code, name="generate_code"),

    path("buy/<slug:plan_slug>/", views.buy_plan, name="buy_plan"),
    path("payment/initiate/<int:transaction_id>/", views.initiate_payment, name="initiate_payment"),

    # ✅ referral
    path("ref/<str:ref_code>/", views_affiliate.ref_redirect, name="ref_redirect"),

    # ✅ Reseller & Wallet System
    path("buy/promo/<str:promo_code>/", views_reseller.reseller_checkout_view, name="reseller_checkout"),
    path("order/success/<str:reference>/", views_reseller.order_success_view, name="order_success"),
    path("dashboard/affiliation/commandes/", views_reseller.provider_orders_view, name="provider_affiliate_orders"),
    path("dashboard/affiliation/valider/<int:order_id>/", views_reseller.validate_delivery_view, name="validate_delivery"),
    path("dashboard/portefeuille/", views_reseller.provider_wallet_view, name="provider_wallet"),

    ################################ facture des clients #############################
    path("receipts/<uuid:receipt_id>/", views.receipt_detail, name="receipt_detail"),
    path("receipts/<uuid:receipt_id>/pdf/", views.receipt_pdf, name="receipt_pdf"),
    path("contract-protection/", views.contract_protection, name="contract_protection"),
    path("receipt/<uuid:pk>/pdf/", views.receipt_pdf, name="receipt_pdf"),
]
