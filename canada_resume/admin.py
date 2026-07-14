from django.contrib import admin
from .models import CanadaCVProfile, CanadaCVExperience, CanadaCVEducation, CanadaCVLanguage, GeneratedCanadaResume

@admin.register(CanadaCVProfile)
class CanadaCVProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "email", "phone", "target_sector", "created_at")
    search_fields = ("first_name", "last_name", "email", "target_sector")


@admin.register(CanadaCVExperience)
class CanadaCVExperienceAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "user", "city", "province_country", "start_date", "is_current")
    list_filter = ("is_current", "province_country")
    search_fields = ("title", "company", "user__email")


@admin.register(CanadaCVEducation)
class CanadaCVEducationAdmin(admin.ModelAdmin):
    list_display = ("degree", "school", "user", "city", "province_country", "start_year", "end_year")
    search_fields = ("degree", "school", "user__email")


@admin.register(CanadaCVLanguage)
class CanadaCVLanguageAdmin(admin.ModelAdmin):
    list_display = ("language", "proficiency", "user", "certificate")
    list_filter = ("language", "proficiency")
    search_fields = ("language", "user__email")


@admin.register(GeneratedCanadaResume)
class GeneratedCanadaResumeAdmin(admin.ModelAdmin):
    list_display = ("user", "offer_title", "language", "created_at")
    list_filter = ("language", "created_at")
    search_fields = ("user__email", "custom_offer_title", "custom_offer_company")
