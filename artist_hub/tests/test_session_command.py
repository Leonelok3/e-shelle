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
            2026, 12, 25, 23, 59, 59, tzinfo=ZoneInfo("Africa/Douala")))
        self.assertTrue(session.is_open)
        self.assertEqual(session.title, "Titre personnalisé")
        self.assertEqual(session.fee_cameroon, 4000)
