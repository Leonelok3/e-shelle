"""
Administration Django pour edu_platform.
Upload direct de PDF / Vidéo / Audio depuis l'admin.
"""
from django.contrib import admin
from django.utils.html import format_html
from edu_platform.models import (
    EduProfile, SubscriptionPlan, AccessCode,
    DeviceBinding, Subject, ExamDocument, VideoLesson,
    AudioResource, PaymentTransaction,
    DailyChallenge, ChallengeSubmission, SubmissionFile,
)


@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "level", "status", "starts_at", "ends_at", "submission_count", "challenge_link")
    list_filter = ("status", "level", "subject")
    search_fields = ("title", "instructions", "answer_key")
    readonly_fields = ("public_token", "created_by", "created_at", "challenge_link", "qr_preview")
    autocomplete_fields = ("subject",)
    fieldsets = (
        ("Challenge", {"fields": ("title", "instructions", "subject", "level", "exercise_file", "status", "starts_at", "ends_at")} ),
        ("Correction IA", {"fields": ("answer_key", "rubric", "total_points")} ),
        ("Partage", {"fields": ("public_token", "challenge_link", "qr_preview", "leaderboard_enabled")} ),
        ("Création", {"fields": ("created_by", "created_at")} ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def submission_count(self, obj):
        return obj.submissions.count()
    submission_count.short_description = "Copies"

    def challenge_link(self, obj):
        if not obj.pk:
            return "Enregistre le challenge pour créer le lien."
        from django.urls import reverse
        return format_html('<a href="{}" target="_blank">Ouvrir le formulaire élève</a>', reverse("edu:challenge_public", args=[obj.public_token]))
    challenge_link.short_description = "Lien élève"

    def qr_preview(self, obj):
        if not obj.pk:
            return ""
        from django.urls import reverse
        return format_html('<img src="{}" width="180" height="180" alt="QR code"><br><a href="{}" download>Enregistrer le QR code</a>', reverse("edu:challenge_qr", args=[obj.public_token]), reverse("edu:challenge_qr", args=[obj.public_token]))
    qr_preview.short_description = "QR code"


class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    extra = 0
    can_delete = False
    fields = ("original_name", "mime_type", "size_bytes", "secure_download")
    readonly_fields = fields

    def secure_download(self, obj):
        if not obj.pk:
            return ""
        from django.urls import reverse
        url = reverse("edu:challenge_submission_file", args=[obj.submission_id, obj.pk])
        return format_html('<a href="{}">Télécharger la copie</a>', url)
    secure_download.short_description = "Fichier"


@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = ("student_name", "challenge", "student_class", "score", "status", "submitted_at")
    list_filter = ("status", "challenge", "submitted_at")
    search_fields = ("student_name", "student_class", "challenge__title")
    readonly_fields = ("access_token", "submitted_at", "graded_at", "student")
    fields = ("challenge", "student", "student_name", "student_class", "score", "status", "feedback", "error_message", "show_name_on_leaderboard", "access_token", "submitted_at", "graded_at", "reviewed_by", "reviewed_at")
    inlines = (SubmissionFileInline,)

    def save_model(self, request, obj, form, change):
        if obj.status == ChallengeSubmission.Status.REVIEWED:
            obj.reviewed_by = request.user
            from django.utils import timezone
            obj.reviewed_at = timezone.now()
            if obj.feedback:
                obj.feedback = {**obj.feedback, "provisional": False}
        super().save_model(request, obj, form, change)


# ──────────────────────────────────────────────────────────────────────────────
# Inlines pour Subject (upload direct depuis la fiche matière)
# ──────────────────────────────────────────────────────────────────────────────

class ExamDocumentInline(admin.TabularInline):
    model = ExamDocument
    extra = 1
    fields = ['doc_type', 'title', 'file', 'is_downloadable', 'preview_pages']
    show_change_link = True


class VideoLessonInline(admin.TabularInline):
    model = VideoLesson
    extra = 1
    fields = ['title', 'video_url', 'video_file', 'duration_minutes', 'is_preview', 'order']
    show_change_link = True


class AudioResourceInline(admin.TabularInline):
    model = AudioResource
    extra = 1
    fields = ['audio_type', 'title', 'audio_file', 'duration_minutes', 'is_preview', 'order']
    show_change_link = True


# ──────────────────────────────────────────────────────────────────────────────
# Subject — page centrale pour tout le contenu
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'section_badge', 'level', 'subject_type',
        'year', 'doc_count', 'video_count', 'audio_count_display',
        'is_premium', 'is_published', 'order',
    ]
    list_filter = ['section', 'level', 'subject_type', 'is_premium', 'is_published']
    list_editable = ['is_published', 'order']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'description']
    filter_horizontal = ['allowed_plans']
    inlines = [ExamDocumentInline, VideoLessonInline, AudioResourceInline]

    fieldsets = (
        ('Identification', {
            'fields': ('title', 'slug', 'section', 'level', 'subject_type', 'year'),
        }),
        ('Contenu', {
            'fields': ('description', 'thumbnail'),
        }),
        ('Accès', {
            'fields': ('is_premium', 'is_published', 'order', 'allowed_plans'),
        }),
    )

    def section_badge(self, obj):
        colors = {
            'francophone': '#27ae60',
            'technique':   '#e67e22',
            'anglophone':  '#2980b9',
        }
        color = colors.get(obj.section, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_section_display()
        )
    section_badge.short_description = 'Section'

    def doc_count(self, obj):
        n = obj.document_count
        return format_html('<b>{}</b> PDF', n) if n else '—'
    doc_count.short_description = 'Docs'

    def video_count(self, obj):
        n = obj.video_count
        return format_html('<b>{}</b> vidéo(s)', n) if n else '—'
    video_count.short_description = 'Vidéos'

    def audio_count_display(self, obj):
        n = obj.audio_count
        return format_html('<b>{}</b> audio(s)', n) if n else '—'
    audio_count_display.short_description = 'Audios'


