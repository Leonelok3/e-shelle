from django.db import migrations, models


def publish_pending_photos(apps, schema_editor):
    Photo = apps.get_model('rencontres', 'PhotoProfil')
    Profile = apps.get_model('rencontres', 'ProfilRencontre')
    alias = schema_editor.connection.alias
    profiles = list(Photo.objects.using(alias).filter(est_approuvee=False)
                    .values_list('profil_id', flat=True).distinct())
    Photo.objects.using(alias).filter(est_approuvee=False).update(est_approuvee=True)
    for profile in Profile.objects.using(alias).filter(pk__in=profiles).iterator():
        photos = Photo.objects.using(alias).filter(profil_id=profile.pk)
        main = photos.order_by('-est_principale', 'ordre', 'pk').first()
        photos.exclude(pk=main.pk).update(est_principale=False)
        photos.filter(pk=main.pk).update(est_principale=True)
        fields = [profile.prenom_affiche, profile.biographie, profile.profession,
                  main.image.name, profile.origine_ethnique,
                  profile.ce_que_je_cherche, bool(profile.interets)]
        Profile.objects.using(alias).filter(pk=profile.pk).update(
            photo_principale=main.image.name,
            profil_complet=int(sum(bool(value) for value in fields) / len(fields) * 100))


class Migration(migrations.Migration):
    dependencies = [('rencontres', '0006_profilrencontre_boost_fin_and_more')]
    operations = [
        migrations.AlterField(model_name='photoprofil', name='est_approuvee',
                              field=models.BooleanField(default=True)),
        migrations.RunPython(publish_pending_photos, migrations.RunPython.noop),
    ]
