from django.contrib import admin
from .models import Category, Salon, Service, OpeningHour


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class OpeningHourInline(admin.TabularInline):
    model = OpeningHour
    extra = 0
    max_num = 7


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "city", "owner", "is_active", "is_verified", "created_at")
    list_filter = ("kind", "city", "is_active", "is_verified")
    search_fields = ("name", "city", "district")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OpeningHourInline, ServiceInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "salon", "price", "duration_minutes", "is_active")
    list_filter = ("is_active",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(salon__owner=request.user)
