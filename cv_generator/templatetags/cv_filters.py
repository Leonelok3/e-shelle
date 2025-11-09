# cv_generator/templatetags/cv_filters.py
from django import template
import re

register = template.Library()

@register.filter
def lines_to_list(value):
    """
    Transforme une description libre en puces propres:
    - convertit <br>, <p>, <li>, etc. en sauts de ligne
    - supprime tout HTML restant
    - enlève les caractères de puce (•, -, –, —, &bull;)
    - ignore les fragments bruités comme "< b r >" ou des lettres isolées
    - déduplique et limite le nombre d’items
    """
    if not value:
        return []

    txt = str(value)

    # 1) Normaliser les sauts de ligne HTML en \n
    txt = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', txt)
    txt = re.sub(r'(?i)</?\s*(p|li|ul|ol|div)[^>]*>', '\n', txt)

    # 2) Enlever tout tag HTML résiduel
    txt = re.sub(r'<[^>]+>', '', txt)

    # 3) Split, trim, retirer les puces en tête
    lines = [ln.strip() for ln in txt.splitlines()]

    # retirer puces/tires au début
    lines = [re.sub(r'^\s*(?:[•\-–—]|&bull;)\s*', '', ln) for ln in lines]

    # 4) Filtrer le bruit (vides, bricoles comme "< b r >", lettres isolées)
    cleaned = []
    for ln in lines:
        if not ln:
            continue
        # ignore séquences quasi-HTML ou trop courtes
        if re.fullmatch(r'[<>\s/]*br[<>\s/]*', ln, flags=re.I):
            continue
        if len(ln) <= 1:
            continue
        cleaned.append(ln)

    # 5) Dédupliquer en conservant l’ordre et limiter
    seen = set()
    out = []
    for ln in cleaned:
        if ln not in seen:
            out.append(ln)
            seen.add(ln)

    return out[:15]
