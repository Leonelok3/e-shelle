from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
import requests

from .availability import available_offers, available_scholarships, clean_unavailable
from .models import AusbildungOffer, ScholarshipOpportunity, UserOpportunityBookmark
from .source_checks import source_expired


class AvailabilityTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.old = AusbildungOffer.objects.create(ref_nr="old", title="Old", company="Test", city="Berlin", start_date=self.today-timedelta(days=1))
        self.current = AusbildungOffer.objects.create(ref_nr="current", title="Current", company="Test", city="Berlin", start_date=self.today)

    def test_expiry_boundary_and_stale_offers(self):
        self.assertEqual(list(available_offers()), [self.current])
        AusbildungOffer.objects.filter(pk=self.current.pk).update(last_seen=timezone.now()-timedelta(days=8))
        self.assertFalse(available_offers().exists())

    def test_scholarships_exclude_expired_and_undated(self):
        for deadline in (self.today-timedelta(days=1), self.today, None):
            ScholarshipOpportunity.objects.create(title="Test", provider="DAAD", level="master", deadline=deadline)
        self.assertEqual(available_scholarships().count(), 1)
        clean_unavailable()
        self.assertEqual(ScholarshipOpportunity.objects.count(), 3)
        self.assertEqual(ScholarshipOpportunity.objects.filter(is_active=True).count(), 1)

    def test_cleanup_preserves_bookmarks_and_application_history(self):
        user = get_user_model().objects.create_user(username="history")
        bookmark = UserOpportunityBookmark.objects.create(user=user, offer=self.old, applied=True)
        clean_unavailable()
        self.old.refresh_from_db()
        bookmark.refresh_from_db()
        self.assertFalse(self.old.is_active)
        self.assertTrue(bookmark.applied)
        self.assertEqual(bookmark.offer_id, self.old.pk)

    def test_dry_run_does_not_modify(self):
        self.assertEqual(clean_unavailable(True)["offers_hidden"], 1)
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_active)

    def test_expired_detail_returns_404_before_ai(self):
        from .views import offer_detail
        with self.assertRaises(Http404):
            offer_detail(RequestFactory().get("/"), self.old.pk)

    @patch("germany_opportunities.tasks.requests.get")
    def test_total_import_failure_is_reported_without_deleting_history(self, get):
        from .tasks import fetch_ausbildung_offers
        get.return_value.status_code = 403
        with self.assertRaises(RuntimeError):
            fetch_ausbildung_offers.run()
        self.assertTrue(AusbildungOffer.objects.filter(pk=self.old.pk).exists())


class SourceTests(SimpleTestCase):
    @patch("germany_opportunities.source_checks.requests.get")
    def test_withdrawal_and_transient_failure(self, get):
        response = MagicMock(status_code=200, text="Dieses Stellenangebot ist nicht mehr verfügbar")
        response.__enter__.return_value = response
        get.return_value = response
        self.assertTrue(source_expired("https://www.arbeitsagentur.de/jobsuche/jobdetail/1"))
        response.status_code = 503
        self.assertIsNone(source_expired("https://www.daad.de/test"))
        get.side_effect = requests.Timeout()
        self.assertIsNone(source_expired("https://www.daad.de/test"))

    @patch("germany_opportunities.source_checks.requests.get")
    def test_external_redirect_not_followed(self, get):
        response = MagicMock(status_code=302, headers={"Location": "http://127.0.0.1/private"})
        response.__enter__.return_value = response
        get.return_value = response
        self.assertIsNone(source_expired("https://www.daad.de/test"))
        self.assertEqual(get.call_count, 1)
