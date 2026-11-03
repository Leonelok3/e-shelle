from django.contrib import admin

from .models import BusinessWhatsAppAudit, BusinessWhatsAppConnection, WhatsAppProviderReferral


@admin.register(BusinessWhatsAppAudit)
class BusinessWhatsAppAuditAdmin(admin.ModelAdmin):
	list_display = ("created_at", "connection", "contact", "event_type", "intent", "action")
	list_filter = ("event_type", "intent", "action", "created_at")
	search_fields = ("connection__business__name", "contact__phone", "contact__display_name")
	readonly_fields = (
		"connection", "contact", "event_type", "intent", "action", "details", "created_at",
	)


@admin.register(BusinessWhatsAppConnection)
class BusinessWhatsAppConnectionAdmin(admin.ModelAdmin):
	list_display = (
		"business", "display_phone_number", "status", "meta_phone_status",
		"meta_verified_name", "meta_quality_rating", "webhook_subscribed", "last_meta_sync_at",
	)
	list_filter = ("status", "meta_phone_status", "meta_quality_rating", "webhook_subscribed")
	search_fields = ("business__name", "waba_id", "phone_number_id", "display_phone_number")
	readonly_fields = (
		"business", "waba_id", "phone_number_id", "meta_business_id", "catalog_id",
		"display_phone_number", "phone_registered",
		"webhook_subscribed", "status", "last_error", "meta_phone_status",
		"meta_verified_name", "meta_quality_rating", "meta_messaging_limit", "last_meta_sync_at",
		"connected_at", "created_at", "updated_at",
	)
	exclude = ("access_token_encrypted",)


@admin.register(WhatsAppProviderReferral)
class WhatsAppProviderReferralAdmin(admin.ModelAdmin):
	list_display = ("clicked_at", "source", "status", "business", "connection")
	list_filter = ("source", "status", "clicked_at")
	search_fields = ("business__name", "connection__display_phone_number")
	readonly_fields = (
		"source", "status", "business", "connection",
		"clicked_at", "signup_started_at", "connected_at",
	)
