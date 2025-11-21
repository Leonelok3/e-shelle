from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PRProfile, PRPlanStep, ImmigrationProgram, ProgramResource

# Tes autres admin PRProfile / PRPlanStep si tu en as déjà…

@admin.register(ImmigrationProgram)
class ImmigrationProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "category", "is_active")
    list_filter = ("country", "category", "is_active")
    search_fields = ("name", "slug", "summary")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProgramResource)
class ProgramResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "program", "resource_type", "order")
    list_filter = ("resource_type", "program__country")
    search_fields = ("title", "description", "program__name")
    autocomplete_fields = ("program",)
    ordering = ("program", "resource_type", "order")
