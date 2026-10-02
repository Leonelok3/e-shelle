from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from edu_cm.immigration_domain import ImmigrationDomainMiddleware


@override_settings(ALLOWED_HOSTS=['immigration97.com', 'www.immigration97.com', 'e-shelle.com'])
class ImmigrationDomainTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.seen = []

        def application(request):
            self.seen.append(request.path)
            response = HttpResponse('application')
            response.set_cookie('sessionid', 'example', domain='.e-shelle.com', httponly=True)
            return response

        self.middleware = ImmigrationDomainMiddleware(application)

    def request(self, path, host='immigration97.com', method='get'):
        return self.middleware(getattr(self.factory, method)(path, HTTP_HOST=host))

    def test_eshelle_routes_and_cookies_are_unchanged(self):
        for path in ('/', '/canada/', '/prep/', '/boutique/', '/accounts/login/'):
            response = self.request(path, host='e-shelle.com')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.cookies['sessionid']['domain'], '.e-shelle.com')

    def test_new_domain_enters_canada_and_preserves_query(self):
        for host in ('immigration97.com', 'www.immigration97.com'):
            self.assertEqual(self.request('/?utm_source=test', host)['Location'],
                             '/canada/?utm_source=test')

    def test_canada_and_shared_services_stay_local(self):
        for path in ('/canada/', '/canada/parcours/', '/prep/api/submit-ee/',
                     '/jobs/canada/bourses/', '/accounts/login/', '/billing/access/',
                     '/payments/', '/canada', '/cgu/'):
            response = self.request(path, method='post')
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.cookies['sessionid']['domain'], '')
            self.assertTrue(response.cookies['sessionid']['httponly'])

    def test_other_apps_do_not_send_users_to_another_brand(self):
        self.assertEqual(self.request('/boutique/?page=2').status_code, 404)
        self.assertEqual(self.request('/canada-fake/').status_code, 404)
        self.assertEqual(self.seen, [])

    def test_legacy_prep_payment_page_uses_immigration_brand(self):
        request = self.factory.get('/accounts/upgrade/?app=prep', HTTP_HOST='e-shelle.com')
        response = self.middleware(request)
        self.assertEqual(request.site_brand, 'Immigration97')
        self.assertEqual(response.cookies['sessionid']['domain'], '.e-shelle.com')

    def test_tariffs_are_local_prep_offers(self):
        self.assertEqual(self.request('/tarifs/')['Location'], '/accounts/upgrade/?app=prep')

    def test_does_not_forward_post_to_another_domain(self):
        self.assertEqual(self.request('/boutique/', method='post').status_code, 404)
        self.assertEqual(self.seen, [])

    def test_registration_default_dashboard_returns_to_canada(self):
        self.assertEqual(self.request('/dashboard/')['Location'], '/canada/parcours/')

    def test_does_not_publish_global_sitemap(self):
        self.assertEqual(self.request('/sitemap.xml').status_code, 404)
        self.assertNotIn(b'Sitemap:', self.request('/robots.txt').content)

    def test_brand_is_attached_only_to_immigration_requests(self):
        for host, expected in [('immigration97.com', 'Immigration97'), ('e-shelle.com', 'Immigration97')]:
            request = self.factory.get('/canada/', HTTP_HOST=host)
            self.middleware(request)
            self.assertEqual(getattr(request, 'site_brand', None), expected)

    def test_browser_default_icon_does_not_leave_immigration97(self):
        self.assertEqual(self.request('/favicon.ico')['Location'],
                         '/static/img/immigration97-logo.png?v=20261001')
