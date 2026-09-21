from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

from canada_resume.templatetags.canada_navigation import GROUPS, canada_navigation


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class CanadaNavigationTests(SimpleTestCase):
    def request_for(self, name):
        request = RequestFactory().get(reverse(name))
        request.resolver_match = resolve(request.path)
        request.user = AnonymousUser()
        return request

    def test_every_module_resolves_and_selects_its_own_group(self):
        for key, _, links in GROUPS:
            for name, _ in links:
                with self.subTest(route=name):
                    menu = canada_navigation({'request': self.request_for(name)})
                    self.assertEqual([g['key'] for g in menu['groups'] if g['active']], [key])
                    self.assertEqual(sum(i['exact'] for g in menu['groups'] for i in g['items']), 1)

    def test_cv_is_not_mistaken_for_job_list(self):
        menu = canada_navigation({'request': self.request_for('canada_resume:edit_profile')})
        self.assertEqual(menu['current'], 'Mon CV et ma lettre')

    def test_full_base_renders_one_navigation_across_canada_and_tcf(self):
        for name in ('canada_landing', 'canada_resume:dashboard',
                     'preparation_tests:tcf_hub', 'jobs:canada_jobs'):
            with self.subTest(route=name):
                request = self.request_for(name)
                html = render_to_string('base.html', {'request': request, 'user': request.user})
                self.assertEqual(html.count('aria-label="Modules Canada"'), 1)
                self.assertIn(reverse('canada_landing'), html)
                self.assertIn('canada-navigation.css', html)

    def test_unrelated_page_does_not_enable_canada(self):
        request = RequestFactory().get('/')
        request.resolver_match = resolve('/')
        self.assertFalse(canada_navigation({'request': request})['enabled'])
