from django.contrib import admin
from .models import Source, Opportunity, Subscription, Alert

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("code","name","country","active","last_run_at")
    search_fields = ("code","name","country")

@admin.register(Opportunity)
class OppAdmin(admin.ModelAdmin):
    list_display = ("title","country","category","is_scholarship","score","deadline","source")
    list_filter = ("country","category","is_scholarship")
    search_fields = ("title","url","eligibility_tags")

@admin.register(Subscription)
class SubAdmin(admin.ModelAdmin):
    list_display = ("user","country_filter","category_filter","min_score","active","created_at")
    list_filter = ("active",)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("user","opportunity","created_at")
