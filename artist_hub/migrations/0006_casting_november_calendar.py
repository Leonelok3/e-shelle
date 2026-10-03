import datetime
from zoneinfo import ZoneInfo
from django.db import migrations


def update_calendar(apps, schema_editor):
    Session = apps.get_model("artist_hub", "CastingSession")
    Session.objects.using(schema_editor.connection.alias).filter(slug="douala-fashion-week-2026").update(
        casting_date=datetime.date(2026, 11, 14),
        event_date=datetime.date(2026, 12, 26),
        closes_at=datetime.datetime(2026, 11, 13, 23, 59, 59, tzinfo=ZoneInfo("Africa/Douala")),
        subtitle="Casting : 14 novembre 2026 · Défilé : 26 décembre 2026 — Hôtel Krystal Palace Douala",
        description="Casting gratuit OPLUS / GROUP OPUS : les candidats inscrits participent au casting le 14 novembre 2026. Les profils retenus par le jury participeront au défilé de la Douala Fashion Week le 26 décembre 2026 à l’Hôtel Krystal Palace, Douala. Les horaires et le lieu du casting seront précisés par l’organisation.",
    )


class Migration(migrations.Migration):
    dependencies = [("artist_hub", "0005_castingsession_casting_date")]
    operations = [migrations.RunPython(update_calendar, migrations.RunPython.noop)]
