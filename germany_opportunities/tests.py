from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AusbildungOffer, UserOpportunityBookmark


class GermanyOpportunitiesViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="secret123")
        self.offer_berlin = AusbildungOffer.objects.create(
            ref_nr="BA-001",
            title="Pflegefachkraft im Krankenhaus",
            company="Klinikum Berlin",
            city="Berlin",
            region="Berlin",
            sector="gesundheit",
            language_req="B2",
            salary_month="1800 EUR",
            description="Position en soins infirmiers.",
            url_apply="https://example.com/apply/1",
        )
        self.offer_hamburg = AusbildungOffer.objects.create(
            ref_nr="BA-002",
            title="IT Support Fachkraft",
            company="Tech Hamburg",
            city="Hamburg",
            region="Hamburg",
            sector="it",
            language_req="B1",
            salary_month="1600 EUR",
            description="Support informatique.",
            url_apply="https://example.com/apply/2",
        )

    def test_catalogue_supports_region_and_sort_filters(self):
        response = self.client.get(
            reverse("germany_opportunities:catalogue"),
            {"region": "Berlin", "sort": "soonest"},
        )

        self.assertEqual(response.status_code, 200)
        offers = list(response.context["offers"])
        self.assertEqual(offers, [self.offer_berlin])
        self.assertContains(response, "Berlin")

    def test_toggle_bookmark_returns_state_and_count(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("germany_opportunities:toggle_bookmark", args=[self.offer_berlin.pk])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "saved")
        self.assertTrue(payload["bookmarked"])
        self.assertEqual(payload["bookmark_count"], 1)

        bookmark = UserOpportunityBookmark.objects.get(user=self.user, offer=self.offer_berlin)
        self.assertFalse(bookmark.applied)
