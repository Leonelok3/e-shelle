from django.contrib import admin
from .models import Business, BusinessPhoto


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'sector', 'city', 'whatsapp')


@admin.register(BusinessPhoto)
class BusinessPhotoAdmin(admin.ModelAdmin):
    list_display = ('business', 'order')
