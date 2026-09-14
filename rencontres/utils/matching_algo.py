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


def get_profils_compatibles(profil, limit=20, exclude_ids=None, filters=None):
    from rencontres.models import ProfilRencontre, Like, Blocage
    from rencontres.utils.access import entitlements
    from django.db.models import Q
    from django.utils import timezone
    if not profil.est_actif or profil.age() < 18:
        return []
    filters = filters or {}
    rights = entitlements(profil)
    likes = Like.objects.filter(envoyeur=profil).values_list('recepteur_id', flat=True)
    blocks = Blocage.objects.filter(Q(bloqueur=profil) | Q(bloque=profil)).values_list('bloqueur_id', 'bloque_id')
    excluded = set(exclude_ids or []) | set(likes) | {profil.pk}
    for pair in blocks:
        excluded.update(pair)
    qs = ProfilRencontre.objects.filter(est_actif=True, user__is_active=True,
        photos__est_approuvee=True).exclude(pk__in=excluded).select_related('user').distinct()
    # Incognito only has effect while the feature is covered by a valid pass.
    hidden = ProfilRencontre.objects.filter(incognito=True, abonnements__est_actif=True,
        abonnements__date_fin__gt=timezone.now(), abonnements__plan__mode_incognito=True).values('pk')
    qs = qs.exclude(pk__in=hidden)
    if profil.recherche_genre:
        qs = qs.filter(genre=profil.recherche_genre.lower())
    if filters.get('pays'):
        qs = qs.filter(pays__iexact=filters['pays'])
    if filters.get('religion'):
        qs = qs.filter(religion=filters['religion'])
    if filters.get('verifie_seulement'):
        qs = qs.filter(badge_verifie=True)
    if rights['filtre_avance'] and filters.get('niveau_etude'):
        levels = ['primaire', 'secondaire', 'bac2', 'licence', 'master', 'doctorat']
        if filters['niveau_etude'] in levels:
            qs = qs.filter(niveau_etude__in=levels[levels.index(filters['niveau_etude']):])
    minimum = max(18, filters.get('age_min') or profil.recherche_age_min)
    maximum = min(99, filters.get('age_max') or profil.recherche_age_max)
    now = timezone.now()
    results = []
    # Boosted members enter the candidate pool first, but still meet all filters.
    for candidate in qs.order_by('-boost_fin', '-derniere_connexion')[:500]:
        if not minimum <= candidate.age() <= maximum:
            continue
        if candidate.recherche_genre and candidate.recherche_genre != profil.genre:
            continue
        if not candidate.recherche_age_min <= profil.age() <= candidate.recherche_age_max:
            continue
        result = calculer_score_compatibilite(profil, candidate)
        distance = result['distance_km']
        known = None not in (profil.latitude, profil.longitude, candidate.latitude, candidate.longitude)
        if filters.get('distance_km') and (not known or distance > filters['distance_km']):
            continue
        public_distance = distance if known and candidate.afficher_distance else None
        boosted = bool(candidate.boost_fin and candidate.boost_fin > now)
        results.append((candidate, result['score_total'], public_distance, boosted))
    results.sort(key=lambda item: (item[3], item[1]), reverse=True)
    return [(p, score, distance) for p, score, distance, _ in results[:limit]]
