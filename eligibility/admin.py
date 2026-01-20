from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Session

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
