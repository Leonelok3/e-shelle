"""
whatsapp_parser.py — immobilier_cameroun/services
Parsing automatique des messages immobiliers WhatsApp (groupes Cameroun : ViSLE, E-Shelle Immo).
- Extraction intelligente des prix et formules (ex: "80mil*4+2", "150k", "80mil", "80 millions")
- Reconnaissance précise des quartiers Douala & Yaoundé
- Sélection experte des 5 meilleures photos avec Pillow (netteté, résolution, exposition)
- Génération d'une description enrichie professionnelle et optimisée SEO
"""
import re
import os
import math
import logging
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageStat, ImageFilter

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# QUARTIERS DOUALA & YAOUNDÉ
# ─────────────────────────────────────────────────────────────────

QUARTIERS_YAOUNDE = [
    "Bastos", "Omnisports", "Ngousso", "Santa Barbara", "Mfandena", "Golf",
    "Tsinga", "Nlongkak", "Elig-Essono", "Elig-Edzoa", "Mokolo", "Melen",
    "Ngoa-Ekelle", "Biyem-Assi", "Mendong", "Simbock", "Ahala", "Nsam",
    "Mvan", "Tropicana", "Kondengui", "Emombo", "Ekounou", "Nkolndongo",
    "Nkoabang", "Biteng", "Odza", "Messamendongo", "Awae", "Soa",
    "Etoa-Meki", "Dragages", "Mermoz", "Olembe", "Etoudi", "Nyom",
    "Nkolbisson", "Leboudi", "Mimboman", "Obobogo", "Damas", "Ekoumdoum",
    "Mballa 2", "Nkol-Eton", "Camp Sic", "Nkolbikok", "Oyomabang", "Etoug-Ebe",
    "Emana", "Messassi", "Tongolo", "Mvog-Ada", "Mvog-Mbi", "Mvog-Betsi"
]

QUARTIERS_DOUALA = [
    "Akwa", "Bonanjo", "Bonapriso", "Bali", "Deido", "Bonamoussadi",
    "Makepe", "Kotto", "Denver", "Logpom", "Logbessou", "PK8", "PK9", "PK10",
    "PK11", "PK12", "PK14", "PK17", "PK21", "Ndogbong", "Bepanda", "New Bell",
    "Nyalla", "Yassa", "Japoma", "Village", "Ndokoti", "Cite des Palmiers",
    "Cite CICAM", "Beedi", "Bessengue", "Bonaberi", "Mabanda", "Grand Moulin",
    "Sodiko", "Ndogpassi", "Ngangue", "Nkolmintag", "Youpwe", "Lendi", "Bangue",
    "Akwa-Nord", "Bassa", "Bonamikengue", "Bonangang"
]

VILLES_CAMEROUN_SUPPLEMENTAIRES = [
    "Kribi", "Limbe", "Buea", "Bafoussam", "Garoua", "Maroua", "Ngaoundere", "Bertoua", "Ebolowa", "Dschang"
]


# ─────────────────────────────────────────────────────────────────
# PARSER TEXTE IMMOBILIER WHATSAPP
# ─────────────────────────────────────────────────────────────────

