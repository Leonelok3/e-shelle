"""
Administration Django standard pour edu_platform.
"""
from django.contrib import admin
from edu_platform.models import (
    EduProfile, SubscriptionPlan, AccessCode,
    DeviceBinding, Subject, ExamDocument, VideoLesson, PaymentTransaction
)


@admin.register(EduProfile)
class EduProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'country', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'phone_number']
    list_filter = ['country']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_xaf', 'duration_days', 'is_active']
    list_filter = ['plan_type', 'is_active']
    list_editable = ['is_active']


@admin.register(AccessCode)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'plan', 'status', 'activated_by', 'generated_at', 'expires_at']
    list_filter = ['status', 'plan']
    search_fields = ['code', 'activated_by__email']
    readonly_fields = ['code', 'generated_at', 'activation_count']
    raw_id_fields = ['activated_by', 'transaction']


@admin.register(DeviceBinding)
class DeviceBindingAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_label', 'first_seen', 'last_seen', 'connection_count']
    search_fields = ['user__email', 'device_label']
    readonly_fields = ['device_fingerprint', 'first_seen']


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'provider', 'amount_xaf', 'status', 'created_at']
    list_filter = ['provider', 'status']
    search_fields = ['user__email', 'phone_number', 'external_reference']
    readonly_fields = ['transaction_id', 'created_at', 'webhook_data']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject_type', 'level', 'year', 'is_premium', 'is_published', 'order']
    list_filter = ['level', 'subject_type', 'is_premium', 'is_published']
    list_editable = ['is_published', 'order']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title']


@admin.register(ExamDocument)
class ExamDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'doc_type', 'is_downloadable', 'uploaded_at']
    list_filter = ['doc_type', 'is_downloadable', 'subject__level']
    search_fields = ['title', 'subject__title']


@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'duration_minutes', 'is_preview', 'view_count', 'order']
    list_filter = ['is_preview', 'subject__level']
    list_editable = ['order']
    search_fields = ['title', 'subject__title']
