from django.contrib import admin
from .models import GermanCVProfile, CVExperience, CVEducation, CVLanguage, GeneratedLebenslauf


@admin.register(GermanCVProfile)
class GermanCVProfileAdmin(admin.ModelAdmin):
    list_display  = ("full_name", "user", "german_level", "goethe_certified",
                     "target_sector", "updated_at")
    list_filter   = ("german_level", "goethe_certified")
    search_fields = ("first_name", "last_name", "user__username")


@admin.register(CVExperience)
class CVExperienceAdmin(admin.ModelAdmin):
    list_display  = ("title", "company", "city", "start_date", "end_date", "is_current")
    list_filter   = ("is_current", "country")
    search_fields = ("title", "company", "user__username")
    raw_id_fields = ("user",)


@admin.register(CVEducation)
class CVEducationAdmin(admin.ModelAdmin):
    list_display  = ("degree", "school", "city", "start_year", "end_year")
    search_fields = ("degree", "school", "user__username")
    raw_id_fields = ("user",)


@admin.register(CVLanguage)
class CVLanguageAdmin(admin.ModelAdmin):
    list_display  = ("language", "proficiency", "certificate")
    list_filter   = ("proficiency",)
    raw_id_fields = ("user",)


@admin.register(GeneratedLebenslauf)
class GeneratedLebenslaufAdmin(admin.ModelAdmin):
    list_display  = ("user", "offer_title", "created_at")
    list_filter   = ("created_at",)
    search_fields = ("user__username",)
    readonly_fields = ("content_html", "created_at")
