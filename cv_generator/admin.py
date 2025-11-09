from django.contrib import admin
from .models import (
    CV, CVTemplate, Experience, Education, 
    Skill, Language, Volunteer, Hobby, 
    Certification, Project, CVExportHistory
)


# ------------------------------
# 🔹 Inline pour les sections du CV
# ------------------------------
class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 1
    fields = ('title', 'company', 'start_date', 'end_date', 'location')


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1
    fields = ('diploma', 'institution', 'start_date', 'end_date')


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ('name', 'category', 'level')


class LanguageInline(admin.TabularInline):
    model = Language
    extra = 1
    fields = ('name', 'level')


class VolunteerInline(admin.TabularInline):
    model = Volunteer
    extra = 1
    fields = ('role', 'organization', 'start_date', 'end_date')


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 1
    fields = ('name', 'organization', 'date_obtained')


class HobbyInline(admin.TabularInline):
    model = Hobby
    extra = 1
    fields = ('name',)


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 1
    fields = ('title', 'start_date', 'end_date')


# ------------------------------
# 🔹 Admin du CV principal
# ------------------------------
@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'profession', 'pays_cible', 'get_completion_percentage', 'is_completed', 'date_modification')
    list_filter = ('is_completed', 'is_published', 'pays_cible', 'step1_completed', 'step2_completed', 'step3_completed')
    search_fields = ('utilisateur__username', 'utilisateur__email', 'profession')
    readonly_fields = ('date_creation', 'date_modification', 'get_completion_percentage')
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('utilisateur', 'profession', 'pays_cible', 'template', 'summary')
        }),
        ('Progression', {
            'fields': ('current_step', 'step1_completed', 'step2_completed', 'step3_completed', 'is_completed', 'is_published')
        }),
        ('Analyse IA', {
            'fields': ('quality_score', 'last_analysis'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification', 'date_completion'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [
        ExperienceInline,
        EducationInline,
        SkillInline,
        LanguageInline,
        CertificationInline,
        VolunteerInline,
        ProjectInline,
        HobbyInline,
    ]


# ------------------------------
# 🔹 Admin des Templates
# ------------------------------
@admin.register(CVTemplate)
class CVTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'style_type', 'country', 'industry', 'popularity_score', 'is_active')
    list_filter = ('style_type', 'country', 'is_active')
    search_fields = ('name', 'industry', 'country')
    list_editable = ('is_active', 'popularity_score')


# ------------------------------
# 🔹 Admin des Expériences
# ------------------------------
@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'cv', 'start_date', 'end_date', 'location')
    list_filter = ('start_date', 'company')
    search_fields = ('title', 'company', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin de l'Éducation
# ------------------------------
@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('diploma', 'institution', 'cv', 'start_date', 'end_date')
    list_filter = ('start_date', 'institution')
    search_fields = ('diploma', 'institution', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin des Compétences
# ------------------------------
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'level', 'cv')
    list_filter = ('category', 'level')
    search_fields = ('name', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin des Langues
# ------------------------------
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'cv')
    list_filter = ('level',)
    search_fields = ('name', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin du Bénévolat
# ------------------------------
@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('role', 'organization', 'cv', 'start_date', 'end_date')
    list_filter = ('start_date',)
    search_fields = ('role', 'organization', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin des Certifications
# ------------------------------
@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'cv', 'date_obtained', 'expiry_date')
    list_filter = ('date_obtained', 'organization')
    search_fields = ('name', 'organization', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin des Projets
# ------------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'cv', 'start_date', 'end_date')
    list_filter = ('start_date',)
    search_fields = ('title', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin des Loisirs
# ------------------------------
@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    list_display = ('name', 'cv')
    search_fields = ('name', 'cv__utilisateur__username')


# ------------------------------
# 🔹 Admin de l'historique d'export
# ------------------------------
@admin.register(CVExportHistory)
class CVExportHistoryAdmin(admin.ModelAdmin):
    list_display = ('cv', 'export_format', 'exported_at', 'file_size')
    list_filter = ('export_format', 'exported_at')
    search_fields = ('cv__utilisateur__username',)
    readonly_fields = ('exported_at',)