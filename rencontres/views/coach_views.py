from django.shortcuts import get_object_or_404, render
from django.db.models import Q

from rencontres.models import Conversation, Match, ProfilRencontre
from rencontres.utils.love_coach import (
    compatibility_notes,
    first_messages,
    improve_bio,
    profile_advice,
)
from rencontres.views.profile_views import profil_requis


@profil_requis
def coach_love(request):
    profil = request.user.profil_rencontre
    target = None
    conversation = None

    target_id = request.GET.get("profil")
    conversation_id = request.GET.get("conversation")

    if conversation_id:
        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            match__in=Match.objects.filter(Q(profil_1=profil) | Q(profil_2=profil)),
        )
        target = conversation.get_other_profil(profil)
    elif target_id:
        target = get_object_or_404(ProfilRencontre, pk=target_id, est_actif=True)

    context = {
        "profil": profil,
        "target": target,
        "conversation": conversation,
        "bio_amelioree": improve_bio(profil),
        "conseils": profile_advice(profil),
        "messages": first_messages(profil, target) if target else [],
        "compatibilite": compatibility_notes(profil, target) if target else [],
    }
    return render(request, "rencontres/coach.html", context)
