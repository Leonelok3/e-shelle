# cv_generator/admin.py

from django.contrib import admin
from .models import (
    CV,
    CVTemplate,
    Experience,
    Formation,
    Competence,
    Langue,
    Skill,
    Certification,
    Volunteer,
    Project,
    Hobby,
    CVUpload,
)


# =====================================================
# ADMIN CV TEMPLATE
# =====================================================
@admin.register(CVTemplate)
class CVTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_premium", "order", "template_file", "created_at")
    list_filter = ("is_active", "is_premium")
    search_fields = ("name", "description", "template_file")
    list_editable = ("is_active", "is_premium")
    ordering = ("order", "name")


# =====================================================
# ADMIN CV
# =====================================================
@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_username",
        "prenom",
        "nom",
        "titre_poste",
        "is_completed",
        "current_step",
        "created_at",
    )
    list_filter = ("is_completed", "current_step", "is_published", "created_at")
    search_fields = ("prenom", "nom", "email", "titre_poste", "user__username")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)

    fieldsets = (
        ("Utilisateur", {"fields": ("user", "template")}),
        ("Informations Personnelles", {
            "fields": (
                "prenom", "nom", "titre_poste", "email", "telephone",
                "ville", "province", "linkedin",
            )
        }),
        ("Résumé", {"fields": ("summary", "resume_professionnel")}),
        ("Paramètres", {"fields": ("language", "profession", "pays_cible", "is_published")}),
        ("Progression", {
            "fields": (
                "current_step", "step1_completed", "step2_completed",
                "step3_completed", "is_completed",
            )
        }),
        ("Métadonnées", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Utilisateur")
    def get_username(self, obj):
        return getattr(obj.user, "username", str(obj.user))


# =====================================================
# ADMIN EXPERIENCE (SAFE: support FR + EN)
# =====================================================
@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "poste_or_title", "entreprise_or_company", "debut", "fin")
    # ✅ SAFE: évite date_debut/start_date qui peuvent varier selon ton modèle réel
    list_filter = ("cv",)
    search_fields = (
        "poste", "entreprise", "ville", "date_debut", "date_fin",
        "title", "company", "location",
        "cv__prenom", "cv__nom",
    )
    ordering = ("-id",)

    @admin.display(description="Poste/Titre")
    def poste_or_title(self, obj):
        return obj.poste or obj.title or ""

    @admin.display(description="Entreprise")
    def entreprise_or_company(self, obj):
        return obj.entreprise or obj.company or ""

    @admin.display(description="Début")
    def debut(self, obj):
        # date_debut (str) ou start_date (DateField)
        return obj.date_debut or obj.start_date or ""

    @admin.display(description="Fin")
    def fin(self, obj):
        return obj.date_fin or obj.end_date or ""


# =====================================================
# ADMIN FORMATION (SAFE: support FR + EN)
# =====================================================
@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "diplome_or_diploma", "etablissement_or_institution", "start_date", "end_date", "annee_obtention")
    list_filter = ("cv",)
    search_fields = (
        "diplome", "etablissement", "ville", "annee_obtention",
        "diploma", "institution", "location",
        "cv__prenom", "cv__nom",
    )
    ordering = ("-id",)

    @admin.display(description="Diplôme")
    def diplome_or_diploma(self, obj):
        return obj.diplome or obj.diploma or ""

    @admin.display(description="Établissement")
    def etablissement_or_institution(self, obj):
        return obj.etablissement or obj.institution or ""


# =====================================================
# ADMIN COMPÉTENCE (SAFE)
# =====================================================
@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "nom", "niveau", "created_at")
    list_filter = ("cv",)
    search_fields = ("nom", "niveau", "cv__prenom", "cv__nom")
    ordering = ("-id",)


# =====================================================
# ADMIN LANGUE (SAFE: support FR + EN)
# =====================================================
@admin.register(Langue)
class LangueAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "langue_or_name", "niveau_or_level")
    # ✅ SAFE: pas de list_filter sur niveau car chez toi ça casse parfois
    list_filter = ("cv",)
    search_fields = ("langue", "niveau", "name", "level", "cv__prenom", "cv__nom")
    ordering = ("-id",)

    @admin.display(description="Langue")
    def langue_or_name(self, obj):
        return obj.langue or obj.name or ""

    @admin.display(description="Niveau")
    def niveau_or_level(self, obj):
        return obj.niveau or obj.level or ""


# =====================================================
# ADMIN SKILL
# =====================================================
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "name", "category")
    list_filter = ("category", "cv")
    search_fields = ("name",)
    ordering = ("-id",)


# =====================================================
# ADMIN CERTIFICATION (SAFE: support FR + EN)
# =====================================================
@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "nom_or_name", "organisme_or_org", "annee", "date_obtained")
    list_filter = ("cv",)
    search_fields = ("nom", "organisme", "name", "organization", "credential_id", "cv__prenom", "cv__nom")
    ordering = ("-id",)

    @admin.display(description="Nom")
    def nom_or_name(self, obj):
        return obj.nom or obj.name or ""

    @admin.display(description="Organisme")
    def organisme_or_org(self, obj):
        return obj.organisme or obj.organization or ""


# =====================================================
# ADMIN VOLUNTEER
# =====================================================
@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "role", "organization", "start_date", "end_date")
    list_filter = ("cv",)
    search_fields = ("role", "organization", "description", "cv__prenom", "cv__nom")
    ordering = ("-id",)


# =====================================================
# ADMIN PROJECT
# =====================================================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "title", "technologies", "start_date", "end_date")
    list_filter = ("cv",)
    search_fields = ("title", "technologies", "description", "cv__prenom", "cv__nom")
    ordering = ("-id",)


# =====================================================
# ADMIN HOBBY
# =====================================================
@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    list_display = ("id", "cv", "name")
    list_filter = ("cv",)
    search_fields = ("name", "description", "cv__prenom", "cv__nom")
    ordering = ("-id",)


# =====================================================
# ADMIN CV UPLOAD
# =====================================================
@admin.register(CVUpload)
class CVUploadAdmin(admin.ModelAdmin):
    list_display = ("cv", "status", "created_at")
    list_filter = ("status", "created_at")
    readonly_fields = ("extracted_text", "created_at")
    ordering = ("-created_at",)
