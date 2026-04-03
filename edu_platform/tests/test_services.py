"""
Tests unitaires des services EduCam Pro.
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from edu_platform.models import (
    SubscriptionPlan, AccessCode, EduProfile, PaymentTransaction, DeviceBinding
)
from edu_platform.services.code_generator import generate_access_code, _format_code, _generate_raw_code
from edu_platform.services.device_service import (
    bind_device, verify_device, DeviceConflictException, extract_fingerprint
)

User = get_user_model()


def make_plan(**kwargs):
    defaults = dict(
        name='Plan Test', plan_type='quarterly',
        price_xaf=5000, duration_days=90,
    )
    defaults.update(kwargs)
    return SubscriptionPlan.objects.create(**defaults)


def make_user(username='testuser', email='test@test.com', phone='+237699000001'):
    user = User.objects.create_user(username=username, email=email, password='pass123')
    EduProfile.objects.create(user=user, phone_number=phone)
    return user


def make_transaction(user, plan, provider='orange_money'):
    return PaymentTransaction.objects.create(
        user=user, plan=plan, provider=provider,
        phone_number=user.edu_profile.phone_number,
        amount_xaf=plan.price_xaf, status='confirmed',
    )


# ── TEST CODE GENERATOR ───────────────────────────────────────────

class TestCodeFormat(TestCase):

    def test_code_format_XXXX_XXXX_XXXX_XXXX(self):
        """Le code généré doit respecter le format XXXX-XXXX-XXXX-XXXX."""
        raw = _generate_raw_code()
        code = _format_code(raw)
        parts = code.split('-')
        self.assertEqual(len(parts), 4, "Le code doit avoir 4 groupes séparés par -")
        for part in parts:
            self.assertEqual(len(part), 4, f"Chaque groupe doit avoir 4 caractères, got: {part}")

    def test_code_chars_no_ambiguous(self):
        """Le code ne doit pas contenir O, 0, I, l (caractères ambigus)."""
        for _ in range(20):
            raw = _generate_raw_code()
            for char in ['O', '0', 'I', 'l']:
                self.assertNotIn(char, raw, f"Caractère ambigu '{char}' trouvé dans le code")

    def test_code_length(self):
        """Code formaté = 19 caractères (16 + 3 tirets)."""
        raw = _generate_raw_code()
        self.assertEqual(len(_format_code(raw)), 19)


class TestCodeGenerator(TestCase):

    def setUp(self):
        self.plan = make_plan()
        self.user = make_user()

    def test_generate_access_code_creates_object(self):
        """generate_access_code doit créer un AccessCode avec status='unused'."""
        tx = make_transaction(self.user, self.plan)
        with patch('edu_platform.services.notification_service.send_access_code_notification'):
            code = generate_access_code(tx)
        self.assertIsNotNone(code.pk)
        self.assertEqual(code.status, 'unused')
        self.assertEqual(code.plan, self.plan)
        self.assertEqual(code.transaction, tx)

    def test_code_uniqueness(self):
        """Deux codes générés ne doivent pas être identiques."""
        tx1 = make_transaction(self.user, self.plan)
        tx2 = make_transaction(self.user, self.plan)
        with patch('edu_platform.services.notification_service.send_access_code_notification'):
            code1 = generate_access_code(tx1)
            code2 = generate_access_code(tx2)
        self.assertNotEqual(code1.code, code2.code)

    def test_single_activation_enforcement(self):
        """Un code ne peut être activé qu'une seule fois (max_activations=1 par défaut)."""
        tx = make_transaction(self.user, self.plan)
        with patch('edu_platform.services.notification_service.send_access_code_notification'):
            code = generate_access_code(tx)
        self.assertEqual(code.max_activations, 1)


# ── TEST DEVICE SERVICE ────────────────────────────────────────────

