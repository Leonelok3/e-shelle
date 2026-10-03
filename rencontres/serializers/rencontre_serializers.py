"""
Serializers légers pour les endpoints AJAX/JSON.
Pas de DRF requis — utilise des dicts simples.
"""


def serialize_profil_card(profil, score=None, distance_km=None):
    """Sérialise un profil pour une carte de découverte."""
    return {
        'id': profil.id,
        'prenom': profil.prenom_affiche,
        'age': profil.age(),
        'ville': profil.ville,
        'pays': profil.pays_actuel,
        'profession': profil.profession,
        'biographie': profil.biographie[:200] if profil.biographie else '',
        'religion': profil.get_religion_display() if profil.religion else '',
        'langues': profil.langues[:3] if profil.langues else [],
        'interets': profil.interets[:5] if profil.interets else [],
        'est_premium': profil.est_premium,
        'badge_verifie': profil.badge_verifie,
        'photo': profil.photo_principale.url if profil.photo_principale else '',
        'score': score,
        'distance_km': distance_km,
        'profil_url': f'/rencontres/profil/{profil.id}/',
    }


def serialize_message(message, mon_profil_id):
    """Sérialise un message pour l'affichage en temps réel."""
    return {
        'id': message.id,
        'contenu': message.contenu,
        'type_message': message.type_message,
        'date_envoi': message.date_envoi.isoformat(),
        'est_moi': message.expediteur_id == mon_profil_id,
        'est_lu': message.est_lu,
        'expediteur_prenom': message.expediteur.prenom_affiche,
    }


def serialize_match(match, mon_profil):
    """Sérialise un match pour la liste."""
    autre = match.get_other_profil(mon_profil)
    dernier_msg = None
    if hasattr(match, 'conversation'):
        msg = match.conversation.messages.order_by('-date_envoi').first()
        if msg:
            dernier_msg = {
                'contenu': msg.contenu[:100],
                'date': msg.date_envoi.isoformat(),
                'est_moi': msg.expediteur == mon_profil,
            }
    return {
        'id': match.id,
        'autre_profil': serialize_profil_card(autre),
        'date_match': match.date_match.isoformat(),
        'score_compatibilite': match.score_compatibilite,
        'conversation_id': match.conversation.id if hasattr(match, 'conversation') else None,
        'dernier_message': dernier_msg,
    }