def parse_immo_text(text: str) -> Dict[str, Any]:
    """
    Analyse un message WhatsApp brut et extrait toutes les informations clés :
    - Prix et conditions (ex: 80mil*4+2 -> 80 000 XAF, 4 mois avance + 2 mois caution)
    - Ville et quartier
    - Type de bien et type de transaction
    - Numéro de téléphone de contact
    - Titre accrocheur et description nettoyée
    """
    if not text:
        return {}

    cleaned_text = text.strip()
    result = {
        "titre": "",
        "type_bien": "STUDIO",
        "type_transaction": "LOCATION",
        "prix": None,
        "conditions": "",
        "ville": "Yaoundé",
        "quartier": "",
        "telephone": "",
        "description": cleaned_text,
        "quality_score": 50.0,
    }

    # ── 1. EXTRACTION TÉLÉPHONE SOURCE ──
    # Formats camerounais : +237 6XXXXXXXX, 237 6XXXXXXXX, 6XXXXXXXX, 2XXXXXXXX
    phone_pattern = r"(?:\+?237\s*)?([62]\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}|[62][0-9]{8})"
    phone_match = re.search(phone_pattern, cleaned_text)
    if phone_match:
        raw_phone = re.sub(r"\s+", "", phone_match.group(0))
        if raw_phone.startswith("+"):
            raw_phone = raw_phone[1:]
        if not raw_phone.startswith("237") and len(raw_phone) == 9:
            raw_phone = f"237{raw_phone}"
        result["telephone"] = f"+{raw_phone}"

    # ── 2. EXTRACTION VILLE & QUARTIER ──
    found_quartier = None
    inferred_ville = None

    # Recherche dans Douala d'abord (case insensitive avec word boundaries)
    for q in sorted(QUARTIERS_DOUALA, key=len, reverse=True):
        pattern = r"\b" + re.escape(q) + r"\b"
        if re.search(pattern, cleaned_text, re.IGNORECASE):
            found_quartier = q
            inferred_ville = "Douala"
            break

    # Si pas trouvé, recherche dans Yaoundé
    if not found_quartier:
        for q in sorted(QUARTIERS_YAOUNDE, key=len, reverse=True):
            pattern = r"\b" + re.escape(q) + r"\b"
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                found_quartier = q
                inferred_ville = "Yaoundé"
                break

    # Vérification explicite de la ville dans le texte
    lower_text = cleaned_text.lower()
    if "douala" in lower_text or "dla" in lower_text:
        result["ville"] = "Douala"
    elif "yaoundé" in lower_text or "yaounde" in lower_text or "yde" in lower_text:
        result["ville"] = "Yaoundé"
    elif "kribi" in lower_text:
        result["ville"] = "Kribi"
    elif inferred_ville:
        result["ville"] = inferred_ville

    if found_quartier:
        result["quartier"] = found_quartier
    else:
        # Tentative d'extraction par regex : "à Bastos", "a Makepe", "au quartier X"
        m_q = re.search(r"(?:à|a|au quartier|quartier)\s+([A-ZÀ-Ÿ][a-zA-ZÀ-ÿ0-9\s\-]{2,25})", cleaned_text)
        if m_q:
            candidate = m_q.group(1).strip()
            # Nettoyer les mots parasites
            candidate = re.split(r"[,.;\n]|prix|loyer|caution|avance", candidate, flags=re.IGNORECASE)[0].strip()
            if candidate and len(candidate) > 2:
                result["quartier"] = candidate

    # ── 3. TYPE DE TRANSACTION ──
    if re.search(r"\b(à vendre|a vendre|vente|acheter|achat|titre foncier|morcellement)\b", lower_text):
        result["type_transaction"] = "VENTE"
    elif re.search(r"\b(colocation|coloc)\b", lower_text):
        result["type_transaction"] = "COLOCATION"
    else:
        result["type_transaction"] = "LOCATION"

    # ── 4. TYPE DE BIEN ──
    if re.search(r"\b(terrain|parcelle|lot)\b", lower_text):
        result["type_bien"] = "TERRAIN"
    elif re.search(r"\b(bureau|bureaux|espace commercial)\b", lower_text):
        result["type_bien"] = "BUREAU"
    elif re.search(r"\b(boutique|magasin|commerce)\b", lower_text):
        result["type_bien"] = "BOUTIQUE"
    elif re.search(r"\b(duplex|triplex)\b", lower_text):
        result["type_bien"] = "DUPLEX"
    elif re.search(r"\b(villa)\b", lower_text):
        result["type_bien"] = "VILLA"
    elif re.search(r"\b(meubl[eé]|meublee)\b", lower_text):
        result["type_bien"] = "APPARTEMENT_MEUBLE"
    elif re.search(r"\b(appartement|appart)\b", lower_text):
        result["type_bien"] = "APPARTEMENT_NON_MEUBLE"
    elif re.search(r"\b(chambre)\b", lower_text):
        result["type_bien"] = "STUDIO"
    elif re.search(r"\b(studio)\b", lower_text):
        result["type_bien"] = "STUDIO"
    else:
        result["type_bien"] = "STUDIO"

    # ── 5. ANALYSE PRIX & FORMULE CONDITIONS ──
    # Cas clé 1 : Formule camerounaise type "80mil*4+2" ou "80k*6+2" ou "150 000 * 10 + 2"
    # Formule : [Loyer] * [Mois avance] + [Mois caution]
    formula_regex = r"(\d+(?:[.,]\d+)?)\s*(mil|k|mille|millions?)?\s*[*xX]\s*(\d+)\s*\+\s*(\d+)"
    f_match = re.search(formula_regex, cleaned_text, re.IGNORECASE)

    extracted_prix = None
    extracted_conditions = ""

    if f_match:
        raw_val_str = f_match.group(1).replace(",", ".")
        unit = (f_match.group(2) or "").lower()
        avance = f_match.group(3)
        caution = f_match.group(4)

        base_val = float(raw_val_str)
        if unit in ("mil", "k", "mille") or (not unit and base_val < 1000):
            montant = int(base_val * 1000)
        elif "million" in unit:
            montant = int(base_val * 1_000_000)
        else:
            montant = int(base_val)

        extracted_prix = montant
        extracted_conditions = f"{avance} mois d'avance + {caution} mois de caution"

    # Cas clé 2 : Prix avec mention "80mil", "150k", "80 millions"
    if extracted_prix is None:
        # Ex: "80mil" ou "80 mil" ou "80 mille"
        m_mil = re.search(r"\b(\d+)\s*(?:mil\b|mille\b)", cleaned_text, re.IGNORECASE)
        if m_mil:
            val = int(m_mil.group(1))
            if val < 1000:
                extracted_prix = val * 1000
            else:
                extracted_prix = val

    if extracted_prix is None:
        # Ex: "150k" ou "45k"
        m_k = re.search(r"\b(\d+)\s*k\b", cleaned_text, re.IGNORECASE)
        if m_k:
            extracted_prix = int(m_k.group(1)) * 1000

    if extracted_prix is None:
        # Ex: "80 millions" ou "80 M" (souvent vente terrain/maison)
        m_m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:millions?|m)\b", cleaned_text, re.IGNORECASE)
        if m_m and result["type_transaction"] == "VENTE":
            val = float(m_m.group(1).replace(",", "."))
            extracted_prix = int(val * 1_000_000)

    if extracted_prix is None:
        # Ex: "150 000 FCFA", "150.000 F", "80000 XAF", "150000"
        m_cfa = re.search(r"\b(\d{1,3}(?:[\s.,]\d{3})+|\d{4,9})\s*(?:fcfa|cfa|frs|f\b|xaf)?", cleaned_text, re.IGNORECASE)
        if m_cfa:
            digits = re.sub(r"[\s.,]", "", m_cfa.group(1))
            if digits.isdigit() and int(digits) >= 10000:
                extracted_prix = int(digits)

    if extracted_prix:
        result["prix"] = Decimal(extracted_prix)

    # Extraction des conditions si non extraites par la formule
    if not extracted_conditions:
        # Chercher format "6+2" ou "10+2" ou "12+1"
        cond_match = re.search(r"\b(\d{1,2})\s*\+\s*(\d{1,2})\b", cleaned_text)
        if cond_match:
            av, ca = cond_match.group(1), cond_match.group(2)
            extracted_conditions = f"{av} mois d'avance + {ca} mois de caution"
        else:
            # Chercher "avance : X mois", "caution : Y mois"
            m_av = re.search(r"avance\s*[:=]?\s*(\d+)\s*mois", cleaned_text, re.IGNORECASE)
            m_ca = re.search(r"caution\s*[:=]?\s*(\d+)\s*mois", cleaned_text, re.IGNORECASE)
            parts = []
            if m_av:
                parts.append(f"{m_av.group(1)} mois d'avance")
            if m_ca:
                parts.append(f"{m_ca.group(1)} mois de caution")
            if parts:
                extracted_conditions = " + ".join(parts)

    result["conditions"] = extracted_conditions

    # ── 6. GÉNÉRATION DU TITRE ──
    type_labels = {
        "STUDIO": "Studio moderne",
        "APPARTEMENT_MEUBLE": "Appartement meublé de standing",
        "APPARTEMENT_NON_MEUBLE": "Bel Appartement",
        "VILLA": "Superbe Villa",
        "DUPLEX": "Magnifique Duplex",
        "BUREAU": "Espace Bureau professionnel",
        "BOUTIQUE": "Boutique / Local commercial",
        "TERRAIN": "Terrain titré",
        "AUTRE": "Bien immobilier",
    }
    action_label = "à Louer" if result["type_transaction"] == "LOCATION" else "à Vendre"
    q_label = f" à {result['quartier']}" if result["quartier"] else ""
    v_label = f" ({result['ville']})" if result["ville"] else ""

    result["titre"] = f"{type_labels.get(result['type_bien'], 'Bien')} {action_label}{q_label}{v_label}"

    # ── 7. CALCUL DU SCORE QUALITÉ INITIAL (0 - 100) ──
    score = 30.0
    if result["prix"]:
        score += 20.0
    if result["quartier"]:
        score += 20.0
    if result["telephone"]:
        score += 15.0
    if result["conditions"]:
        score += 10.0
    if len(cleaned_text) > 80:
        score += 5.0
    result["quality_score"] = min(score, 100.0)

    return result


