from django.contrib import admin
from .models import DrivingSchool, Course


@admin.register(DrivingSchool)
class DrivingSchoolAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "city", "is_active", "created_at")
    search_fields = ("name", "city", "address")
    list_display_links = ("name",)
    readonly_fields = ("created_at",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "order", "is_published")
    list_filter = ("is_published", "school")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary")
    list_display_links = ("title",)
