from django.contrib import admin
from .models import Profile, Category, PortfolioItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

class PortfolioInline(admin.TabularInline):
    model = PortfolioItem
    extra = 1

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [PortfolioInline]
    list_display = ('user', 'headline', 'category', 'location')
    list_filter = ('category',)