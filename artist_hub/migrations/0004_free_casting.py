from django.db import migrations


def make_casting_free(apps, schema_editor):
    Session = apps.get_model("artist_hub", "CastingSession")
    Candidate = apps.get_model("artist_hub", "Candidate")
    alias = schema_editor.connection.alias
    Session.objects.using(alias).all().update(
        fee_cameroon=0, fee_international=0,
        rules="Le casting est gratuit. L’inscription ne garantit pas la sélection finale. Les mineurs doivent fournir l’autorisation de leur tuteur. Les photos et vidéos doivent être récentes et fidèles.",
    )
    Candidate.objects.using(alias).filter(status__in=["EN_ATTENTE_PAIEMENT", "EN_ATTENTE_VALIDATION"]).update(status="INSCRIT")


class Migration(migrations.Migration):
    dependencies = [("artist_hub", "0003_alter_candidate_status_and_more")]
    operations = [migrations.RunPython(make_casting_free, migrations.RunPython.noop)]
