from django.contrib import admin
from django.utils.html import format_html
from .models import OpportunityCategory, Opportunity, LiveSession, OCDPackage, Slot, Booking


@admin.register(OpportunityCategory)
class OpportunityCategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "city", "country", "min_capital_display", "estimated_roi", "status", "is_featured", "created_at")
    list_filter = ("status", "category", "is_featured", "country")
    search_fields = ("title", "summary", "city", "full_description")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("status", "is_featured")

    def min_capital_display(self, obj):
        return f"{int(obj.min_capital_xaf):,} FCFA".replace(",", " ")
    min_capital_display.short_description = "Capital Min."


class SlotInline(admin.TabularInline):
    model = Slot
    extra = 1
    fields = ("title", "expert_name", "start_time", "end_time", "capacity", "booked_count", "price_xaf", "is_active")


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "speaker_name", "scheduled_at", "access_tier", "ticket_price_display", "is_live_now", "is_completed")
    list_filter = ("is_live_now", "is_completed", "access_tier", "stream_provider")
    search_fields = ("title", "subtitle", "speaker_name", "description")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_live_now", "is_completed")
    inlines = [SlotInline]

    def ticket_price_display(self, obj):
        return f"{int(obj.ticket_price_xaf):,} FCFA".replace(",", " ")
    ticket_price_display.short_description = "Prix Billet"


@admin.register(OCDPackage)
class OCDPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_display", "duration_days", "can_access_all_lives", "is_popular", "is_active", "order")
    list_filter = ("is_active", "is_popular")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_popular", "is_active", "order")

    def price_display(self, obj):
        return f"{int(obj.price_xaf):,} FCFA".replace(",", " ")
    price_display.short_description = "Prix"


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("title", "expert_name", "start_time", "end_time", "capacity", "booked_count", "price_xaf", "is_active")
    list_filter = ("is_active", "start_time")
    search_fields = ("title", "expert_name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("ticket_code", "user", "target_display", "amount_paid_display", "status_badge", "whatsapp_number", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("ticket_code", "user__username", "user__email", "whatsapp_number", "transaction_ref")
    readonly_fields = ("ticket_code", "created_at", "updated_at")

    def target_display(self, obj):
        if obj.session:
            return f"Session: {obj.session.title[:30]}"
        if obj.package:
            return f"Pass: {obj.package.name}"
        if obj.slot:
            return f"Créneau: {obj.slot.title[:30]}"
        return "Général"
    target_display.short_description = "Prestation"

    def amount_paid_display(self, obj):
        return f"{int(obj.amount_paid):,} FCFA".replace(",", " ")
    amount_paid_display.short_description = "Montant"

    def status_badge(self, obj):
        colors = {
            "CONFIRMED": "#10B981",
            "PENDING": "#F59E0B",
            "CANCELLED": "#EF4444",
        }
        return format_html(
            '<span style="background:{};color:#FFF;padding:3px 8px;border-radius:6px;font-weight:700;font-size:0.75rem">{}</span>',
            colors.get(obj.status, "#6B7280"),
            obj.get_status_display(),
        )
    status_badge.short_description = "Statut"

