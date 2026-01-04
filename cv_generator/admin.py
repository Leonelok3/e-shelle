from django.contrib import admin
from .models import (
    CV,
    CVTemplate,
    Experience,
    Education,
    Skill,
    Language,
    Volunteer,
    Hobby,
    Project,
    Certification,
)


# =====================================================
# CV TEMPLATE
# =====================================================
@admin.register(CVTemplate)
class CVTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "style", "is_active")
    list_filter = ("style", "is_active")
    search_fields = ("name", "description")
    list_editable = ("is_active",)
    ordering = ("name",)


# =====================================================
# CV
# =====================================================
@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "utilisateur",
        "template",
        "profession",
        "is_completed",
        "is_published",
        "created_at",
    )
    list_filter = ("is_completed", "is_published", "template")
    search_fields = ("utilisateur__username", "utilisateur__email", "profession")
    ordering = ("-created_at",)


# =====================================================
# EXPERIENCE
# =====================================================
@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "cv", "start_date", "end_date")
    list_filter = ("company",)
    search_fields = ("title", "company")


# =====================================================
# EDUCATION
# =====================================================
@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("diploma", "institution", "cv", "start_date", "end_date")
    search_fields = ("diploma", "institution")


# =====================================================
# SKILL
# =====================================================
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "cv")
    list_filter = ("category",)
    search_fields = ("name",)


# =====================================================
# LANGUAGE
# =====================================================
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "cv")
    search_fields = ("name", "level")


# =====================================================
# PROJECT
# =====================================================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "cv")
    search_fields = ("title",)


# =====================================================
# VOLUNTEER
# =====================================================
@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ("role", "cv", "start_date", "end_date")
    search_fields = ("role",)


# =====================================================
# CERTIFICATION
# =====================================================
@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "cv", "date_obtained")
    search_fields = ("name", "organization")


# =====================================================
# HOBBY
# =====================================================
@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    list_display = ("name", "cv")
    search_fields = ("name",)