# ─────────────────────────────────────────────────────────────────
# SÉLECTION EXPERTE DES MEILLEURES PHOTOS AVEC PILLOW
# ─────────────────────────────────────────────────────────────────

def _evaluer_qualite_image(image_path_or_file) -> Tuple[float, Dict[str, Any]]:
    """
    Évalue la qualité d'une image avec Pillow :
    - Résolution (dimensions optimales pour l'immo)
    - Netteté & relief (variance des contours / Laplacian filter)
    - Exposition & contraste (luminance moyenne, écart-type)
    - Ratio d'aspect (paysage 4:3 / 16:9 privilégié)
    Retourne (score_global, métadonnées).
    """
    try:
        if isinstance(image_path_or_file, Image.Image):
            img = image_path_or_file
        elif hasattr(image_path_or_file, "read"):
            img = Image.open(image_path_or_file)
            image_path_or_file.seek(0)
        else:
            img = Image.open(image_path_or_file)

        width, height = img.size
        if width == 0 or height == 0:
            return 0.0, {}

        # 1. Score de Résolution (0 - 35 pts)
        nb_pixels = width * height
        if nb_pixels >= 1920 * 1080:      # Full HD
            score_res = 35.0
        elif nb_pixels >= 1280 * 720:     # HD 720p
            score_res = 30.0
        elif nb_pixels >= 800 * 600:      # Bonne résolution
            score_res = 22.0
        elif nb_pixels >= 400 * 400:      # Acceptable
            score_res = 12.0
        else:                             # Trop petite (vignette WhatsApp)
            score_res = 3.0

        # 2. Score Ratio d'Aspect (0 - 15 pts)
        ratio = max(width, height) / max(min(width, height), 1)
        # Ratio immobilier idéal : 1.33 (4:3) ou 1.5 (3:2) ou 1.77 (16:9)
        if 1.2 <= ratio <= 1.8:
            score_ratio = 15.0
        elif ratio <= 2.2:
            score_ratio = 10.0
        else:
            score_ratio = 3.0  # Panoramique extrême ou bandeau

        # 3. Score Exposition & Contraste (0 - 25 pts)
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        mean_lum = stat.mean[0]  # 0 (noir) à 255 (blanc)
        std_lum = stat.stddev[0] # Contraste

        # Pénalisation images trop sombres (< 45) ou cramées (> 235)
        if 80 <= mean_lum <= 180:
            score_expo = 15.0
        elif 50 <= mean_lum < 80 or 180 < mean_lum <= 220:
            score_expo = 10.0
        else:
            score_expo = 3.0

        # Contraste (dynamique de l'image)
        if std_lum >= 45:
            score_contraste = 10.0
        elif std_lum >= 25:
            score_contraste = 7.0
        else:
            score_contraste = 2.0

        # 4. Score de Netteté (Filtre Contours / Détails) (0 - 25 pts)
        # Détection des contours avec FIND_EDGES pour mesurer la quantité de détails
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_mean = edge_stat.mean[0]

        if edge_mean >= 18.0:
            score_nettete = 25.0
        elif edge_mean >= 10.0:
            score_nettete = 18.0
        elif edge_mean >= 5.0:
            score_nettete = 10.0
        else:
            score_nettete = 4.0  # Image floue ou aplat sans détails

        total_score = score_res + score_ratio + score_expo + score_contraste + score_nettete
        meta = {
            "width": width,
            "height": height,
            "mean_lum": round(mean_lum, 1),
            "edge_detail": round(edge_mean, 1),
            "score": round(total_score, 1),
        }
        return total_score, meta

    except Exception as e:
        logger.warning(f"[select_best_photos] Erreur évaluation image {image_path_or_file}: {e}")
        return 10.0, {"error": str(e)}


