from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client_name", "salon", "service", "date", "time", "status")
    list_filter = ("status", "date", "salon")
    search_fields = ("client_name", "client_phone")
    list_editable = ("status",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(salon__owner=request.user)
