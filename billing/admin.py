# billing/admin.py
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv
import uuid

from django.utils.html import format_html
from django.urls import path

from .models import (
    SubscriptionPlan,
    Subscription,
    CreditCode,
    Transaction,
    AffiliateProfile,
    Referral,
    Commission,
    Receipt,
)

from .utils.receipt_pdf import render_receipt_pdf


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "duration_days", "price_usd", "is_active", "order", "is_popular")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active", "is_popular")
    search_fields = ("name", "slug")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "starts_at", "expires_at", "is_active")
    list_filter = ("plan", "is_active")
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "amount", "currency", "status", "payment_method", "created_at", "plan")
    list_filter = ("type", "status", "currency", "payment_method")
    search_fields = ("user__username", "user__email", "description")
    readonly_fields = ("created_at",)


@admin.register(CreditCode)
class CreditCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "plan", "is_used", "expiration_date", "used_by", "used_ip", "batch_id", "created_by_staff", "uses_count", "max_uses")
    list_filter = ("is_used", "plan")
    search_fields = ("code", "batch_id")
    readonly_fields = ("created_at", "used_at", "uses_count")
    actions = ["export_csv", "generate_10", "generate_50", "generate_100"]

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="credit_codes.csv"'
        writer = csv.writer(response)
        writer.writerow(["code", "plan", "is_used", "expiration_date", "used_by", "used_at", "used_ip", "batch_id"])

        for cc in queryset.select_related("plan", "used_by"):
            writer.writerow([
                cc.code,
                cc.plan.name,
                cc.is_used,
                cc.expiration_date,
                getattr(cc.used_by, "username", ""),
                cc.used_at,
                cc.used_ip,
                cc.batch_id,
            ])
        return response

    export_csv.short_description = "Exporter en CSV"

    def _generate_bulk(self, request, quantity):
        plan = SubscriptionPlan.objects.filter(is_active=True).order_by("duration_days").first()
        if not plan:
            self.message_user(request, "Aucun plan actif trouvé.")
            return

        batch_id = str(uuid.uuid4())[:8]
        expire_days = 90

        created = 0
        for _ in range(quantity):
            CreditCode.objects.create(
                code=CreditCode.generate_unique(),
                plan=plan,
                expiration_date=timezone.now() + timedelta(days=expire_days),
                created_by_staff=request.user if request.user.is_staff else None,
                batch_id=batch_id,
                notes=f"Batch admin {batch_id}",
                max_uses=1,
            )
            created += 1

        self.message_user(request, f"{created} codes générés (batch {batch_id}) sur le plan {plan.name}.")

    def generate_10(self, request, queryset): self._generate_bulk(request, 10)
    def generate_50(self, request, queryset): self._generate_bulk(request, 50)
    def generate_100(self, request, queryset): self._generate_bulk(request, 100)

    generate_10.short_description = "Générer 10 codes (plan par défaut)"
    generate_50.short_description = "Générer 50 codes (plan par défaut)"
    generate_100.short_description = "Générer 100 codes (plan par défaut)"


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "ref_code", "is_enabled", "created_at")
    list_filter = ("is_enabled",)
    search_fields = ("user__username", "user__email", "ref_code")
    readonly_fields = ("created_at",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("affiliate", "referred_user", "created_at")
    search_fields = ("affiliate__ref_code", "referred_user__username", "referred_user__email")
    readonly_fields = ("created_at",)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("transaction", "affiliate", "amount", "currency", "rate", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("affiliate__ref_code", "transaction__user__username", "transaction__user__email")
    readonly_fields = ("created_at",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "client_full_name", "service_name", "amount", "currency", "status", "issued_at", "pdf_link")
    search_fields = ("receipt_number", "client_full_name", "client_email", "client_phone", "transaction_id")
    list_filter = ("status", "currency", "issued_at")
    readonly_fields = ("receipt_number", "created_at")

    def pdf_link(self, obj: Receipt):
        url = f"/admin/billing/receipt/{obj.id}/pdf/"
        return format_html('<a href="{}" target="_blank">📄 PDF</a>', url)
    pdf_link.short_description = "PDF"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<uuid:pk>/pdf/",
                self.admin_site.admin_view(self.receipt_pdf_view),
                name="billing_receipt_pdf",
            ),
        ]
        return custom + urls

    def receipt_pdf_view(self, request, pk):
        receipt = Receipt.objects.get(pk=pk)
        filename = f"recu-{receipt.receipt_number}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        render_receipt_pdf(receipt, response)
        return response
