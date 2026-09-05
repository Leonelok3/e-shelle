from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from jobs.canada_validation import check_offer, parse_deadline
from jobs.models import CanadaJobOffer

URL = "https://www.jobbank.gc.ca/jobsearch/jobposting/123"


class SourceTests(SimpleTestCase):
    def response(self, text, code=200):
        response = MagicMock(status_code=code, text=text)
        response.__enter__.return_value = response
        return response

    @patch("jobs.canada_validation.requests.get")
    def test_retired_page_with_success_status(self, get):
        for text in ("<h1>Job posting no longer advertised</h1>",
                     "Cette offre d’emploi n’est plus disponible"):
            get.return_value = self.response(text)
            self.assertEqual(check_offer(URL)[0], "expired")

    @patch("jobs.canada_validation.requests.get")
    def test_transient_errors_and_generic_pages_are_unknown(self, get):
        for code in (200, 403, 429, 500, 503):
            get.return_value = self.response("Please try again", code)
            self.assertEqual(check_offer(URL)[0], "unknown")
        get.side_effect = requests.Timeout()
        self.assertEqual(check_offer(URL)[0], "unknown")

    @patch("jobs.canada_validation.requests.get")
    def test_source_deadline_and_not_found(self, get):
        get.return_value = self.response("Publiée jusqu’au 2026-12-05")
        self.assertEqual(check_offer(URL)[2].isoformat(), "2026-12-05")
        get.return_value = self.response("", 410)
        self.assertEqual(check_offer(URL)[0], "expired")

    def test_complete_dates_only(self):
        self.assertEqual(parse_deadline("2026-09-05").isoformat(), "2026-09-05")
        self.assertEqual(parse_deadline("5 février 2026").isoformat(), "2026-02-05")
        for value in ("05/09/2026", "septembre", "Non précisé", "2026-02-30"):
            self.assertIsNone(parse_deadline(value))

    @patch("jobs.canada_validation.requests.get")
    def test_untrusted_hosts_not_requested(self, get):
        self.assertEqual(check_offer("https://jobbank.gc.ca.evil.test/a")[0], "unknown")
        get.assert_not_called()


class CleanupTests(TestCase):
    def offer(self, ref, deadline=""):
        return CanadaJobOffer.objects.create(ref_nr=ref, title="Test", company="Test", url_apply=URL, deadline=deadline)

    @patch("jobs.management.commands.clean_expired_canada_jobs.check_offer")
    def test_delete_expired_hide_unknown_and_restore_valid(self, check):
        expired = self.offer("expired", (timezone.localdate() - timedelta(days=1)).isoformat())
        pending = self.offer("pending")
        check.return_value = ("unknown", "Timeout", None)
        call_command("clean_expired_canada_jobs", stdout=StringIO())
        self.assertFalse(CanadaJobOffer.objects.filter(pk=expired.pk).exists())
        pending.refresh_from_db()
        self.assertFalse(pending.is_active)
        check.return_value = ("active", "Verified", None)
        call_command("clean_expired_canada_jobs", stdout=StringIO())
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)

    @patch("jobs.management.commands.clean_expired_canada_jobs.check_offer")
    def test_dry_run_preserves_rows(self, check):
        offer = self.offer("test")
        check.return_value = ("expired", "Removed", None)
        call_command("clean_expired_canada_jobs", dry_run=True, stdout=StringIO())
        self.assertTrue(CanadaJobOffer.objects.filter(pk=offer.pk, is_active=True).exists())


class DailyTaskTests(SimpleTestCase):
    @patch("jobs.tasks.call_command")
    @patch("jobs.tasks.log")
    def test_generation_failures_propagate_to_celery(self, log, command):
        from jobs import tasks
        command.side_effect = RuntimeError("Source unavailable")
        for task in (tasks.fetch_canada_jobs_task, tasks.fetch_canada_scholarships_task,
                     tasks.fetch_canada_visitor_opps_task, tasks.fetch_canada_news_task):
            with self.assertRaises(RuntimeError):
                task.run()
