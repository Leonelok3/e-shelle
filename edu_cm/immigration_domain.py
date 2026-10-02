"""Route the dedicated Canada host without changing E-Shelle requests."""
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect


IMMIGRATION_HOSTS = frozenset({'immigration97.com', 'www.immigration97.com'})
CANADA_PREFIXES = ('/canada/', '/prep/', '/jobs/canada/')
SHARED_PREFIXES = ('/accounts/', '/billing/', '/payments/', '/static/', '/media/')
SHARED_PAGES = frozenset({'/cgu/', '/terms/', '/tarifs/'})


def is_immigration_host(request):
    return request.get_host().split(':', 1)[0].lower() in IMMIGRATION_HOSTS


class ImmigrationDomainMiddleware:
    """Keep authentication local and exclude unrelated applications."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        dedicated_host = is_immigration_host(request)
        # Legacy Canada/preparation links share the same public identity.
        legacy_canada = request.path_info.startswith(CANADA_PREFIXES) or (
            request.path_info.rstrip('/') == '/accounts/upgrade'
            and request.GET.get('app') == 'prep'
        )
        if not dedicated_host and not legacy_canada:
            return self.get_response(request)

        request.is_immigration97 = True
        request.site_brand = 'Immigration97'
        request.public_domain = 'immigration97.com'

        if not dedicated_host:
            return self.get_response(request)

        path = request.path_info
        if path == '/favicon.ico':
            return HttpResponseRedirect('/static/img/immigration97-logo.png?v=20261001')
        if path == '/tarifs/':
            return HttpResponseRedirect('/accounts/upgrade/?app=prep')
        if path in ('/', '/dashboard/', '/accounts/go/'):
            target = '/canada/' if path == '/' else '/canada/parcours/'
            if request.method not in ('GET', 'HEAD'):
                return HttpResponseNotFound()
            query = request.META.get('QUERY_STRING', '')
            return HttpResponseRedirect(target + ('?' + query if query else ''))

        if path == '/robots.txt':
            return HttpResponse('User-agent: *\nAllow: /\nDisallow: /accounts/\n'
                                'Disallow: /billing/\nDisallow: /payments/\n',
                                content_type='text/plain')

        # Do not publish the global E-Shelle sitemap on the Canada domain.
        if path == '/sitemap.xml':
            return HttpResponseNotFound()

        # Accept slashless paths so CommonMiddleware can canonicalize them.
        normalized = path.rstrip('/') + '/'
        allowed = normalized.startswith(CANADA_PREFIXES + SHARED_PREFIXES)
        if not allowed and normalized not in SHARED_PAGES:
            if request.method not in ('GET', 'HEAD'):
                return HttpResponseNotFound()
            return HttpResponseNotFound()

        response = self.get_response(request)
        # Existing .e-shelle.com cookie settings cannot apply to this domain.
        # This middleware must wrap SessionMiddleware and CsrfViewMiddleware.
        for cookie in response.cookies.values():
            cookie['domain'] = ''
        return response
