from django.db import migrations
import uuid


def fill_public_ids(apps, schema_editor):
    CEFRCertificate = apps.get_model("preparation_tests", "CEFRCertificate")

    for cert in CEFRCertificate.objects.filter(public_id__isnull=True):
        cert.public_id = uuid.uuid4().hex[:12].upper()
        cert.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("preparation_tests", "0020_remove_cefrcertificate_certificate_id_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_public_ids),
    ]