# ──────────────────────────────────────────────────────────────────────────────
# Documents, Vidéos, Audios — pages dédiées avec filtres par section/niveau
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(ExamDocument)
class ExamDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'section_display', 'level_display', 'doc_type', 'file_size_kb', 'is_downloadable', 'uploaded_at']
    list_filter = ['doc_type', 'is_downloadable', 'subject__section', 'subject__level', 'subject__subject_type']
    search_fields = ['title', 'subject__title']
    readonly_fields = ['file_size_kb', 'uploaded_at']
    raw_id_fields = ['subject']

    def section_display(self, obj):
        return obj.subject.get_section_display()
    section_display.short_description = 'Section'

    def level_display(self, obj):
        return obj.subject.get_level_display()
    level_display.short_description = 'Niveau'


@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'section_display', 'level_display', 'duration_minutes', 'is_preview', 'view_count', 'order']
    list_filter = ['is_preview', 'subject__section', 'subject__level']
    list_editable = ['order']
    search_fields = ['title', 'subject__title']
    raw_id_fields = ['subject']

    def section_display(self, obj):
        return obj.subject.get_section_display()
    section_display.short_description = 'Section'

    def level_display(self, obj):
        return obj.subject.get_level_display()
    level_display.short_description = 'Niveau'


@admin.register(AudioResource)
class AudioResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'section_display', 'level_display', 'audio_type', 'duration_minutes', 'is_preview', 'play_count', 'order']
    list_filter = ['audio_type', 'is_preview', 'subject__section', 'subject__level']
    list_editable = ['order']
    search_fields = ['title', 'subject__title']
    raw_id_fields = ['subject']

    def section_display(self, obj):
        return obj.subject.get_section_display()
    section_display.short_description = 'Section'

    def level_display(self, obj):
        return obj.subject.get_level_display()
    level_display.short_description = 'Niveau'


# ──────────────────────────────────────────────────────────────────────────────
# Abonnements & Paiements
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(EduProfile)
class EduProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'country', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'phone_number']
    list_filter = ['country']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display  = ['plan_display', 'type_display', 'prix_display', 'duree_display', 'badge_label', 'is_active']
    list_filter   = ['plan_type', 'is_active']
    list_editable = ['is_active', 'badge_label']
    ordering      = ['price_xaf']

    fieldsets = (
        ('🎓 Identité du forfait', {
            'fields': ('name', 'plan_type', 'badge_label', 'is_active'),
            'description': 'badge_label : texte affiché sur la carte (ex: "Populaire", "Meilleure offre")'
        }),
        ('💰 Tarification', {
            'fields': ('price_xaf', 'duration_days'),
            'description': 'Prix en FCFA · Trimestriel = 90 jours · Annuel = 365 jours'
        }),
        ('✨ Fonctionnalités incluses', {
            'fields': ('features',),
            'description': 'Liste JSON : ["Accès illimité aux sujets","Corrections détaillées","Téléchargement PDF","Vidéos exclusives"]'
        }),
    )

    def plan_display(self, obj):
        icons = {'quarterly': '📅', 'annual': '🗓️'}
        return format_html('<strong>{} {}</strong>', icons.get(obj.plan_type, '📋'), obj.name)
    plan_display.short_description = 'Forfait'
    plan_display.admin_order_field = 'name'

    def type_display(self, obj):
        colors = {'quarterly': '#3B82F6', 'annual': '#8B5CF6'}
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colors.get(obj.plan_type, '#666'), obj.get_plan_type_display()
        )
    type_display.short_description = 'Type'

    def prix_display(self, obj):
        return format_html('<strong>{:,} FCFA</strong>', int(obj.price_xaf)).replace(',', ' ')
    prix_display.short_description = 'Prix'
    prix_display.admin_order_field = 'price_xaf'

    def duree_display(self, obj):
        if obj.duration_days >= 360:
            return '12 mois'
        if obj.duration_days >= 180:
            return '6 mois'
        if obj.duration_days >= 85:
            return '3 mois'
        return f'{obj.duration_days} jours'
    duree_display.short_description = 'Durée'


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