def select_best_photos(images_list: List[Any], max_photos: int = 5) -> List[Dict[str, Any]]:
    """
    Parcourt une liste d'images (chemins fichiers ou objets fichiers Django),
    calcule leur score de qualité Pillow et retourne les top `max_photos` classées
    par ordre décroissant de qualité (la première étant la photo principale).
    """
    if not images_list:
        return []

    evaluated = []
    for idx, item in enumerate(images_list):
        score, meta = _evaluer_qualite_image(item)
        identifier = getattr(item, "name", str(item))
        evaluated.append({
            "item": item,
            "identifier": identifier,
            "original_index": idx,
            "score": score,
            "meta": meta,
        })

    # Tri par score décroissant
    evaluated.sort(key=lambda x: x["score"], reverse=True)

    # Sélection des N meilleures
    selected = evaluated[:max_photos]
    logger.info(
        f"[select_best_photos] {len(selected)}/{len(images_list)} photos retenues. "
        f"Meilleur score: {selected[0]['score'] if selected else 0}"
    )
    return selected


# ─────────────────────────────────────────────────────────────────
# ENRICHISSEMENT & AMÉLIORATION DE LA DESCRIPTION (SEO & AEO)
# ─────────────────────────────────────────────────────────────────

def improve_description(raw_text: str, parsed_data: Dict[str, Any]) -> str:
    """
    Génère une description immobilière professionnelle, séduisante,
    structurée avec emojis et optimisée pour le SEO local camerounais.
    """
    titre = parsed_data.get("titre") or "Bien immobilier de standing"
    ville = parsed_data.get("ville") or "Cameroun"
    quartier = parsed_data.get("quartier") or "Zone résidentielle"
    prix = parsed_data.get("prix")
    conditions = parsed_data.get("conditions") or ""
    phone = parsed_data.get("telephone") or ""
    type_bien = parsed_data.get("type_bien") or "BIEN"
    type_transaction = parsed_data.get("type_transaction") or "LOCATION"

    # Formatage prix
    if prix:
        prix_str = f"{int(prix):,} XAF".replace(",", " ")
        if type_transaction == "LOCATION":
            prix_label = f"{prix_str} / mois"
        else:
            prix_label = f"{prix_str}"
    else:
        prix_label = "Prix sur demande"

    # Détection des points forts dans le texte brut
    points_forts = []
    raw_lower = raw_text.lower()
    
    if any(k in raw_lower for k in ["forage", "eau cde", "camwater", "eau disponible", "bâche"]):
        points_forts.append("💧 Alimentation en eau continue (forage / Camwater)")
    if any(k in raw_lower for k in ["compteur", "eneo", "prépayé", "prepaye"]):
        points_forts.append("⚡ Compteur électrique individuel prépayé")
    if any(k in raw_lower for k in ["parking", "garage"]):
        points_forts.append("🚗 Parking sécurisé disponible")
    if any(k in raw_lower for k in ["gardien", "vigile", "sécurité", "securite", "clôturé", "cloture"]):
        points_forts.append("🛡️ Cadre sécurisé et clôturé avec gardiennage")
    if any(k in raw_lower for k in ["clim", "climatisé", "climatise"]):
        points_forts.append("❄️ Logement climatisé")
    if any(k in raw_lower for k in ["balcon", "terrasse", "véranda"]):
        points_forts.append("🌅 Balcon avec vue agréable")
    if any(k in raw_lower for k in ["chauffe-eau", "chauffe eau"]):
        points_forts.append("🚿 Chauffe-eau installé")
    if any(k in raw_lower for k in ["placard", "dressing"]):
        points_forts.append("🚪 Placards et rangements intégrés")

    if not points_forts:
        points_forts = [
            "✨ Cadre calme, propre et accessible",
            "🛡️ Environnement sécurisé",
            "🚗 Accès facile pour véhicule",
        ]

    bullets_str = "\n".join(f"- {p}" for p in points_forts)

    conditions_block = ""
    if conditions:
        conditions_block = f"📋 **Conditions d'entrée** : {conditions}\n"

    contact_block = f"📱 **Contact direct WhatsApp** : {phone}\n" if phone else ""

    improved = f"""🏠 **{titre.upper()}**

📍 **Localisation** : Quartier {quartier}, {ville}
💰 **Tarif** : {prix_label}
{conditions_block}
✨ **Points forts & Équipements** :
{bullets_str}

📝 **Description & Ambiance** :
Ce bien immobilier idéalement situé à {quartier} offre un cadre de vie paisible, sécurisé et proche de toutes commodités (transports, commerces, écoles). Parfait pour toute personne à la recherche de confort et de sérénité au quotidien.

{contact_block}👉 **Visites & réservations rapides garanties via E-Shelle Immobilier**.
"""
    return improved.strip()
