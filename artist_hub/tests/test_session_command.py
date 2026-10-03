import datetime
from io import StringIO
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from artist_hub.models import CastingSession


class SessionCommandTests(TestCase):
    def test_extend_existing_session_preserves_event_configuration(self):
        session = CastingSession.objects.create(
            slug="douala-fashion-week-2026", title="Titre personnalisé",
            fee_cameroon=4000, is_active=False,
            closes_at=datetime.datetime(2026, 9, 28, tzinfo=ZoneInfo("Africa/Douala")),
        )
        call_command("init_casting_session", stdout=StringIO())
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertEqual(session.closes_at.month, 9)

        call_command("init_casting_session", extend_registration=True, stdout=StringIO())
        session.refresh_from_db()
        self.assertEqual(session.closes_at, datetime.datetime(
            2026, 11, 13, 23, 59, 59, tzinfo=ZoneInfo("Africa/Douala")))
        self.assertEqual(session.casting_date, datetime.date(2026, 11, 14))
        self.assertEqual(session.event_date, datetime.date(2026, 12, 26))
        self.assertTrue(session.is_open)
        self.assertEqual(session.title, "Titre personnalisé")
        self.assertEqual(session.fee_cameroon, 4000)

    def test_calendar_migration_only_updates_official_session(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        official = CastingSession.objects.create(slug="douala-fashion-week-2026", title="OPLUS")
        other = CastingSession.objects.create(slug="other-event", title="Autre casting")
        import_module("artist_hub.migrations.0006_casting_november_calendar").update_calendar(apps, SimpleNamespace(connection=connection))
        official.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(official.casting_date, datetime.date(2026, 11, 14))
        self.assertEqual(official.event_date, datetime.date(2026, 12, 26))
        self.assertEqual(official.closes_at, datetime.datetime(2026, 11, 13, 23, 59, 59, tzinfo=ZoneInfo("Africa/Douala")))
        self.assertIsNone(other.casting_date)
