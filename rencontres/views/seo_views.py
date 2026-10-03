from django.http import Http404
from django.shortcuts import render
from rencontres.seo_content import SEO_PAGES, COMMON_FAQ, destination_links


def seo_landing(request, slug):
    page = SEO_PAGES.get(slug)
    if not page:
        raise Http404
    return render(request, 'rencontres/seo_landing.html', {
        'page': page, 'slug': slug, 'love_faq': COMMON_FAQ,
        'love_destinations': destination_links(),
    })
