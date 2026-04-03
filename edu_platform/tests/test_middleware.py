"""
Tests du middleware DeviceLockMiddleware.
"""
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from edu_platform.models import SubscriptionPlan, AccessCode, EduProfile
from edu_platform.middleware.device_lock_middleware import DeviceLockMiddleware

User = get_user_model()


def make_plan():
    return SubscriptionPlan.objects.create(
        name='Plan Test', plan_type='quarterly',
        price_xaf=5000, duration_days=90,
    )


def make_user(username='mw_user'):
    user = User.objects.create_user(username=username, email=f'{username}@test.com', password='pass')
    EduProfile.objects.create(user=user, phone_number=f'+23769900000{len(username)}')
    return user


def make_active_code(user, plan, days_from_now=90):
    return AccessCode.objects.create(
        code='TEST-1111-2222-3333',
        plan=plan,
        status='active',
        activation_count=1,
        activated_by=user,
        activated_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=days_from_now),
    )


class TestDeviceLockMiddleware(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.plan = make_plan()

    def _make_request(self, path='/edu/dashboard/', user=None, fingerprint='a' * 64):
        request = self.factory.get(path)
        request.META['HTTP_X_DEVICE_FINGERPRINT'] = fingerprint
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        session = SessionStore()
        session.create()
        request.session = session
        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return request

    def _get_middleware(self):
        def dummy_response(req):
            from django.http import HttpResponse
            return HttpResponse('OK')
        return DeviceLockMiddleware(dummy_response)

    def test_non_edu_path_passes(self):
        """Les URLs hors /edu/ ne sont pas touchées par le middleware."""
        user = make_user('non_edu')
        request = self._make_request(path='/accounts/login/', user=user)
        mw = self._get_middleware()
        response = mw(request)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_passes(self):
        """Un utilisateur non connecté n'est pas bloqué (laissé à Django auth)."""
        request = self._make_request(path='/edu/dashboard/')
        mw = self._get_middleware()
        response = mw(request)
        self.assertEqual(response.status_code, 200)

    def test_exempt_path_passes(self):
        """Les chemins exemptés (/edu/login/, /edu/plans/, etc.) passent toujours."""
        user = make_user('exempt_user')
        for path in ['/edu/login/', '/edu/plans/', '/edu/register/', '/edu/']:
            request = self._make_request(path=path, user=user)
            mw = self._get_middleware()
            response = mw(request)
            self.assertEqual(response.status_code, 200, f"Chemin {path} devrait être exempté")

    def test_valid_device_passes(self):
        """Un utilisateur avec abonnement actif et bon appareil passe."""
        user = make_user('valid_device_user')
        code = make_active_code(user, self.plan)

        from edu_platform.models import DeviceBinding
        DeviceBinding.objects.create(
            user=user,
            access_code=code,
            device_fingerprint='a' * 64,
            is_primary=True,
        )

        request = self._make_request(path='/edu/dashboard/', user=user, fingerprint='a' * 64)
        mw = self._get_middleware()
        response = mw(request)
        self.assertEqual(response.status_code, 200)

    def test_unknown_device_redirects(self):
        """Un appareil inconnu doit être redirigé vers /edu/device-blocked/."""
        from django.test import Client
        from edu_platform.models import DeviceBinding

        user = make_user('blocked_user')
        code = make_active_code(user, self.plan)

        # Enregistrer un appareil A
        DeviceBinding.objects.create(
            user=user,
            access_code=code,
            device_fingerprint='a' * 64,
            is_primary=True,
        )

        # Requête depuis appareil B (fingerprint différent) via Client
        client = Client()
        client.force_login(user)
        response = client.get('/edu/subjects/', HTTP_X_DEVICE_FINGERPRINT='b' * 64)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/edu/device-blocked/', response.get('Location', ''))

    def test_expired_subscription_redirects(self):
        """Un abonnement expiré doit rediriger vers la page de renouvellement."""
        from django.test import Client

        user = make_user('expired_user')
        AccessCode.objects.create(
            code='EXPR-1111-2222-3333',
            plan=self.plan,
            status='active',
            activation_count=1,
            activated_by=user,
            activated_at=timezone.now() - timedelta(days=100),
            expires_at=timezone.now() - timedelta(days=10),  # Expiré !
        )

        client = Client()
        client.force_login(user)
        response = client.get('/edu/subjects/')
        self.assertEqual(response.status_code, 302)
        location = response.get('Location', '')
        self.assertTrue(
            '/edu/renew/' in location or '/edu/plans/' in location,
            f"Doit rediriger vers renew ou plans, got: {location}"
        )
