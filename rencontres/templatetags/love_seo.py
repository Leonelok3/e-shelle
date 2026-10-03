import json
from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from rencontres.seo_content import SEO_PAGES, COMMON_FAQ, HOME_DESCRIPTION, public_routes, destination_links

register = template.Library()


@register.simple_tag(takes_context=True)
def love_metadata(context):
    request = context.get('request')
    route = request.resolver_match.url_name if request and request.resolver_match else ''
    if route not in public_routes() or (route == 'accueil' and request.user.is_authenticated):
        return {'public': False}
    origin = getattr(settings, 'RENCONTRES_PUBLIC_ORIGIN', 'https://e-shelle.com').rstrip('/')
    url = origin + reverse('rencontres:' + route)
    page = next((p for p in SEO_PAGES.values() if p['route'] == route), None)
    title = page['title'] if page else {
        'accueil': 'Rencontres locales & internationales | E-Shelle Love',
        'premium': 'Gratuit et pass Love | E-Shelle Love',
        'securite': 'Conseils de sécurité pour vos rencontres | E-Shelle Love',
    }[route]
    description = page['intro'] if page else {
        'accueil': HOME_DESCRIPTION,
        'premium': 'Découvrez le compte gratuit et les pass E-Shelle Love : fonctionnalités, durées et demandes d’activation.',
        'securite': 'Conseils E-Shelle Love pour des rencontres locales et à distance : confidentialité, blocage, signalement et premier rendez-vous.',
    }[route]
    website_id = origin + reverse('rencontres:accueil') + '#website'
    graph = [
        {'@type': 'WebSite', '@id': website_id, 'name': 'E-Shelle Love',
         'url': origin + reverse('rencontres:accueil'), 'inLanguage': 'fr', 'description': HOME_DESCRIPTION},
        {'@type': 'WebPage', '@id': url + '#page', 'url': url, 'name': title,
         'description': description, 'inLanguage': 'fr', 'isPartOf': {'@id': website_id}},
    ]
    if page:
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'E-Shelle Love',
             'item': origin + reverse('rencontres:accueil')},
            {'@type': 'ListItem', 'position': 2, 'name': page['city'], 'item': url},
        ]})
    if page or route == 'accueil':
        graph.append({'@type': 'FAQPage', '@id': url + '#questions', 'mainEntity': [
            {'@type': 'Question', 'name': item['question'],
             'acceptedAnswer': {'@type': 'Answer', 'text': item['answer']}} for item in COMMON_FAQ]})
    data = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)
    for char, escaped in [('<', '\\u003C'), ('>', '\\u003E'), ('&', '\\u0026')]:
        data = data.replace(char, escaped)
    return {'public': True, 'canonical': url, 'title': title, 'description': description,
            'schema': mark_safe(data), 'image': origin + '/static/rencontres/images/love-social.png'}


@register.inclusion_tag('rencontres/components/destinations.html')
def love_destinations():
    return {'love_destinations': destination_links()}


@register.inclusion_tag('rencontres/components/faq.html')
def love_questions():
    return {'love_faq': COMMON_FAQ}
