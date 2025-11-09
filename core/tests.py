from django.test import TestCase

# Create your tests here.
from django.test import TestCase

class HomePageTests(TestCase):
    def test_home_status(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-i18n-key="hero_title"')

    def test_module_routes_exist(self):
        for path in [
            "/visa-photo/", "/cv-generator/", "/motivation-letter/", "/visa-tourisme/",
            "/visa-etudes/", "/visa-travail/", "/prep-langues/", "/residence-permanente/", "/billing/"
        ]:
            r = self.client.get(path)
            self.assertIn(r.status_code, (200, 301, 302))
