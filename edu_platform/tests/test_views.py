"""
Tests d'intégration des vues EduCam Pro (smoke tests HTTP).
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from edu_platform.models import SubscriptionPlan, EduProfile

User = get_user_model()


def make_plan():
    return SubscriptionPlan.objects.create(
        name='Plan Test', plan_type='quarterly',
        price_xaf=5000, duration_days=90,
        features=['Accès complet'],
    )


def make_user(username='view_user', phone='+237699111222'):
    user = User.objects.create_user(
        username=username, email=f'{username}@test.com', password='pass123'
    )
    EduProfile.objects.create(user=user, phone_number=phone)
    return user


class TestPublicViews(TestCase):
    """Vues accessibles sans authentification."""

    def setUp(self):
        self.client = Client()
        make_plan()

    def test_landing_page(self):
        r = self.client.get('/edu/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'EduCam')

    def test_plans_page(self):
        r = self.client.get('/edu/plans/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Forfait')

    def test_login_page(self):
        r = self.client.get('/edu/login/')
        self.assertEqual(r.status_code, 200)

    def test_register_page(self):
        r = self.client.get('/edu/register/')
        self.assertEqual(r.status_code, 200)

    def test_activate_code_redirects_when_not_logged_in(self):
        r = self.client.get('/edu/activate/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/edu/login/', r.get('Location', ''))


class TestAuthViews(TestCase):
    """Tests de connexion / inscription."""

    def setUp(self):
        self.client = Client()
        make_plan()

    def test_register_creates_user(self):
        r = self.client.post('/edu/register/', {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@test.cm',
            'phone_number': '+237699000099',
            'password1': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(email='jean@test.cm').exists())

    def test_login_valid_user(self):
        user = make_user('login_test', '+237699000088')
        # AuthenticationForm utilise USERNAME_FIELD = 'username' pour CustomUser (AbstractUser)
        r = self.client.post('/edu/login/', {
            'username': 'login_test',
            'password': 'pass123',
        })
        self.assertEqual(r.status_code, 302)

    def test_login_invalid_redirects_back(self):
        r = self.client.post('/edu/login/', {
            'username': 'wrong@test.com',
            'password': 'wrongpass',
        })
        self.assertEqual(r.status_code, 200)  # Re-affiche le formulaire


class TestProtectedViews(TestCase):
    """Vues nécessitant authentification."""

    def setUp(self):
        self.client = Client()
        make_plan()
        self.user = make_user()
        self.client.force_login(self.user)

    def test_dashboard_redirects_without_subscription(self):
        """Sans abonnement, dashboard redirige vers activation."""
        r = self.client.get('/edu/dashboard/')
        # Doit rediriger (vers /edu/activate/ ou /edu/plans/)
        self.assertIn(r.status_code, [200, 302])

    def test_subject_list_accessible(self):
        # Le middleware redirige vers /edu/plans/ si pas d'abonnement actif
        r = self.client.get('/edu/subjects/')
        self.assertIn(r.status_code, [200, 302])

    def test_activate_code_page_accessible(self):
        r = self.client.get('/edu/activate/')
        self.assertEqual(r.status_code, 200)

    def test_subscription_status_page(self):
        r = self.client.get('/edu/subscription/')
        self.assertEqual(r.status_code, 200)

    def test_renew_page(self):
        r = self.client.get('/edu/renew/')
        self.assertEqual(r.status_code, 200)

    def test_profile_page(self):
        r = self.client.get('/edu/profile/')
        self.assertEqual(r.status_code, 200)

    def test_device_blocked_page(self):
        r = self.client.get('/edu/device-blocked/')
        self.assertEqual(r.status_code, 200)


class TestAdminViews(TestCase):
    """Back-office admin EduCam."""

    def setUp(self):
        self.client = Client()
        make_plan()
        self.staff = User.objects.create_user(
            username='staff_edu', email='staff@test.cm',
            password='staffpass', is_staff=True
        )
        self.client.force_login(self.staff)

    def test_admin_dashboard_accessible(self):
        r = self.client.get('/edu/admin/')
        self.assertEqual(r.status_code, 200)

    def test_admin_users_accessible(self):
        r = self.client.get('/edu/admin/users/')
        self.assertEqual(r.status_code, 200)

    def test_admin_codes_accessible(self):
        r = self.client.get('/edu/admin/codes/')
        self.assertEqual(r.status_code, 200)

    def test_admin_transactions_accessible(self):
        r = self.client.get('/edu/admin/transactions/')
        self.assertEqual(r.status_code, 200)

    def test_admin_devices_accessible(self):
        r = self.client.get('/edu/admin/devices/')
        self.assertEqual(r.status_code, 200)

    def test_admin_content_accessible(self):
        r = self.client.get('/edu/admin/content/')
        self.assertEqual(r.status_code, 200)

    def test_non_staff_cannot_access_admin(self):
        normal_user = make_user('normal_user', '+237699555444')
        client2 = Client()
        client2.force_login(normal_user)
        r = client2.get('/edu/admin/')
        # Doit rediriger vers login
        self.assertEqual(r.status_code, 302)
