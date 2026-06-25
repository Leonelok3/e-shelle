from django.contrib import admin
from .models import GermanCVProfile, CVExperience, CVEducation, CVLanguage, GeneratedLebenslauf


class CVExperienceInline(admin.TabularInline):
    model  = CVExperience
    extra  = 0
    fields = ("title", "company", "city", "start_date", "end_date", "is_current")


class CVEducationInline(admin.TabularInline):
    model  = CVEducation
    extra  = 0
    fields = ("degree", "school", "start_year", "end_year")


class CVLanguageInline(admin.TabularInline):
    model  = CVLanguage
    extra  = 0
    fields = ("language", "proficiency", "certificate")


@admin.register(GermanCVProfile)
class GermanCVProfileAdmin(admin.ModelAdmin):
    list_display  = ("full_name", "user", "german_level", "goethe_certified",
                     "target_sector", "updated_at")
    list_filter   = ("german_level", "goethe_certified")
    search_fields = ("first_name", "last_name", "user__username")
    inlines       = [CVExperienceInline, CVEducationInline, CVLanguageInline]


@admin.register(GeneratedLebenslauf)
class GeneratedLebenslaufAdmin(admin.ModelAdmin):
    list_display  = ("user", "offer_title", "created_at")
    list_filter   = ("created_at",)
    search_fields = ("user__username",)
    readonly_fields = ("content_html", "created_at")
