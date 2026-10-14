from django.contrib import admin

from .models import BusinessWhatsAppAudit


@admin.register(BusinessWhatsAppAudit)
class BusinessWhatsAppAuditAdmin(admin.ModelAdmin):
	list_display = ("created_at", "connection", "contact", "event_type", "intent", "action")
	list_filter = ("event_type", "intent", "action", "created_at")
	search_fields = ("connection__business__name", "contact__phone", "contact__display_name")
	readonly_fields = (
		"connection", "contact", "event_type", "intent", "action", "details", "created_at",
	)
