"""
Njangi+ — Administration Django
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Group, Membership,
    Session, Contribution,
    FundDeposit, FundTransaction,
    Loan, LoanRepayment,
    Notification, Document,
    MonthlyGroupInterest, MemberMonthlyStatement,
    SubscriptionRequest,
)


# ── Groupe & Membres ──────────────────────────────────────────────────────────

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ("user", "role", "hand_order", "is_active", "total_contributed", "total_received")
    readonly_fields = ("total_contributed", "total_received")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display  = ("name", "status", "member_count", "frequency", "contribution_amount", "current_cycle", "created_at")
    list_filter   = ("status", "frequency", "meeting_type")
    search_fields = ("name", "invite_code")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("fund_balance", "fund_available_for_loans", "invite_code")
    inlines = [MembershipInline]

    fieldsets = (
        ("Identité", {"fields": ("name", "slug", "invite_code", "description", "logo", "created_by")}),
        ("Configuration", {"fields": (
            "meeting_type", "frequency", "contribution_amount", "max_members",
            "fund_loan_rate", "fund_deposit_rate", "penalty_per_day",
            "max_loan_multiplier", "fund_reserve_pct", "require_guarantor",
        )}),
        ("Calendrier", {"fields": ("start_date", "next_session_date", "current_cycle")}),
        ("État", {"fields": ("status",)}),
        ("Abonnement", {"fields": ("plan", "plan_expires_at", "plan_note")}),
        ("Fond commun (calculé)", {"fields": ("fund_balance", "fund_available_for_loans"), "classes": ("collapse",)}),
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display  = ("user", "group", "role", "hand_order", "is_active", "total_contributed", "total_received")
    list_filter   = ("role", "is_active", "group")
    search_fields = ("user__username", "user__email", "group__name")
    raw_id_fields = ("user", "group")


# ── Séances & Cotisations ─────────────────────────────────────────────────────

class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 0
    fields = ("membership", "amount_due", "amount_paid", "status", "payment_method", "paid_at")
    readonly_fields = ("paid_at",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display  = ("__str__", "date", "status", "total_collected", "hand_amount", "attendance_rate")
    list_filter   = ("status", "group", "cycle")
    search_fields = ("group__name",)
    readonly_fields = ("total_collected", "hand_amount", "penalties_collected", "opened_at", "closed_at", "attendance_rate")
    inlines = [ContributionInline]


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display  = ("membership", "session", "amount_due", "amount_paid", "status", "is_late", "paid_at")
    list_filter   = ("status", "is_late", "payment_method")
    search_fields = ("membership__user__username", "transaction_ref")
    readonly_fields = ("paid_at",)


# ── Fond commun ───────────────────────────────────────────────────────────────

@admin.register(FundDeposit)
class FundDepositAdmin(admin.ModelAdmin):
    list_display  = ("membership", "amount", "interest_rate", "status", "deposited_at", "monthly_interest_potential")
    list_filter   = ("status",)
    search_fields = ("membership__user__username",)
    readonly_fields = ("deposited_at", "interest_earned", "withdrawn_at", "withdrawn_amount", "current_interest", "monthly_interest_potential")


@admin.register(FundTransaction)
class FundTransactionAdmin(admin.ModelAdmin):
    list_display  = ("group", "type", "amount", "signed_amount", "balance_after", "created_at", "is_credit_badge")
    list_filter   = ("type", "group")
    search_fields = ("description", "group__name")
    readonly_fields = ("signed_amount", "created_at")

    def is_credit_badge(self, obj):
        color = "green" if obj.is_credit else "red"
        label = "+" if obj.is_credit else "−"
        return format_html('<span style="color:{};font-weight:bold">{}</span>', color, label)
    is_credit_badge.short_description = "Sens"


# ── Prêts ─────────────────────────────────────────────────────────────────────

class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    fields = ("amount_paid", "principal_part", "interest_part", "balance_after", "payment_method", "paid_at")
    readonly_fields = ("principal_part", "interest_part", "balance_after", "paid_at")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display  = ("membership", "amount_approved", "interest_rate", "duration_months", "status", "due_date", "repayment_progress_pct")
    list_filter   = ("status",)
    search_fields = ("membership__user__username",)
    readonly_fields = ("requested_at", "approved_at", "disbursed_at", "total_interest", "total_due", "total_repaid", "balance_remaining", "repayment_progress_pct")
    inlines = [LoanRepaymentInline]

    fieldsets = (
        ("Demande", {"fields": ("membership", "guarantor", "amount_requested", "purpose", "requested_at")}),
        ("Décision", {"fields": ("status", "amount_approved", "interest_rate", "duration_months", "reviewed_by", "approved_at", "rejection_reason")}),
        ("Décaissement", {"fields": ("disbursed_at", "due_date", "payment_method", "transaction_ref")}),
        ("Finances", {"fields": ("total_interest", "total_due", "total_repaid", "balance_remaining", "repayment_progress_pct")}),
    )


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display  = ("loan", "amount_paid", "principal_part", "interest_part", "balance_after", "payment_method", "paid_at")
    list_filter   = ("payment_method",)
    search_fields = ("loan__membership__user__username", "transaction_ref")
    readonly_fields = ("paid_at", "principal_part", "interest_part", "balance_after")


# ── Notifications & Documents ─────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("membership", "type", "title", "is_read", "created_at")
    list_filter   = ("type", "is_read")
    search_fields = ("membership__user__username", "title")
    readonly_fields = ("created_at", "read_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ("group", "type", "title", "uploaded_by", "created_at")
    list_filter   = ("type", "group")
    search_fields = ("title", "group__name")


# ── Wallet — Intérêts mensuels ────────────────────────────────────────────────

class MemberMonthlyStatementInline(admin.TabularInline):
    model = MemberMonthlyStatement
    extra = 0
    fields = ("membership", "deposit_balance", "pool_share_pct", "interest_earned", "cumulative_interest", "wallet_balance")
    readonly_fields = ("membership", "deposit_balance", "pool_share_pct", "interest_earned", "cumulative_interest", "wallet_balance")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MonthlyGroupInterest)
class MonthlyGroupInterestAdmin(admin.ModelAdmin):
    list_display  = ("group", "period_label", "formatted_pool", "nb_active_loans", "nb_depositors", "formatted_interest", "utilization_rate_badge", "is_calculated", "calculated_at")
    list_filter   = ("group", "is_calculated", "year")
    search_fields = ("group__name",)
    readonly_fields = ("calculated_at", "utilization_rate", "formatted_interest", "formatted_pool")
    inlines       = [MemberMonthlyStatementInline]
    ordering      = ("-year", "-month")

    fieldsets = (
        ("Période", {"fields": ("group", "year", "month")}),
        ("Snapshot financier", {"fields": ("total_pool", "total_loans_outstanding", "total_interest_generated", "nb_active_loans", "nb_depositors")}),
        ("Statut", {"fields": ("is_calculated", "calculated_at")}),
    )

    actions = ["recalculate_selected"]

    def utilization_rate_badge(self, obj):
        rate = obj.utilization_rate
        color = "#22c55e" if rate < 60 else "#f59e0b" if rate < 85 else "#ef4444"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">{} %</span>',
            color, rate
        )
    utilization_rate_badge.short_description = "Utilisation pool"

    @admin.action(description="Recalculer les intérêts pour les mois sélectionnés")
    def recalculate_selected(self, request, queryset):
        from njangi.services import InterestCalculationService
        count = 0
        for record in queryset:
            try:
                InterestCalculationService.calculate_month(record.group, record.year, record.month)
                count += 1
            except Exception as exc:
                self.message_user(request, f"Erreur {record}: {exc}", level="error")
        self.message_user(request, f"{count} mois recalculé(s) avec succès.")


@admin.register(MemberMonthlyStatement)
class MemberMonthlyStatementAdmin(admin.ModelAdmin):
    list_display  = ("membership", "period_label", "formatted_deposit", "pool_share_pct", "formatted_interest", "formatted_cumulative", "formatted_wallet")
    list_filter   = ("monthly_record__group", "monthly_record__year")
    search_fields = ("membership__user__username", "membership__group__name")
    readonly_fields = ("period_label", "formatted_interest", "formatted_deposit", "formatted_cumulative", "formatted_wallet")


# ── Abonnements ───────────────────────────────────────────────────────────────

@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display  = ("group", "plan_badge", "duration_months", "amount_paid", "payment_method", "payment_date", "status_badge", "created_at")
    list_filter   = ("status", "plan", "payment_method")
    search_fields = ("group__name", "requested_by__username", "phone_used", "payment_ref")
    readonly_fields = ("created_at", "processed_at", "processed_by", "amount_expected")
    actions = ["approve_requests", "reject_requests"]

    fieldsets = (
        ("Groupe & Plan", {"fields": ("group", "requested_by", "plan", "duration_months", "amount_expected")}),
        ("Paiement déclaré", {"fields": ("payment_method", "phone_used", "payment_date", "payment_ref", "amount_paid", "notes")}),
        ("Traitement", {"fields": ("status", "processed_by", "processed_at", "rejection_reason")}),
    )

    def plan_badge(self, obj):
        colors = {"standard": "#1B6CA8", "pro": "#7c3aed", "association": "#F5A623"}
        color = colors.get(obj.plan, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_plan_display().split(" —")[0]
        )
    plan_badge.short_description = "Plan"

    def status_badge(self, obj):
        colors = {"pending": "#f59e0b", "approved": "#22c55e", "rejected": "#ef4444"}
        labels = {"pending": "⏳ En attente", "approved": "✓ Approuvé", "rejected": "✗ Refusé"}
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, labels.get(obj.status, obj.status)
        )
    status_badge.short_description = "Statut"

    @admin.action(description="✅ Approuver et activer le plan")
    def approve_requests(self, request, queryset):
        count = 0
        for sub in queryset.filter(status="pending"):
            sub.approve(request.user)
            count += 1
        self.message_user(request, f"{count} abonnement(s) activé(s) avec succès.")

    @admin.action(description="❌ Refuser les demandes sélectionnées")
    def reject_requests(self, request, queryset):
        count = queryset.filter(status="pending").update(
            status="rejected",
            processed_by=request.user,
            processed_at=__import__("django.utils.timezone", fromlist=["timezone"]).timezone.now()
        )
        self.message_user(request, f"{count} demande(s) refusée(s).", level="warning")
