"""
Njangi+ — URLs
"""
from django.urls import path
from . import views

app_name = "njangi"

urlpatterns = [
    # ── Pages publiques ───────────────────────────────────────────────────────
    path("",                        views.LandingView.as_view(),         name="landing"),
    path("rejoindre/",              views.JoinGroupView.as_view(),        name="join"),
    path("groupe/creer/",           views.CreateGroupView.as_view(),      name="create_group"),
    path("groupe/<slug:slug>/",     views.GroupDetailView.as_view(),      name="group_detail"),

    # ── Dashboard membre ──────────────────────────────────────────────────────
    path("mon-espace/",                     views.MemberDashboardView.as_view(),      name="member_dashboard"),
    path("mon-espace/cotisations/",         views.MemberContributionsView.as_view(),  name="member_contributions"),
    path("mon-espace/prets/",               views.MemberLoansView.as_view(),          name="member_loans"),
    path("mon-espace/prets/demande/",       views.LoanRequestView.as_view(),          name="loan_request"),
    path("mon-espace/depots/",              views.MemberDepositsView.as_view(),       name="member_deposits"),
    path("mon-espace/depots/nouveau/",      views.DepositCreateView.as_view(),        name="deposit_create"),
    path("mon-espace/depots/<int:pk>/retirer/", views.DepositWithdrawView.as_view(), name="deposit_withdraw"),
    path("mon-espace/portefeuille/",         views.MemberWalletView.as_view(),         name="member_wallet"),
    path("mon-espace/notifications/",       views.MemberNotificationsView.as_view(),  name="member_notifications"),

    # ── Bureau (président / trésorier / secrétaire) ───────────────────────────
    path("bureau/<slug:slug>/",                         views.BureauDashboardView.as_view(),    name="bureau_dashboard"),
    path("bureau/<slug:slug>/membres/",                 views.BureauMembersView.as_view(),      name="bureau_members"),
    path("bureau/<slug:slug>/seances/",                 views.BureauSessionsView.as_view(),     name="bureau_sessions"),
    path("bureau/<slug:slug>/seances/creer/",           views.SessionCreateView.as_view(),      name="session_create"),
    path("bureau/<slug:slug>/seances/<int:pk>/",        views.SessionDetailView.as_view(),      name="session_detail"),
    path("bureau/<slug:slug>/seances/<int:pk>/ouvrir/", views.SessionOpenView.as_view(),        name="session_open"),
    path("bureau/<slug:slug>/seances/<int:pk>/cloturer/", views.SessionCloseView.as_view(),    name="session_close"),
    path("bureau/<slug:slug>/seances/<int:session_pk>/prets/<int:loan_pk>/rembourser/", views.HtmxBureauRepaymentView.as_view(), name="bureau_loan_repay"),
    path("bureau/<slug:slug>/seances/<int:session_pk>/rembourser-pret/", views.HtmxBureauRepaymentView.as_view(), name="bureau_loan_repay_quick"),
    path("bureau/<slug:slug>/prets/",                   views.BureauLoansView.as_view(),        name="bureau_loans"),
    path("bureau/<slug:slug>/prets/<int:pk>/approuver/", views.LoanApproveView.as_view(),      name="loan_approve"),
    path("bureau/<slug:slug>/prets/<int:pk>/refuser/",  views.LoanRejectView.as_view(),         name="loan_reject"),
    path("bureau/<slug:slug>/prets/<int:pk>/decaisser/", views.LoanDisburseView.as_view(),     name="loan_disburse"),
    path("bureau/<slug:slug>/fond/",                    views.FundView.as_view(),               name="fund"),
    path("bureau/<slug:slug>/interets/",                views.BureauMonthlyInterestView.as_view(),  name="bureau_monthly_interest"),
    path("bureau/<slug:slug>/interets/calculer/",       views.BureauCalculateInterestView.as_view(), name="bureau_calculate_interest"),
    path("bureau/<slug:slug>/distribution/<int:membership_pk>/", views.DistributionPreviewView.as_view(), name="distribution_preview"),

    # ── Premium ───────────────────────────────────────────────────────────────
    path("premium/", views.PremiumView.as_view(), name="premium"),

    # ── Abonnement ────────────────────────────────────────────────────────────
    path("groupe/<slug:slug>/upgrade/",   views.UpgradeView.as_view(),             name="upgrade"),
    path("groupe/<slug:slug>/souscrire/", views.SubscriptionRequestView.as_view(), name="subscription_request"),

    # ── HTMX partials ─────────────────────────────────────────────────────────
    path("htmx/cotisation/<int:pk>/payer/",   views.HtmxContributionPayView.as_view(),  name="htmx_contribution_pay"),
    path("htmx/bureau/<slug:slug>/seances/<int:session_pk>/cotisation/<int:contribution_pk>/toggle/", views.HtmxBureauContributionToggleView.as_view(), name="htmx_bureau_contribution_toggle"),
    path("htmx/bureau/<slug:slug>/membres/<int:membership_pk>/role/", views.HtmxBureauMemberRoleView.as_view(), name="htmx_bureau_member_role"),
    path("htmx/bureau/<slug:slug>/seances/<int:session_pk>/cotisation/<int:contribution_pk>/presence/", views.HtmxBureauContributionPresenceView.as_view(), name="htmx_bureau_contribution_presence"),
    path("htmx/bureau/<slug:slug>/seances/<int:session_pk>/cotisation/<int:contribution_pk>/methode/", views.HtmxBureauContributionMethodView.as_view(), name="htmx_bureau_contribution_method"),
    path("htmx/remboursement/<int:pk>/",      views.HtmxRepaymentView.as_view(),        name="htmx_repayment"),
    path("htmx/notifications/marquer-lues/",  views.HtmxMarkNotificationsRead.as_view(), name="htmx_mark_read"),

    # ── Export PDF ────────────────────────────────────────────────────────────
    path("mon-espace/releve-pdf/",            views.MemberStatementPDFView.as_view(),   name="member_statement_pdf"),
    path("bureau/<slug:slug>/fond/pdf/",      views.FundStatementPDFView.as_view(),     name="fund_statement_pdf"),

    # ── Réconciliation ────────────────────────────────────────────────────────
    path("bureau/<slug:slug>/reconciliation/", views.FundReconciliationView.as_view(),  name="fund_reconciliation"),

    # ── Audit trail ───────────────────────────────────────────────────────────
    path("bureau/<slug:slug>/audit/",          views.AuditTrailView.as_view(),          name="audit_trail"),
]
