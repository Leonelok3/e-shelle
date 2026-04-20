from django.contrib import admin
from .models import ConsultationRequest


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = [
        "full_name", "email", "phone", "consultation_type",
        "destination_country", "budget", "status", "created_at",
    ]
    list_filter = ["status", "consultation_type", "budget", "created_at"]
    search_fields = ["full_name", "email", "phone", "message", "destination_country"]
    readonly_fields = ["created_at", "updated_at", "user"]
    list_editable = ["status"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        ("Informations du candidat", {
            "fields": ("user", "full_name", "email", "phone", "country")
        }),
        ("Demande", {
            "fields": ("consultation_type", "destination_country", "message", "budget", "preferred_date")
        }),
        ("Suivi interne", {
            "fields": ("status", "admin_notes", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
