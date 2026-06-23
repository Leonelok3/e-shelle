from django.contrib import admin
from .models import VideoRender


@admin.register(VideoRender)
class VideoRenderAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'status', 'created_at')
