from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simplo.courses"
    label = "simplo_courses"
    verbose_name = "Simplo - Courses"
