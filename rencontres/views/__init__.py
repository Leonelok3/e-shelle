from .profile_views import (
    accueil_rencontre, creer_profil, modifier_profil,
    detail_profil, gerer_photos, parametres_rencontre,
    desactiver_compte_rencontre,
)
from .discovery_views import decouverte, filtres, ajax_like, ajax_passer, ajax_charger_profils
from .match_views import liste_matchs, detail_match, popup_nouveau_match, qui_maime
from .messaging_views import (
    inbox, conversation, ajax_envoyer_message, ajax_marquer_lu,
    ajax_check_notifications,
)
from .premium_views import page_premium, souscrire_premium, activer_boost, ajax_stats_profil
from .moderation_views import bloquer_profil, signaler_profil, moderation_photos
from .coach_views import coach_love
from .seo_views import seo_landing

__all__ = [
    'accueil_rencontre', 'creer_profil', 'modifier_profil',
    'detail_profil', 'gerer_photos', 'parametres_rencontre', 'desactiver_compte_rencontre',
    'decouverte', 'filtres', 'ajax_like', 'ajax_passer', 'ajax_charger_profils',
    'liste_matchs', 'detail_match', 'popup_nouveau_match', 'qui_maime',
    'inbox', 'conversation', 'ajax_envoyer_message', 'ajax_marquer_lu',
    'ajax_check_notifications',
    'page_premium', 'souscrire_premium', 'activer_boost', 'ajax_stats_profil',
    'bloquer_profil', 'signaler_profil', 'moderation_photos',
    'coach_love', 'seo_landing',
]
