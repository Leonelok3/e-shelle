from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory, override_settings
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from accounts.adapters import SocialAccountAdapter


class DomainOAuthTests(SimpleTestCase):
    @override_settings(IMMIGRATION97_GOOGLE_CLIENT_ID='dedicated-client',
                       IMMIGRATION97_GOOGLE_CLIENT_SECRET='test-secret')
    def test_google_identity_is_isolated_by_domain(self):
        adapter = SocialAccountAdapter()
        request = RequestFactory().get('/')
        request.is_immigration97 = True
        app = adapter.get_app(request, 'google')
        self.assertEqual(app.client_id, 'dedicated-client')
        self.assertEqual(app.name, 'Immigration97')
        request.is_immigration97 = False
        with patch.object(DefaultSocialAccountAdapter, 'get_app', return_value='shared'):
            self.assertEqual(adapter.get_app(request, 'google'), 'shared')

    @override_settings(IMMIGRATION97_GOOGLE_CLIENT_ID='', IMMIGRATION97_GOOGLE_CLIENT_SECRET='')
    def test_existing_google_configuration_remains_available(self):
        request = RequestFactory().get('/')
        request.is_immigration97 = True
        with patch.object(DefaultSocialAccountAdapter, 'get_app', return_value='shared'):
            self.assertEqual(SocialAccountAdapter().get_app(request, 'google'), 'shared')
