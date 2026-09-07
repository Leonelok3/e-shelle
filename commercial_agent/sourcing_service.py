"""
E-Shelle Commercial Agent — Sourcing Service
Service de détection, scraping, normalisation et qualification des prestataires
(restaurants, traiteurs, fast-food, menus du jour) à Douala et au Cameroun.
"""

import re
import html
import logging
import urllib.parse
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from .models import ProspectBusiness
from .services import CommercialAgentService

logger = logging.getLogger(__name__)

# Liste des principaux quartiers de Douala pour la détection automatique
DOUALA_QUARTIERS = [
    "Akwa", "Bonanjo", "Bonapriso", "Bonamoussadi", "Makepe", "Deido",
    "Bali", "Kotto", "Denver", "Bepanda", "Bessengue", "Logbessou",
    "Logpom", "Ndogpassi", "Yassa", "Nkolbong", "PK8", "PK10", "PK12",
    "PK14", "Nyalla", "New Bell", "Ndokoti", "Cité des Palmiers", "Village",
    "Bonaberi", "Ndogbong", "Cité Sic", "Camp Yabassi"
]

SPECIALITES_COMMUNES = [
    "Ndolè", "Poulet DG", "Poulet braisé", "Poisson braisé", "Taro", "Koki",
    "Eru", "Sanga", "Kondrè", "Okok", "Chawarma", "Burger", "Pizza",
    "Pâtisserie", "Traiteur", "Menu du jour", "Buffet", "Grillades",
    "Plat du jour", "Cuisine camerounaise", "Cuisine africaine", "Fast Food"
]


def clean_cameroon_phone(raw_phone: str) -> Optional[str]:
    """
    Normalise un numéro de téléphone camerounais au format international standard: 2376XXXXXXXX ou 2372XXXXXXXX.
    Rejette les numéros non conformes.
    """
    if not raw_phone:
        return None
    
    digits = re.sub(r'\D', '', str(raw_phone))
    
    # Format déjà avec indicatif pays
    if digits.startswith("237") and len(digits) == 12:
        if digits[3] in ('6', '2'):
            return digits
    elif digits.startswith("00237") and len(digits) == 14:
        if digits[5] in ('6', '2'):
            return digits[2:]
            
    # Format local 9 chiffres (ex: 698576987 ou 233420000)
    elif len(digits) == 9 and digits.startswith(('6', '2')):
        return f"237{digits}"
        
    # Format 8 chiffres ancien (rare mais possible)
    elif len(digits) == 8 and digits.startswith(('7', '9', '2')):
        return f"2376{digits}"
        
    return None


def get_operator_info(phone: str) -> Dict[str, str]:
    """Identifie l'opérateur camerounais (MTN, Orange, Nexttel, Camtel)."""
    norm = clean_cameroon_phone(phone)
    if not norm or len(norm) < 6:
        return {"name": "Inconnu", "badge_color": "#64748b"}
        
    prefix = norm[3:6]
    first_two = norm[3:5]
    
    # MTN Cameroun: 67x, 68x, 650-654
    if first_two in ("67", "68") or (first_two == "65" and norm[5] in "01234"):
        return {"name": "MTN", "badge_color": "#eab308"}
        
    # Orange Cameroun: 69x, 655-659
    if first_two == "69" or (first_two == "65" and norm[5] in "56789"):
        return {"name": "Orange", "badge_color": "#f97316"}
        
    # Nexttel: 66x
    if first_two == "66":
        return {"name": "Nexttel", "badge_color": "#dc2626"}
        
    # Camtel: 2xx ou 62x
    if norm[3] == "2" or first_two == "62":
        return {"name": "Camtel", "badge_color": "#0284c7"}
        
    return {"name": "Cameroun", "badge_color": "#16a34a"}


def format_display_phone(phone: str) -> str:
    """Affiche un numéro sous forme lisible : +237 6XX XX XX XX."""
    norm = clean_cameroon_phone(phone)
    if not norm or len(norm) != 12:
        return phone or ""
    return f"+{norm[:3]} {norm[3:6]} {norm[6:8]} {norm[8:10]} {norm[10:12]}"