class TestDeviceService(TestCase):

    def setUp(self):
        self.plan = make_plan()
        self.user = make_user()

    def _make_active_code(self):
        """Crée un AccessCode unused pour les tests."""
        return AccessCode.objects.create(
            code='TEST-ABCD-EFGH-IJKL',
            plan=self.plan,
            status='unused',
        )

    def _make_request(self, fingerprint='abc' * 21 + 'de'):
        """Crée un mock de request avec fingerprint."""
        req = MagicMock()
        req.META = {
            'HTTP_X_DEVICE_FINGERPRINT': fingerprint,
            'REMOTE_ADDR': '192.168.1.1',
            'HTTP_USER_AGENT': 'TestBrowser/1.0 (Android)',
        }
        req.COOKIES = {}
        return req

    def _valid_fingerprint(self):
        return 'a' * 64  # 64 chars hex valides

    def test_first_binding_success(self):
        """La première activation d'un code doit réussir et créer un DeviceBinding."""
        code = self._make_active_code()
        req = self._make_request(self._valid_fingerprint())
        binding = bind_device(self.user, code, req)
        self.assertIsNotNone(binding.pk)
        self.assertEqual(binding.user, self.user)
        code.refresh_from_db()
        self.assertEqual(code.status, 'active')
        self.assertEqual(code.activation_count, 1)

    def test_second_device_rejected(self):
        """Un deuxième appareil différent doit être rejeté avec DeviceConflictException."""
        code = self._make_active_code()
        req1 = self._make_request('a' * 64)
        bind_device(self.user, code, req1)

        # Deuxième appareil avec fingerprint différent
        req2 = self._make_request('b' * 64)
        user2 = make_user(username='user2', email='u2@test.com', phone='+237699000002')
        with self.assertRaises(DeviceConflictException):
            bind_device(user2, code, req2)

    def test_same_device_second_login_accepted(self):
        """Le même appareil qui se reconnecte doit être accepté."""
        code = self._make_active_code()
        fp = self._valid_fingerprint()
        req = self._make_request(fp)
        bind_device(self.user, code, req)
        # Deuxième connexion avec le même fingerprint
        binding2 = bind_device(self.user, code, req)
        self.assertIsNotNone(binding2.pk)

    def test_fingerprint_mismatch_logout(self):
        """verify_device doit retourner False si le fingerprint est différent."""
        code = self._make_active_code()
        req1 = self._make_request('a' * 64)
        bind_device(self.user, code, req1)
        code.refresh_from_db()

        # Nouvelle requête avec fingerprint différent
        req2 = self._make_request('c' * 64)
        result = verify_device(self.user, code, req2)
        self.assertFalse(result)

    def test_verify_device_correct_fingerprint(self):
        """verify_device doit retourner True pour le bon fingerprint."""
        code = self._make_active_code()
        fp = 'a' * 64
        req = self._make_request(fp)
        bind_device(self.user, code, req)
        code.refresh_from_db()
        result = verify_device(self.user, code, req)
        self.assertTrue(result)


# ── TEST PAYMENT SERVICE ──────────────────────────────────────────

class TestPaymentService(TestCase):

    def setUp(self):
        self.plan = make_plan()
        self.user = make_user()

    def test_on_payment_confirmed_generates_code(self):
        """on_payment_confirmed doit générer un AccessCode après paiement."""
        tx = make_transaction(self.user, self.plan)
        tx.status = 'pending'
        tx.save()

        from edu_platform.services.payment_service import MobileMoneyService
        service = MobileMoneyService()

        with patch('edu_platform.services.notification_service.send_access_code_notification'):
            service.on_payment_confirmed(tx)

        tx.refresh_from_db()
        self.assertEqual(tx.status, 'confirmed')
        self.assertIsNotNone(tx.confirmed_at)
        self.assertTrue(hasattr(tx, 'access_code'))

    def test_duplicate_webhook_ignored(self):
        """Un webhook dupliqué sur une transaction déjà confirmée doit être ignoré."""
        tx = make_transaction(self.user, self.plan)
        tx.status = 'confirmed'
        tx.save()

        from edu_platform.services.payment_service import MobileMoneyService
        service = MobileMoneyService()

        with patch('edu_platform.services.code_generator.generate_access_code') as mock_gen:
            service.on_payment_confirmed(tx)
            mock_gen.assert_not_called()

    def test_orange_money_webhook_valid_signature(self):
        """verify_orange_money_webhook doit valider une signature HMAC correcte."""
        import json, hashlib, hmac as _hmac
        from edu_platform.services.payment_service import MobileMoneyService

        secret = 'test-secret-key'
        payload = {'order_id': 'abc123', 'status': 'SUCCESS'}
        expected_sig = _hmac.new(
            secret.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()

        with override_settings(EDU_PLATFORM={'WEBHOOK_HMAC_SECRET': secret}):
            service = MobileMoneyService()
            result = service.verify_orange_money_webhook(payload, expected_sig)

        self.assertTrue(result)

    def test_mtn_momo_callback_triggers_code_generation(self):
        """verify_mtn_momo_callback doit retourner True pour status SUCCESSFUL."""
        from edu_platform.services.payment_service import MobileMoneyService
        service = MobileMoneyService()
        self.assertTrue(service.verify_mtn_momo_callback({'status': 'SUCCESSFUL'}))
        self.assertFalse(service.verify_mtn_momo_callback({'status': 'FAILED'}))
        self.assertFalse(service.verify_mtn_momo_callback({}))
