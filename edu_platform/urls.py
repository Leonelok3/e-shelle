"""
URLs de l'application EduCam Pro.
Toutes préfixées /edu/ (définies dans le projet hôte).
Namespace : edu
"""
from django.urls import path
from edu_platform.views.auth_views import (
    EduLandingView, EduRegisterView, EduLoginView, EduLogoutView,
    ActivateCodeView, DeviceBlockedView,
)
from edu_platform.views.dashboard_views import StudentDashboardView, ProfileView
from edu_platform.views.content_views import (
    SubjectListView, SubjectDetailView,
    DocumentView, SecureDocumentServeView, VideoPlayerView,
)
from edu_platform.views.subscription_views import (
    PlansView, PaymentView, PaymentPendingView, PaymentSuccessView,
    SubscriptionStatusView, RenewSubscriptionView, PaymentReturnView,
)
from edu_platform.views.admin_views import (
    EduAdminDashboardView, EduUserListView, AccessCodeListView,
    ContentManagerView, TransactionListView, DeviceListView,
    ExportSubscribersView,
)
from edu_platform.views.api_views import (
    PaymentStatusAPIView, DeviceCheckAPIView,
    OrangeMoneyWebhookView, MTNMoMoWebhookView,
)

app_name = 'edu'

urlpatterns = [

    # ── PAGES PUBLIQUES ──────────────────────────────────────────────
    path('', EduLandingView.as_view(), name='landing'),
    path('plans/', PlansView.as_view(), name='plans'),

    # ── AUTHENTIFICATION ─────────────────────────────────────────────
    path('login/', EduLoginView.as_view(), name='login'),
    path('logout/', EduLogoutView.as_view(), name='logout'),
    path('register/', EduRegisterView.as_view(), name='register'),
    path('activate/', ActivateCodeView.as_view(), name='activate_code'),
    path('device-blocked/', DeviceBlockedView.as_view(), name='device_blocked'),

    # ── ESPACE ÉTUDIANT ──────────────────────────────────────────────
    path('dashboard/', StudentDashboardView.as_view(), name='dashboard'),
    path('profile/', ProfileView.as_view(), name='profile'),

    # ── CONTENU ──────────────────────────────────────────────────────
    path('subjects/', SubjectListView.as_view(), name='subject_list'),
    path('subjects/<slug:slug>/', SubjectDetailView.as_view(), name='subject_detail'),
    path('documents/<int:pk>/', DocumentView.as_view(), name='document_view'),
    path('documents/<int:pk>/serve/', SecureDocumentServeView.as_view(), name='document_serve'),
    path('videos/<int:pk>/', VideoPlayerView.as_view(), name='video_player'),

    # ── ABONNEMENT & PAIEMENT ────────────────────────────────────────
    path('payment/<int:plan_id>/', PaymentView.as_view(), name='payment'),
    path('payment/pending/<uuid:tx_id>/', PaymentPendingView.as_view(), name='payment_pending'),
    path('payment/success/<uuid:tx_id>/', PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/return/<str:provider>/<uuid:tx_id>/', PaymentReturnView.as_view(), name='payment_return'),
    path('subscription/', SubscriptionStatusView.as_view(), name='subscription_status'),
    path('renew/', RenewSubscriptionView.as_view(), name='renew'),

    # ── ADMIN CUSTOM ─────────────────────────────────────────────────
    path('admin/', EduAdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/users/', EduUserListView.as_view(), name='admin_users'),
    path('admin/codes/', AccessCodeListView.as_view(), name='admin_codes'),
    path('admin/content/', ContentManagerView.as_view(), name='admin_content'),
    path('admin/transactions/', TransactionListView.as_view(), name='admin_transactions'),
    path('admin/devices/', DeviceListView.as_view(), name='admin_devices'),
    path('admin/export/subscribers/', ExportSubscribersView.as_view(), name='export_subscribers'),

    # ── API INTERNES ─────────────────────────────────────────────────
    path('api/payment-status/<uuid:tx_id>/', PaymentStatusAPIView.as_view(), name='api_payment_status'),
    path('api/device-check/', DeviceCheckAPIView.as_view(), name='api_device_check'),

    # ── WEBHOOKS (CSRF-exempt, sécurisés par HMAC) ──────────────────
    path('webhooks/orange-money/', OrangeMoneyWebhookView.as_view(), name='webhook_orange'),
    path('webhooks/mtn-momo/', MTNMoMoWebhookView.as_view(), name='webhook_mtn'),
]