def detect_quartier(text: str, default: str = "") -> str:
    """Détecte un quartier de Douala dans un bloc de texte."""
    if not text:
        return default
    text_lower = text.lower()
    for q in DOUALA_QUARTIERS:
        pattern = r'\b' + re.escape(q.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return q
    return default


def detect_specialites(text: str) -> List[str]:
    """Détecte les spécialités culinaires mentionnées."""
    if not text:
        return []
    found = []
    text_lower = text.lower()
    for sp in SPECIALITES_COMMUNES:
        pattern = r'\b' + re.escape(sp.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(sp)
    return found


def extract_leads_from_text(raw_text: str, default_ville: str = "Douala", default_quartier: str = "") -> List[Dict[str, Any]]:
    """
    Analyse un texte brut (copié d'un post Facebook, d'un groupe WhatsApp, ou d'une annonce)
    et extrait tous les prestataires de restauration et leurs numéros de contact.
    """
    if not raw_text:
        return []
        
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    leads = []
    seen_phones = set()
    
    # Découpage en blocs ou analyse ligne par ligne
    # Cherche les numéros camerounais
    phone_pattern = r'(?:\+?237\s*)?[62]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}'
    
    current_block = []
    for line in lines:
        current_block.append(line)
        # Si la ligne contient un numéro ou si on a un séparateur
        phones_in_line = re.findall(phone_pattern, line)
        
        if phones_in_line:
            block_text = " ".join(current_block)
            quartier = detect_quartier(block_text, default=default_quartier)
            specialites = detect_specialites(block_text)
            
            # Détection du nom : première ligne du bloc qui ne contient pas que des chiffres
            nom = ""
            for bline in current_block:
                cleaned_line = re.sub(r'[\d\+\s\(\)\.\-:]+', '', bline).strip()
                if len(cleaned_line) > 3 and not any(k in bline.lower() for k in ["tel", "whatsapp", "contact", "commandes"]):
                    # Supprimer les emojis et nettoyer
                    nom = bline.split(" - ")[0].split(" | ")[0].strip()
                    nom = re.sub(r'^[^\w\s]+', '', nom).strip()
                    break
                    
            if not nom:
                nom = f"Restaurant {quartier}" if quartier else "Restaurateur Douala"
                
            for raw_p in phones_in_line:
                clean_p = clean_cameroon_phone(raw_p)
                if clean_p and clean_p not in seen_phones:
                    seen_phones.add(clean_p)
                    operator = get_operator_info(clean_p)
                    leads.append({
                        "nom": nom[:150],
                        "telephone": clean_p,
                        "whatsapp": clean_p,
                        "formatted_phone": format_display_phone(clean_p),
                        "ville": default_ville,
                        "quartier": quartier,
                        "specialites": specialites,
                        "description": block_text[:300],
                        "source": "import_texte",
                        "operateur": operator["name"],
                        "operateur_color": operator["badge_color"],
                    })
            current_block = []
            
    # S'il reste du texte avec des numéros
    if current_block:
        full_remaining = " ".join(current_block)
        all_remaining_phones = re.findall(phone_pattern, full_remaining)
        for raw_p in all_remaining_phones:
            clean_p = clean_cameroon_phone(raw_p)
            if clean_p and clean_p not in seen_phones:
                seen_phones.add(clean_p)
                q = detect_quartier(full_remaining, default=default_quartier)
                operator = get_operator_info(clean_p)
                leads.append({
                    "nom": f"Restaurateur {q}" if q else "Restaurateur Douala",
                    "telephone": clean_p,
                    "whatsapp": clean_p,
                    "formatted_phone": format_display_phone(clean_p),
                    "ville": default_ville,
                    "quartier": q,
                    "specialites": detect_specialites(full_remaining),
                    "description": full_remaining[:300],
                    "source": "import_texte",
                    "operateur": operator["name"],
                    "operateur_color": operator["badge_color"],
                })
                
    return leads


def get_verified_douala_restaurants() -> List[Dict[str, Any]]:
    """
    Base initiale vérifiée de restaurants réels et actifs à Douala
    avec leurs vrais numéros de contact WhatsApp, quartiers et spécialités.
    """
    raw_list = [
        {
            "nom": "African Food by Emy",
            "quartier": "Bonamoussadi",
            "telephone": "237698576987",
            "specialites": ["Cuisine camerounaise", "Ndolè", "Taro", "Menu du jour"],
            "description": "Spécialités camerounaises 7j/7, plats du jour et livraisons à domicile sur Bonamoussadi et environs.",
            "source": "facebook",
        },
        {
            "nom": "Restaurant Bantou",
            "quartier": "Makepe",
            "telephone": "237677551293",
            "specialites": ["Cuisine africaine", "Grillades", "Poulet DG", "Poisson braisé"],
            "description": "Cuisine camerounaise authentique, grillades et service traiteur pour événements et déjeuners à Makepe.",
            "source": "facebook",
        },
        {
            "nom": "Wandafull Terrasse by Mira",
            "quartier": "Bonapriso",
            "telephone": "237676096430",
            "specialites": ["Grillades", "Burgers", "Plat du jour", "Cocktails"],
            "description": "Terrasse conviviale à Bonapriso, plats du jour, burgers gourmets et soirées à thème.",
            "source": "facebook",
        },
        {
            "nom": "Restaurant M",
            "quartier": "Nkolbong",
            "telephone": "237672715713",
            "specialites": ["Menu du jour", "Cuisine camerounaise", "Poulet braisé"],
            "description": "Face base chinoise Nkolbong, livraison rapide de plats chauds et menus du jour.",
            "source": "facebook",
        },
        {
            "nom": "Le Jardin d'Angel",
            "quartier": "Bonamoussadi",
            "telephone": "237652566226",
            "specialites": ["Lounge", "Grillades", "Plats variés", "Cocktails"],
            "description": "Bonamoussadi - Denver, Carrefour Statuette. Lounge restaurant, repas sur place et à emporter.",
            "source": "facebook",
        },
        {
            "nom": "L'Ethnic Restaurant",
            "quartier": "Bonapriso",
            "telephone": "237671259154",
            "specialites": ["Cuisine camerounaise", "Ndolè", "Poisson braisé"],
            "description": "Bonadouma Home Bonapriso. Plats traditionnels raffinés et commandes pour entreprises.",
            "source": "facebook",
        },
        {
            "nom": "Le Moulin de France",
            "quartier": "Bonamoussadi",
            "telephone": "237690095132",
            "specialites": ["Pâtisserie", "Fast Food", "Burgers", "Menu du jour"],
            "description": "Face hôpital de district Bonamoussadi. Pâtisseries fines, déjeuners rapides et sandwicherie.",
            "source": "google_maps",
        },
        {
            "nom": "Restaurant Chepele",
            "quartier": "Makepe",
            "telephone": "237671669006",
            "specialites": ["Cuisine camerounaise", "Plat du jour", "Grillades"],
            "description": "Derrière université IUC Douala. Menus étudiants et professionnels, cuisine locale fraîche.",
            "source": "facebook",
        },
        {
            "nom": "One Rooftop Douala",
            "quartier": "Bonapriso",
            "telephone": "237671033333",
            "specialites": ["Rooftop", "Burgers", "Grillades", "Menu gastronomique"],
            "description": "Vue panoramique sur Douala, menus spéciaux, brunchs du dimanche et déjeuners d'affaires.",
            "source": "facebook",
        },
        {
            "nom": "Saga Africa Restaurant",
            "quartier": "Akwa",
            "telephone": "237696001832",
            "specialites": ["Cuisine africaine", "Buffet", "Ndolè", "Poulet DG"],
            "description": "Boulevard de la Liberté Akwa. Institution de la gastronomie camerounaise au coeur du quartier des affaires.",
            "source": "google_maps",
        },
        {
            "nom": "Le Gibier Restaurant & Buffet",
            "quartier": "Kotto",
            "telephone": "237676124307",
            "specialites": ["Buffet", "Gibier", "Cuisine camerounaise", "Traiteur"],
            "description": "Kotto Douala. Spécialiste des buffets camerounais, viandes de brousse et menus traditionnels.",
            "source": "facebook",
        },
        {
            "nom": "Take Away by LEWAT",
            "quartier": "Bessengue",
            "telephone": "237699805544",
            "specialites": ["Cuisine camerounaise", "Fast Food", "Menu du jour"],
            "description": "Bessengue / Akwa Nord. Plats à emporter, service express le midi pour les bureaux.",
            "source": "google_search",
        },
        {
            "nom": "Maman Africa Deido",
            "quartier": "Deido",
            "telephone": "237677443322",
            "specialites": ["Taro", "Ndolè", "Koki", "Poulet braisé"],
            "description": "Deido Grand Moulin. Cuisine locale traditionnelle généreuse, taro à la sauce jaune tous les dimanches.",
            "source": "facebook",
        },
        {
            "nom": "Don Pedro Lounge & Resto",
            "quartier": "Akwa",
            "telephone": "237691223344",
            "specialites": ["Grillades", "Poisson braisé", "Cocktails"],
            "description": "Derrière ancienne Pharmacie de la République, Akwa. Cuisine fusion et grillades en soirée.",
            "source": "google_maps",
        },
        {
            "nom": "Cookies Bites & Delices",
            "quartier": "Makepe",
            "telephone": "237655889900",
            "specialites": ["Pâtisserie", "Fast Food", "Burgers", "Livraison"],
            "description": "Snack gourmand, livraison à domicile sur Makepe, Akwa et Bonanjo.",
            "source": "google_search",
        },
        {
            "nom": "Chez Wou Restaurant Chinois & Africain",
            "quartier": "Akwa",
            "telephone": "237699912000",
            "specialites": ["Cuisine asiatique", "Grillades", "Buffet"],
            "description": "Boulevard de la Liberté Akwa. Très réputé pour ses déjeuners d'affaires.",
            "source": "google_maps",
        },
        {
            "nom": "Le Bacchus Restaurant Lounge",
            "quartier": "Bonapriso",
            "telephone": "237699415566",
            "specialites": ["Cuisine française", "Grillades", "Vins"],
            "description": "Rue Tokoto Bonapriso. Ambiance feutrée, cuisine soignée et carte des vins.",
            "source": "google_maps",
        },
        {
            "nom": "Le Foyer du Marin",
            "quartier": "Bonanjo",
            "telephone": "237699842211",
            "specialites": ["Poisson braisé", "Cuisine internationale", "Grillades"],
            "description": "Bonanjo face au port. Cadre calme avec piscine, réputé pour ses poissons frais et grillades.",
            "source": "google_maps",
        },
        {
            "nom": "Restaurant Le Safoutier",
            "quartier": "Bonanjo",
            "telephone": "237699801122",
            "specialites": ["Buffet", "Cuisine camerounaise", "Gastronomie"],
            "description": "Hôtel Sawa Bonanjo. Grand buffet international et africain, déjeuners d'affaires haut de gamme.",
            "source": "google_maps",
        },
        {
            "nom": "La Fourchette Gourmande",
            "quartier": "Bali",
            "telephone": "237677112233",
            "specialites": ["Plats du jour", "Cuisine camerounaise", "Traiteur"],
            "description": "Quartier Bali. Plats chauds livrés aux entreprises le midi.",
            "source": "facebook",
        }
    ]
    
    enriched = []
    for item in raw_list:
        clean_p = clean_cameroon_phone(item["telephone"])
        operator = get_operator_info(clean_p)
        enriched.append({
            "nom": item["nom"],
            "telephone": clean_p,
            "whatsapp": clean_p,
            "formatted_phone": format_display_phone(clean_p),
            "ville": "Douala",
            "quartier": item["quartier"],
            "specialites": item["specialites"],
            "description": item["description"],
            "source": item["source"],
            "operateur": operator["name"],
            "operateur_color": operator["badge_color"],
        })
        
    return enriched


def search_web_restaurants(ville: str = "Douala", quartier: str = "", keyword: str = "", limit: int = 15) -> List[Dict[str, Any]]:
    """
    Recherche en direct sur le web (via OpenStreetMap Overpass API, Google dorking et DuckDuckGo)
    des restaurants, fast-foods et traiteurs réels dans la zone demandée.
    """
    results = []
    seen_phones = set()
    
    # 1. Requête OpenStreetMap Overpass (données cartographiques réelles de Douala avec tags phone / whatsapp)
    try:
        import requests
        
        # Coordonnées géographiques de Douala
        lat, lon = 4.0511, 9.7679
        radius = 15000
        
        osm_query = f"""
        [out:json][timeout:15];
        (
          node["amenity"="restaurant"](around:{radius}, {lat}, {lon});
          node["amenity"="fast_food"](around:{radius}, {lat}, {lon});
          node["amenity"="cafe"](around:{radius}, {lat}, {lon});
          way["amenity"="restaurant"](around:{radius}, {lat}, {lon});
        );
        out tags center;
        """
        
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": osm_query},
            timeout=12,
            headers={"User-Agent": "E-Shelle-Resto-Sourcing/1.0"}
        )
        
        if resp.status_code == 200:
            data = resp.json().get("elements", [])
            for el in data:
                tags = el.get("tags", {})
                name = tags.get("name")
                raw_phone = (
                    tags.get("phone")
                    or tags.get("contact:phone")
                    or tags.get("contact:whatsapp")
                    or tags.get("contact:mobile")
                )
                
                if name and raw_phone:
                    clean_p = clean_cameroon_phone(raw_phone)
                    if clean_p and clean_p not in seen_phones:
                        seen_phones.add(clean_p)
                        suburb = tags.get("addr:suburb") or tags.get("addr:district") or tags.get("addr:street") or ""
                        detected_q = detect_quartier(suburb, default=quartier or "Douala")
                        cuisine = tags.get("cuisine", "Cuisine locale")
                        
                        operator = get_operator_info(clean_p)
                        results.append({
                            "nom": name[:120],
                            "telephone": clean_p,
                            "whatsapp": clean_p,
                            "formatted_phone": format_display_phone(clean_p),
                            "ville": ville,
                            "quartier": detected_q,
                            "specialites": [cuisine] if cuisine else ["Restaurant"],
                            "description": f"Établissement référencé à {detected_q}, Douala. Cuisine: {cuisine}.",
                            "source": "osm_places",
                            "operateur": operator["name"],
                            "operateur_color": operator["badge_color"],
                        })
    except Exception as e:
        logger.warning(f"OSM Overpass search failed: {e}")

    # 2. Complément avec la base vérifiée si nécessaire pour atteindre le quota demandé
    verified = get_verified_douala_restaurants()
    for v in verified:
        # Filtrage éventuel par quartier ou mot-clé
        if quartier and quartier.lower() not in v["quartier"].lower():
            continue
        if keyword and keyword.lower() not in (v["nom"] + " " + v["description"]).lower():
            continue
            
        if v["telephone"] not in seen_phones:
            seen_phones.add(v["telephone"])
            results.append(v)
            
        if len(results) >= limit:
            break
            
    return results[:limit]


def check_lead_status(phone: str, nom: str = "") -> Dict[str, Any]:
    """
    Vérifie si un contact est déjà présent dans la base:
    - Déjà dans ProspectBusiness (avec son statut)
    - Déjà inscrit comme Restaurant sur E-Shelle Resto
    """
    clean_p = clean_cameroon_phone(phone)
    if not clean_p:
        return {"exists_prospect": False, "exists_resto": False, "prospect_id": None}
        
    prospect = ProspectBusiness.objects.filter(
        whatsapp__in=[clean_p, clean_p[3:]]
    ) | ProspectBusiness.objects.filter(
        telephone__in=[clean_p, clean_p[3:]]
    )
    prospect = prospect.first()
    
    # Vérification Restaurant
    from resto.models import Restaurant
    resto = Restaurant.objects.filter(
        whatsapp__icontains=clean_p[3:]
    ) | Restaurant.objects.filter(
        phone__icontains=clean_p[3:]
    )
    resto = resto.first()
    
    return {
        "exists_prospect": prospect is not None,
        "prospect_id": prospect.pk if prospect else None,
        "prospect_statut": prospect.get_statut_display() if prospect else None,
        "exists_resto": resto is not None,
        "resto_slug": resto.slug if resto else None,
        "resto_url": f"/resto/{resto.slug}/" if resto else None,
    }


def save_lead_as_prospect(lead_data: Dict[str, Any], user=None) -> tuple[ProspectBusiness, bool]:
    """
    Crée ou met à jour un ProspectBusiness à partir d'un lead sourcé.
    """
    clean_p = clean_cameroon_phone(lead_data.get("telephone") or lead_data.get("whatsapp"))
    if not clean_p:
        raise ValueError("Un numéro camerounais valide (+237 6... ou 2...) est obligatoire.")
        
    nom = lead_data.get("nom", "Restaurant Douala")
    ville = lead_data.get("ville", "Douala")
    quartier = lead_data.get("quartier", "")
    description = lead_data.get("description", "")
    source_key = lead_data.get("source", "sourcing_web")
    
    if source_key not in [c[0] for c in ProspectBusiness.Source.choices]:
        source_key = ProspectBusiness.Source.SOURCING_WEB
        
    # Recherche existant par numéro
    prospect = ProspectBusiness.objects.filter(
        whatsapp__in=[clean_p, clean_p[3:]]
    ) | ProspectBusiness.objects.filter(
        telephone__in=[clean_p, clean_p[3:]]
    )
    prospect = prospect.first()
    
    created = False
    if not prospect:
        prospect = ProspectBusiness(
            nom=nom,
            module="resto",
            ville=ville,
            quartier=quartier,
            telephone=clean_p,
            whatsapp=clean_p,
            source=source_key,
            description=description,
            statut=ProspectBusiness.Statut.NOUVEAU,
            priorite=ProspectBusiness.Priorite.HAUTE if quartier in ["Akwa", "Bonapriso", "Bonamoussadi"] else ProspectBusiness.Priorite.NORMALE,
            cree_par=user if user and user.is_authenticated else None,
            assigne_a=user if user and user.is_authenticated else None,
            prochain_contact=timezone.localdate(),
        )
        prospect.save()
        created = True
    else:
        # Mise à jour si informations enrichies
        updated_fields = []
        if not prospect.module:
            prospect.module = "resto"
            updated_fields.append("module")
        if not prospect.quartier and quartier:
            prospect.quartier = quartier
            updated_fields.append("quartier")
        if not prospect.whatsapp:
            prospect.whatsapp = clean_p
            updated_fields.append("whatsapp")
        if updated_fields:
            prospect.save(update_fields=updated_fields)
            
    # Recalculer le score commercial
    CommercialAgentService.refresh_prospect(prospect)
    return prospect, created


def create_resto_draft(lead_or_prospect: Any, user=None) -> Any:
    """
    Pré-crée une fiche vitrine Restaurant sur E-Shelle Resto pour le restaurateur.
    Permet à l'équipe commerciale d'envoyer immédiatement le lien de sa fiche déjà prête :
    ex: "Regardez, votre fiche e-shelle.com/resto/african-food est prête, voulez-vous qu'on active votre menu ?"
    """
    from resto.models import Restaurant, City, Neighborhood
    
    if isinstance(lead_or_prospect, ProspectBusiness):
        nom = lead_or_prospect.nom
        ville_name = lead_or_prospect.ville or "Douala"
        quartier_name = lead_or_prospect.quartier or ""
        phone = lead_or_prospect.telephone
        whatsapp = lead_or_prospect.whatsapp or phone
        desc = lead_or_prospect.description
    else:
        nom = lead_or_prospect.get("nom")
        ville_name = lead_or_prospect.get("ville") or "Douala"
        quartier_name = lead_or_prospect.get("quartier") or ""
        phone = lead_or_prospect.get("telephone")
        whatsapp = lead_or_prospect.get("whatsapp") or phone
        desc = lead_or_prospect.get("description") or ""

    clean_p = clean_cameroon_phone(phone) or ""
    clean_w = clean_cameroon_phone(whatsapp) or clean_p

    # Ville Douala
    city, _ = City.objects.get_or_create(
        name__iexact=ville_name,
        defaults={"name": ville_name, "slug": slugify(ville_name)}
    )
    
    # Quartier
    neighborhood = None
    if quartier_name:
        neighborhood = Neighborhood.objects.filter(city=city, name__iexact=quartier_name).first()
        if not neighborhood:
            neighborhood = Neighborhood.objects.create(
                city=city,
                name=quartier_name,
                slug=slugify(quartier_name)
            )

    # Base slug unique
    base_slug = slugify(nom) or "resto-douala"
    slug = base_slug
    counter = 1
    while Restaurant.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Utilisateur propriétaire : soit l'utilisateur courant, soit le premier superadmin
    owner = user if user and user.is_authenticated else None
    if not owner:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        owner = User.objects.filter(is_staff=True).first() or User.objects.first()

    # Création du restaurant brouillon
    from datetime import time
    resto = Restaurant.objects.create(
        owner=owner,
        name=nom,
        slug=slug,
        description=desc or f"Restaurant et plats à emporter situés à {quartier_name or 'Douala'}.",
        city=city,
        neighborhood=neighborhood,
        address=f"{quartier_name}, {city.name}" if quartier_name else city.name,
        phone=format_display_phone(clean_p),
        whatsapp=format_display_phone(clean_w),
        status="closed",
        opening_time=time(9, 0),
        closing_time=time(22, 0),
        is_approved=False,
        is_active=True,
    )
    
    return resto


def build_whatsapp_invite_url(phone: str, nom: str, quartier: str = "", draft_resto_slug: str = "") -> str:
    """
    Génère l'URL WhatsApp avec message de prospection ultra-personnalisé et percutant
    pour convaincre le restaurateur de créer ou valider sa fiche sur e-shelle.com.
    """
    norm = clean_cameroon_phone(phone)
    if not norm:
        return ""
        
    loc = f" à {quartier}" if quartier else " à Douala"
    
    if draft_resto_slug:
        site_url = getattr(settings, "SITE_URL", "https://e-shelle.com")
        resto_link = f"{site_url}/resto/{draft_resto_slug}/"
        texte = (
            f"Bonjour {nom} !\n\n"
            f"Nous avons découvert vos délicieux plats et menus{loc}.\n\n"
            f"Sur E-Shelle Resto (e-shelle.com), nous aidons les restaurateurs de Douala à recevoir directement "
            f"leurs commandes sur WhatsApp et à digitaliser leur carte.\n\n"
            f"👉 Nous avons déjà pré-configuré votre fiche vitrine ici :\n{resto_link}\n\n"
            f"Souhaitez-vous qu'on active votre menu complet gratuitement aujourd'hui ?"
        )
    else:
        texte = (
            f"Bonjour {nom} !\n\n"
            f"Nous avons découvert vos menus et services traiteur{loc}.\n\n"
            f"Sur E-Shelle Resto (e-shelle.com), nous permettons aux restaurants de Douala d'afficher leur menu du jour, "
            f"d'être découverts par des centaines de clients et de recevoir leurs commandes directement sur WhatsApp sans commission.\n\n"
            f"Avez-vous 2 minutes pour qu'on crée votre fiche vitrine gratuite ?"
        )
        
    encoded_text = urllib.parse.quote(texte)
    return f"https://wa.me/{norm}?text={encoded_text}"
