"""
Coach Love local.

Version sans API externe : produit des suggestions utiles a partir des champs
de profil existants. Le jour ou un moteur IA est branche, cette couche pourra
devenir le fallback en cas d'indisponibilite.
"""


def _join(items, fallback="vos centres d'interet"):
    items = [str(x) for x in (items or []) if x]
    if not items:
        return fallback
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " et " + items[-1]


def improve_bio(profil):
    interests = _join(profil.interets, "les conversations simples")
    values = profil.ce_que_je_cherche or "une relation serieuse, respectueuse et stable"
    job = f"{profil.profession}, " if profil.profession else ""
    return (
        f"Je suis {profil.prenom_affiche}, {job}une personne sincere, posee et ouverte. "
        f"J'aime {interests}. Je recherche {values.lower()}. "
        "J'apprecie les personnes respectueuses, honnetes, capables de construire une relation claire."
    )


def first_messages(my_profile, target_profile):
    target_interests = target_profile.interets or []
    target_interest = target_interests[0] if target_interests else "ton profil"
    city = target_profile.ville
    common_languages = sorted(set(my_profile.langues or []) & set(target_profile.langues or []))
    if my_profile.pays_actuel.casefold() != target_profile.pays_actuel.casefold():
        shared = f"On parle tous les deux {common_languages[0]}. " if common_languages else ''
        return [
            f"Bonjour {target_profile.prenom_affiche}, {shared}j’aimerais découvrir ton quotidien à {city}. "
            "Qu’est-ce que tu aimes le plus dans la ville où tu vis ?",
            f"Salut {target_profile.prenom_affiche}, j’ai remarqué {target_interest} dans ton profil. "
            "Qu’est-ce qui te plaît le plus dans cette passion ?",
            f"Bonjour {target_profile.prenom_affiche}, nous vivons dans des pays différents, "
            "mais j’aimerais faire connaissance si tu en as envie. Quel moment te convient pour discuter ?",
        ]
    return [
        (
            f"Bonjour {target_profile.prenom_affiche}, j'ai apprecie ton profil, "
            f"surtout ton interet pour {target_interest}. Comment se passe ta journee a {city} ?"
        ),
        (
            f"Salut {target_profile.prenom_affiche}, ton profil donne une impression serieuse et naturelle. "
            "J'aimerais bien faire connaissance si tu es d'accord."
        ),
        (
            f"Bonjour {target_profile.prenom_affiche}. J’aimerais apprendre à te connaître. "
            "Qu’est-ce qui est important pour toi dans une rencontre ?"
        ),
    ]


def profile_advice(profil):
    advice = []
    if not profil.photo_principale:
        advice.append("Ajoutez une photo claire et souriante : c'est le premier signal de confiance.")
    if not profil.biographie or len(profil.biographie) < 80:
        advice.append("Allongez un peu votre biographie avec votre temperament, vos valeurs et votre quotidien.")
    if not profil.ce_que_je_cherche:
        advice.append("Precisez ce que vous recherchez afin d'attirer des personnes compatibles.")
    if not profil.interets:
        advice.append("Ajoutez au moins 3 centres d'interet pour faciliter les premiers messages.")
    if not profil.profession:
        advice.append("Indiquez votre profession ou votre activite principale pour rendre le profil plus concret.")
    if not profil.langues:
        advice.append('Indiquez les langues que vous parlez pour faciliter les échanges locaux et internationaux.')
    if profil.est_diaspora and not profil.pays_residence.strip():
        advice.append('Précisez votre pays de résidence pour apparaître dans les recherches du pays où vous vivez.')
    if not advice:
        advice.append("Votre profil est deja bien structure. Ajoutez une phrase plus personnelle pour vous demarquer.")
        advice.append("Mettez en avant une valeur forte : famille, foi, ambition, stabilite ou sens de l'humour.")
    advice.append('Dites si vous privilégiez une relation locale ou si vous êtes ouvert à la distance, à votre rythme.')
    return advice


def compatibility_notes(my_profile, target_profile):
    common_interests = sorted(set(my_profile.interets or []) & set(target_profile.interets or []))
    common_languages = sorted(set(my_profile.langues or []) & set(target_profile.langues or []))
    notes = []
    if common_interests:
        notes.append(f"Interets communs : {_join(common_interests)}.")
    if common_languages:
        notes.append(f"Langues communes : {_join(common_languages)}.")
    if my_profile.religion and target_profile.religion and my_profile.religion == target_profile.religion:
        notes.append("Vous partagez une sensibilite religieuse proche.")
    if (target_profile.ville.casefold() == my_profile.ville.casefold()
            and target_profile.pays_actuel.casefold() == my_profile.pays_actuel.casefold()):
        notes.append("Vous etes dans la meme ville, ce qui facilite une rencontre progressive.")
    if target_profile.pays_actuel.casefold() != my_profile.pays_actuel.casefold():
        notes.append('Vous vivez dans des pays différents : parlez de vos attentes et convenez d’un horaire pour échanger.')
    if not notes:
        notes.append("Commencez par une question simple sur ses valeurs, son quotidien ou ses projets.")
    return notes
