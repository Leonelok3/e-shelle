"""
Algorithme de score de compatibilité sur 100 points.
Facteurs : géographie, religion, âge, enfants, langues, intérêts, niveau d'étude.
"""
import math


def calculer_distance_km(lat1, lon1, lat2, lon2):
    """Formule de Haversine pour calculer la distance entre deux points GPS."""
    if None in (lat1, lon1, lat2, lon2):
        return 9999

    R = 6371  # Rayon Terre en km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculer_score_compatibilite(profil_a, profil_b):
    """
    Retourne un dict avec le score total (0-100) et le détail par critère.
    """
    score = 0
    details = {}

    # 1. Géographie / Distance (20 pts)
    distance = calculer_distance_km(
        profil_a.latitude, profil_a.longitude,
        profil_b.latitude, profil_b.longitude
    )
    if distance <= 50:
        geo_pts = 20
    elif distance <= 200:
        geo_pts = 15
    elif distance <= 1000:
        geo_pts = 10
    elif distance <= 5000:
        geo_pts = 7
    else:
        geo_pts = 4
    score += geo_pts
    details['geographie'] = {'pts': geo_pts, 'distance_km': round(distance)}

    # 2. Compatibilité d'âge (15 pts)
    age_a, age_b = profil_a.age(), profil_b.age()
    in_range_a = profil_a.recherche_age_min <= age_b <= profil_a.recherche_age_max
    in_range_b = profil_b.recherche_age_min <= age_a <= profil_b.recherche_age_max
    if in_range_a and in_range_b:
        age_pts = 15
    elif in_range_a or in_range_b:
        age_pts = 8
    else:
        age_pts = 0
    score += age_pts
    details['age'] = {'pts': age_pts, 'age_a': age_a, 'age_b': age_b}

    # 3. Religion (15 pts)
    if profil_a.religion and profil_b.religion:
        if profil_a.religion == profil_b.religion:
            rel_pts = 15
        elif 'aucune' in (profil_a.religion, profil_b.religion):
            rel_pts = 7
        else:
            rel_pts = 3
    else:
        rel_pts = 8  # pas précisé = neutre
    score += rel_pts
    details['religion'] = {'pts': rel_pts}

    # 4. Vision des enfants (15 pts)
    enfants_compat = {
        ('oui', 'oui'): 15,
        ('non', 'non'): 15,
        ('peut_etre', 'peut_etre'): 12,
        ('oui', 'peut_etre'): 10,
        ('peut_etre', 'oui'): 10,
        ('non', 'peut_etre'): 5,
        ('peut_etre', 'non'): 5,
        ('deja_assez', 'deja_assez'): 15,
        ('oui', 'non'): 0,
        ('non', 'oui'): 0,
    }
    key = (profil_a.veut_des_enfants, profil_b.veut_des_enfants)
    enf_pts = enfants_compat.get(key, enfants_compat.get((key[1], key[0]), 5))
    score += enf_pts
    details['enfants'] = {'pts': enf_pts}

    # 5. Langues communes (10 pts)
    langues_a = set(profil_a.langues) if profil_a.langues else set()
    langues_b = set(profil_b.langues) if profil_b.langues else set()
    langues_communes = langues_a & langues_b
    lang_pts = min(10, len(langues_communes) * 5)
    score += lang_pts
    details['langues'] = {'pts': lang_pts, 'communes': list(langues_communes)}

    # 6. Intérêts communs (15 pts)
    interets_a = set(profil_a.interets) if profil_a.interets else set()
    interets_b = set(profil_b.interets) if profil_b.interets else set()
    interets_communs = interets_a & interets_b
    int_pts = min(15, len(interets_communs) * 3)
    score += int_pts
    details['interets'] = {'pts': int_pts, 'communs': list(interets_communs)}

    # 7. Niveau d'étude (10 pts)
    niveaux = ['primaire', 'secondaire', 'bac2', 'licence', 'master', 'doctorat']
    try:
        diff_niveau = abs(
            niveaux.index(profil_a.niveau_etude) -
            niveaux.index(profil_b.niveau_etude)
        )
        etude_pts = max(0, 10 - diff_niveau * 3)
    except ValueError:
        etude_pts = 5
    score += etude_pts
    details['etude'] = {'pts': etude_pts}

    score_total = min(100, score)

    return {
        'score_total': score_total,
        'details': details,
        'distance_km': round(distance),
        'niveau': (
            'Excellent' if score_total >= 80 else
            'Très bon' if score_total >= 65 else
            'Bon' if score_total >= 50 else
            'Moyen'
        )
    }


def get_profils_compatibles(profil, limit=20, exclude_ids=None):
    """
    Retourne les profils compatibles triés par score décroissant.
    Exclut les profils déjà likés, bloqués ou passés.
    """
    from rencontres.models import ProfilRencontre, Like, Blocage
    from django.db.models import Q

    if exclude_ids is None:
        exclude_ids = []

    # IDs à exclure : déjà likés, bloquages mutuels, profil lui-même
    likes_envoyes = Like.objects.filter(envoyeur=profil).values_list('recepteur_id', flat=True)
    blocages = Blocage.objects.filter(
        Q(bloqueur=profil) | Q(bloque=profil)
    ).values_list('bloqueur_id', 'bloque_id')
    bloques_ids = set()
    for b1, b2 in blocages:
        bloques_ids.add(b1)
        bloques_ids.add(b2)

    exclusions = set(exclude_ids) | set(likes_envoyes) | bloques_ids | {profil.id}

    # Filtrer par critères de base
    qs = ProfilRencontre.objects.filter(
        est_actif=True,
        photos__est_approuvee=True,
    ).exclude(id__in=exclusions).select_related('user').distinct()

    # Filtrer par genre recherché
    if profil.recherche_genre:
        qs = qs.filter(genre=profil.recherche_genre.lower())

    # Filtrer par tranche d'âge recherchée
    from datetime import date
    today = date.today()

    # Calculer les dates de naissance correspondant aux âges min/max
    from datetime import timedelta
    date_max = today.replace(year=today.year - profil.recherche_age_min)
    date_min = today.replace(year=today.year - profil.recherche_age_max)
    qs = qs.filter(date_naissance__gte=date_min, date_naissance__lte=date_max)

    # Calculer les scores et trier
    profils_scores = []
    for p in qs[:100]:  # Limiter le calcul à 100 candidats max
        result = calculer_score_compatibilite(profil, p)
        profils_scores.append((p, result['score_total'], result['distance_km']))

    # Trier par score décroissant
    profils_scores.sort(key=lambda x: x[1], reverse=True)

    return profils_scores[:limit]
