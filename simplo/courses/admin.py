from django.contrib import admin

from .models import CourseRequest


@admin.register(CourseRequest)
class CourseRequestAdmin(admin.ModelAdmin):
    list_display = ("type_demande", "ville", "quartier", "statut", "created_at")
    list_filter = ("type_demande", "ville", "statut")
    search_fields = ("quartier", "description")
