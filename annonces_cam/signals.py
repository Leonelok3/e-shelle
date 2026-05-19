"""
signals.py — annonces_cam
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail

from .models import Annonce, StatutAnnonce, ProfilVendeur


@receiver(post_save, sender=Annonce)
def notifier_statut_annonce(sender, instance, created, **kwargs):
    """Email au vendeur quand une annonce est publiée ou refusée."""
    if not created:
        if instance.statut == StatutAnnonce.PUBLIEE:
            try:
                send_mail(
                    subject=f"✅ Votre annonce est en ligne — {instance.titre}",
                    message=(
                        f"Bonjour {instance.vendeur.get_full_name() or instance.vendeur.username},\n\n"
                        f"Votre annonce « {instance.titre} » est maintenant publiée sur E-Shelle Market.\n\n"
                        f"Bonne vente !\nL'équipe E-Shelle Market"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.vendeur.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        elif instance.statut == StatutAnnonce.REFUSEE:
            try:
                note = instance.note_admin or "Aucune note fournie."
                send_mail(
                    subject=f"❌ Annonce refusée — {instance.titre}",
                    message=(
                        f"Bonjour {instance.vendeur.get_full_name() or instance.vendeur.username},\n\n"
                        f"Votre annonce « {instance.titre} » a été refusée.\n"
                        f"Motif : {note}\n\n"
                        f"Contactez-nous pour plus d'informations.\nL'équipe E-Shelle Market"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.vendeur.email],
                    fail_silently=True,
                )
            except Exception:
                pass


_profil_ancien_compte = {}

@receiver(post_save, sender=ProfilVendeur, dispatch_uid="annonces_profil_save")
def mettre_en_avant_annonces_premium(sender, instance, created, **kwargs):
    """Met automatiquement en avant les annonces quand le compte passe en Premium."""
    if not created and instance.est_premium:
        ancien = _profil_ancien_compte.get(instance.pk)
        if ancien and ancien != "PREMIUM":
            instance.user.annonces.filter(statut=StatutAnnonce.PUBLIEE).update(est_mise_en_avant=True)
    _profil_ancien_compte[instance.pk] = instance.compte_type
