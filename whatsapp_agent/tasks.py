from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone

from .models import Campagne, MessageEnvoi
from .services import WhatsAppService


def recalculer_stats_campagne(campagne: Campagne):
    """Met a jour les compteurs a partir des messages reels."""

    stats = campagne.messages.aggregate(
        total=Count("id"),
        envoyes=Count("id", filter=Q(statut__in=["envoye", "livre", "lu"])),
        livres=Count("id", filter=Q(statut__in=["livre", "lu"])),
        lus=Count("id", filter=Q(statut="lu")),
        echecs=Count("id", filter=Q(statut="echec")),
    )
    campagne.total_destinataires = stats["total"] or 0
    campagne.total_envoyes = stats["envoyes"] or 0
    campagne.total_livres = stats["livres"] or 0
    campagne.total_lus = stats["lus"] or 0
    campagne.total_echecs = stats["echecs"] or 0
    campagne.save(
        update_fields=[
            "total_destinataires",
            "total_envoyes",
            "total_livres",
            "total_lus",
            "total_echecs",
        ]
    )


def _traiter_message_direct(msg: MessageEnvoi):
    """Traite un message sans Celery, utile en local et en simulation."""

    result = WhatsAppService.envoyer_message(msg.numero_whatsapp, msg.message_final)
    if result["success"]:
        msg.statut = MessageEnvoi.STATUT_ENVOYE
        msg.whatsapp_message_id = result["message_id"]
        msg.erreur = ""
        msg.envoye_le = timezone.now()
        msg.save(update_fields=["statut", "whatsapp_message_id", "erreur", "envoye_le", "mis_a_jour_le"])
    else:
        msg.statut = MessageEnvoi.STATUT_ECHEC
        msg.erreur = result["erreur"]
        msg.save(update_fields=["statut", "erreur", "mis_a_jour_le"])


def lancer_campagne_direct(campagne_id: int):
    """Lance une campagne sans broker Celery, pour les tests locaux."""

    campagne = Campagne.objects.get(id=campagne_id)
    if campagne.statut not in [Campagne.STATUT_VALIDEE, Campagne.STATUT_EN_COURS]:
        return

    campagne.statut = Campagne.STATUT_EN_COURS
    campagne.lance_le = timezone.now()
    campagne.save(update_fields=["statut", "lance_le"])

    messages = list(campagne.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).order_by("id"))
    for msg in messages:
        _traiter_message_direct(msg)

    recalculer_stats_campagne(campagne)
    campagne.refresh_from_db()
    if not campagne.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).exists():
        campagne.statut = Campagne.STATUT_TERMINEE
        campagne.termine_le = timezone.now()
        campagne.save(update_fields=["statut", "termine_le"])


@shared_task(bind=True, max_retries=2)
def envoyer_message_task(self, message_envoi_id: int):
    """Envoie un seul message et reessaie deux fois en cas d'echec temporaire."""

    msg = MessageEnvoi.objects.select_related("campagne").get(id=message_envoi_id)
    result = WhatsAppService.envoyer_message(msg.numero_whatsapp, msg.message_final)

    if result["success"]:
        msg.statut = MessageEnvoi.STATUT_ENVOYE
        msg.whatsapp_message_id = result["message_id"]
        msg.erreur = ""
        msg.envoye_le = timezone.now()
        msg.save(update_fields=["statut", "whatsapp_message_id", "erreur", "envoye_le", "mis_a_jour_le"])
    else:
        msg.erreur = result["erreur"]
        if self.request.retries < self.max_retries:
            msg.save(update_fields=["erreur", "mis_a_jour_le"])
            raise self.retry(countdown=60)
        msg.statut = MessageEnvoi.STATUT_ECHEC
        msg.save(update_fields=["statut", "erreur", "mis_a_jour_le"])

    recalculer_stats_campagne(msg.campagne)
    campagne = Campagne.objects.get(pk=msg.campagne_id)
    restants = campagne.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).exists()
    if not restants and campagne.statut == Campagne.STATUT_EN_COURS:
        campagne.statut = Campagne.STATUT_TERMINEE
        campagne.termine_le = timezone.now()
        campagne.save(update_fields=["statut", "termine_le"])


@shared_task
def lancer_campagne_task(campagne_id: int):
    """Lance l'envoi de toute la campagne par lots controles."""

    campagne = Campagne.objects.get(id=campagne_id)
    if campagne.statut not in [Campagne.STATUT_VALIDEE, Campagne.STATUT_EN_COURS]:
        return

    campagne.statut = Campagne.STATUT_EN_COURS
    campagne.lance_le = timezone.now()
    campagne.save(update_fields=["statut", "lance_le"])

    messages = campagne.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).order_by("id")
    if not messages.exists():
        campagne.statut = Campagne.STATUT_TERMINEE
        campagne.termine_le = timezone.now()
        campagne.save(update_fields=["statut", "termine_le"])
        return

    for index, msg in enumerate(messages):
        # Le countdown espace l'envoi sans bloquer le worker pendant une minute.
        countdown = (index // 80) * 60
        envoyer_message_task.apply_async(args=[msg.id], countdown=countdown)
