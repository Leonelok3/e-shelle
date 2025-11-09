from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from radar.models import Source, Opportunity

User = get_user_model()

class RadarApiTests(APITestCase):
    def setUp(self):
        self.src = Source.objects.create(code="TEST", name="Test", url="https://example.com")
        Opportunity.objects.create(
            title="Test opp", country="Canada", category="work", is_scholarship=False,
            url="https://example.com/1", source=self.src, score=77, hash="h"*64
        )
        self.user = User.objects.create_user(username="u", password="p")

    def test_list_opportunities(self):
        url = reverse("opportunities")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data["results"]), 1)

    def test_create_subscription_requires_auth(self):
        url = reverse("subscriptions")
        r = self.client.post(url, {"country_filter":"Canada"})
        self.assertEqual(r.status_code, 403)
        self.client.login(username="u", password="p")
        r = self.client.post(url, {"country_filter":"Canada","category_filter":"work","min_score":60})
        self.assertEqual(r.status_code, 201)
