from django.contrib import admin
from .models import Scene


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'order', 'title', 'duration_seconds')
    list_filter = ('project',)
