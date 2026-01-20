import csv
from django.contrib import admin
from django.http import HttpResponse

from .models import NewsItem, Tag, NewsletterSubscriber


# =====================================================
# TAGS
# =====================================================
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


# =====================================================
# NEWS ITEMS
# =====================================================
@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "country_target",
        "category",
        "is_published",
        "is_featured",
        "publish_date",
        "views_count",
    )
    list_filter = (
        "is_published",
        "is_featured",
        "country_target",
        "category",
        "publish_date",
    )
    search_fields = ("title", "summary", "content", "slug", "city")
    date_hierarchy = "publish_date"
    autocomplete_fields = ("tags",)

    fieldsets = (
        ("Essentiel", {
            "fields": (
                "title",
                "slug",
                "category",
                "country_target",
                "city",
                "publish_date",
                "is_published",
                "is_featured",
            )
        }),
        ("Contenu", {
            "fields": ("summary", "content")
        }),
        ("Médias", {
            "fields": ("featured_image", "external_image_url", "video_url")
        }),
        ("Source", {
            "fields": ("external_link", "tags")
        }),
        ("Stats", {
            "fields": ("views_count",)
        }),
    )

    readonly_fields = ("views_count",)
    prepopulated_fields = {"slug": ("title",)}


# =====================================================
# NEWSLETTER — EXPORT CSV
# =====================================================
@admin.action(description="Exporter en CSV (emails)")
def export_newsletters_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="immigration97_newsletters.csv"'

    # BOM UTF-8 pour Excel
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "email",
        "country_interest",
        "source_page",
        "is_active",
        "created_at",
    ])

    for obj in queryset.order_by("-created_at"):
        writer.writerow([
            obj.email,
            obj.country_interest,
            obj.source_page,
            "1" if obj.is_active else "0",
            obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    return response


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "country_interest",
        "source_page",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "country_interest",
        "source_page",
        "created_at",
    )
    search_fields = ("email",)
    ordering = ("-created_at",)
    actions = [export_newsletters_csv]
