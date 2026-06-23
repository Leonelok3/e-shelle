from django.contrib import admin
from .models import GeneratedImage


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'scene', 'backend', 'seed', 'created_at')
