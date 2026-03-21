from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from .models import NewsItem


class ActualiteRssFeed(Feed):
    title = "Immigration97 — Actualités & Opportunités Immigration"
    description = (
        "Dernières actualités immigration : visa travail, études, résidence permanente "
        "pour USA, Canada, Allemagne, Italie, France. Sources officielles."
    )
    author_name = "Immigration97"
    author_email = "contact@immigration97.com"
    author_link = "https://www.immigration97.com"
    categories = ("immigration", "visa", "emploi", "actualité")
    feed_copyright = "Immigration97"

    def link(self):
        return reverse("actualite:list")

    def items(self):
        return (
            NewsItem.objects.filter(is_published=True)
            .order_by("-publish_date")[:50]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.publish_date

    def item_updateddate(self, item):
        return item.updated_at

    def item_author_name(self, item):
        return "Immigration97"

    def item_categories(self, item):
        return (item.get_category_display(), item.country_target)

    def item_enclosure_url(self, item):
        return item.image_url or None

    def item_enclosure_length(self, item):
        return 0

    def item_enclosure_mime_type(self, item):
        if item.image_url:
            return "image/jpeg"
        return None


class ActualiteAtomFeed(ActualiteRssFeed):
    """Feed Atom — pour Google News et lecteurs modernes."""
    feed_type = Atom1Feed
    subtitle = ActualiteRssFeed.description
