"""
Utilitaires de notifications pour l'app rencontres.
Utilise le polling AJAX (sans Django Channels).
"""
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


def get_stats_notifications(profil):
    """Retourne les compteurs de notifications pour le polling AJAX."""
    from rencontres.models import Message, Match, Like

    nouveaux_messages = Message.objects.filter(
        conversation__match__in=profil.get_matchs_actifs(),
        est_lu=False
    ).exclude(expediteur=profil).count()

    nouveaux_matchs = Match.objects.filter(
        Q(profil_1=profil) | Q(profil_2=profil),
        date_match__gte=timezone.now() - timedelta(hours=24)
    ).count()

    nouveaux_likes = 0
    if profil.est_premium:
        nouveaux_likes = Like.objects.filter(
            recepteur=profil, est_lu=False
        ).count()

    return {
        'nouveaux_messages': nouveaux_messages,
        'nouveaux_matchs': nouveaux_matchs,
        'nouveaux_likes': nouveaux_likes,
        'total': nouveaux_messages + nouveaux_matchs + nouveaux_likes,
    }


def verifier_limite_likes(profil, type_like='like'):
    """
    Vérifie si le profil peut encore liker aujourd'hui.
    Retourne (peut_liker, likes_restants).
    """
    from rencontres.models import Like
    from django.conf import settings

    if profil.est_premium:
        return True, -1  # illimité pour premium

    settings_rencontres = getattr(settings, 'RENCONTRES_SETTINGS', {})
    if type_like == 'super_like':
        limite = settings_rencontres.get('SUPER_LIKES_PAR_JOUR_FREE', 1)
        filters = {'type_like': 'super_like'}
    else:
        limite = settings_rencontres.get('LIKES_PAR_JOUR_FREE', 5)
        filters = {}

    aujourd_hui = timezone.now().date()
    likes_aujourd_hui = Like.objects.filter(
        envoyeur=profil,
        date_like__date=aujourd_hui,
        **filters,
    ).count()

    restants = max(0, limite - likes_aujourd_hui)
    return restants > 0, restants


def verifier_limite_messages(profil):
    """
    Vérifie si le profil peut encore envoyer des messages aujourd'hui.
    Retourne (peut_envoyer, messages_restants).
    """
    from rencontres.models import Message
    from django.conf import settings

    if profil.est_premium:
        return True, -1

    limite = getattr(settings, 'RENCONTRES_SETTINGS', {}).get('MESSAGES_PAR_JOUR_FREE', 5)
    aujourd_hui = timezone.now().date()
    messages_aujourd_hui = Message.objects.filter(
        expediteur=profil,
        date_envoi__date=aujourd_hui
    ).count()

    restants = max(0, limite - messages_aujourd_hui)
    return restants > 0, restants


def verifier_spam(profil, conversation):
    """
    Détecte le spam : 10 messages identiques en moins de 5 min.
    Retourne True si spam détecté.
    """
    from rencontres.models import Message
    cinq_minutes_ago = timezone.now() - timedelta(minutes=5)
    messages_recents = Message.objects.filter(
        expediteur=profil,
        conversation=conversation,
        date_envoi__gte=cinq_minutes_ago
    )
    if messages_recents.count() >= 10:
        return True
    return False
