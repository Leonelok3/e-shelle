import django_filters
from .models import NewsItem, Tag


class NewsItemFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category", lookup_expr="exact")
    country = django_filters.CharFilter(field_name="country_target", lookup_expr="exact")
    tag = django_filters.CharFilter(method="filter_tag")

    q = django_filters.CharFilter(method="filter_q", label="Recherche")

    class Meta:
        model = NewsItem
        fields = ["category", "country"]

    def filter_q(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            title__icontains=value
        ) | queryset.filter(
            summary__icontains=value
        ) | queryset.filter(
            content__icontains=value
        ) | queryset.filter(
            city__icontains=value
        )

    def filter_tag(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(tags__slug=value)
