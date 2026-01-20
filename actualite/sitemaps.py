from django.contrib.sitemaps import Sitemap
from .models import NewsItem


class NewsItemSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return NewsItem.objects.filter(is_published=True).order_by("-publish_date")

    def lastmod(self, obj):
        return obj.updated_at
