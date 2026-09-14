"""Effective entitlements: an expired subscription never grants access."""
from django.conf import settings
from django.utils import timezone


def active_subscription(profil):
    return profil.abonnements.filter(est_actif=True, date_fin__gt=timezone.now()).select_related('plan').first()


def entitlements(profil):
    abo = active_subscription(profil)
    cfg = getattr(settings, 'RENCONTRES_SETTINGS', {})
    values = dict(likes_par_jour=cfg.get('LIKES_PAR_JOUR_FREE', 15),
                  super_likes_par_jour=cfg.get('SUPER_LIKES_PAR_JOUR_FREE', 1),
                  messages_par_jour=cfg.get('MESSAGES_PAR_JOUR_FREE', -1),
                  photos_max=6, peut_voir_qui_a_like=False, peut_rembobiner=False,
                  boost_profil_par_semaine=0, filtre_avance=False,
                  mode_incognito=False, stats_profil=False)
    if abo:
        values.update({key: getattr(abo.plan, key) for key in values})
    return values


def sync_premium(profil):
    active = active_subscription(profil) is not None
    if profil.est_premium != active:
        type(profil).objects.filter(pk=profil.pk).update(est_premium=active)
        profil.est_premium = active
    return active


def can_interact(a, b):
    return (a.pk != b.pk and a.est_actif and b.est_actif
            and a.user.is_active and b.user.is_active and a.age() >= 18 and b.age() >= 18
            and not a.a_bloque(b) and not a.est_bloque_par(b))
