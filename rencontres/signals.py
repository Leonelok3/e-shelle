"""
Signaux Django pour l'app rencontres.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='rencontres.AbonnementRencontre')
def update_profil_premium_status(sender, instance, **kwargs):
    """Met à jour le statut premium du profil lors d'un changement d'abonnement."""
    profil = instance.profil
    from django.utils import timezone
    is_premium = sender.objects.filter(
        profil=profil,
        est_actif=True,
        date_fin__gt=timezone.now(),
    ).exists()
    if profil.est_premium != is_premium:
        profil.est_premium = is_premium
        profil.save(update_fields=['est_premium'])


from django.db.models.signals import post_delete


@receiver(post_save, sender='rencontres.PhotoProfil')
@receiver(post_delete, sender='rencontres.PhotoProfil')
def sync_main_photo(sender, instance, **kwargs):
    from rencontres.models import ProfilRencontre
    profil = ProfilRencontre.objects.filter(pk=instance.profil_id).first()
    if not profil:
        return
    photo = profil.photos.filter(est_approuvee=True).order_by('-est_principale', 'ordre', 'pk').first()
    name = photo.image.name if photo else ''
    ProfilRencontre.objects.filter(pk=profil.pk).update(photo_principale=name)
    if photo:
        profil.photos.exclude(pk=photo.pk).update(est_principale=False)
        profil.photos.filter(pk=photo.pk).update(est_principale=True)
    profil.photo_principale = name
    profil.calculer_completion()
