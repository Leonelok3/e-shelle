"""
dashboard/views.py — Tableau de bord multi-rôle E-Shelle
Admin, formateur, hub unifié (apprenant / client / vendeur / parent).
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.conf import settings
from datetime import timedelta


# ── Catalogue de tous les services E-Shelle ──────────────────────────────────

ESHELLE_SERVICES = [
    {
        "key": "formations",
        "name": "Formations",
        "icon": "📚",
        "color": "#8B5CF6",
        "external_url": getattr(settings, "FORMATIONS_PUBLIC_URL", "http://127.0.0.1:8000/formations/"),
        "desc": "Apprenez de nouvelles compétences en ligne",
        "category": "education",
    },
    {
        "key": "edu",
        "name": "Mapex",
        "icon": "🎓",
        "color": "#0EA5E9",
        "external_url": getattr(settings, "MAPEX_PUBLIC_URL", "http://127.0.0.1:8000/edu/"),
        "desc": "Plateforme e-learning camerounaise certifiée",
        "category": "education",
    },
    {
        "key": "math_cm",
        "name": "Math CM",
        "icon": "📐",
        "color": "#7C3AED",
        "external_url": getattr(settings, "MATHS_PUBLIC_URL", "http://127.0.0.1:8000/maths/"),
        "desc": "Mathématiques secondaire MINESEC",
        "category": "education",
    },
    {
        "key": "boutique",
        "name": "Boutique",
        "icon": "🛒",
        "color": "#10B981",
        "external_url": getattr(settings, "BOUTIQUE_PUBLIC_URL", "http://127.0.0.1:8000/boutique/"),
        "desc": "Produits digitaux & physiques",
        "category": "commerce",
    },
    {
        "key": "agro",
        "name": "E-Shelle Agro",
        "icon": "🌿",
        "color": "#84CC16",
        "external_url": getattr(settings, "AGRO_PUBLIC_URL", "http://127.0.0.1:8000/agro/"),
        "desc": "Marketplace agroalimentaire africaine",
        "category": "commerce",
    },
    {
        "key": "immobilier",
        "name": "Immobilier",
        "icon": "🏠",
        "color": "#14B8A6",
        "external_url": getattr(settings, "IMMOBILIER_PUBLIC_URL", "http://127.0.0.1:8000/immobilier/"),
        "desc": "Achat, vente & location de biens",
        "category": "commerce",
    },
    {
        "key": "auto",
        "name": "Auto Cameroun",
        "icon": "🚗",
        "color": "#F59E0B",
        "external_url": getattr(settings, "AUTO_PUBLIC_URL", "http://127.0.0.1:8000/auto/"),
        "desc": "Achat et vente de véhicules",
        "category": "commerce",
    },
    {
        "key": "annonces",
        "name": "E-Shelle Market",
        "icon": "📢",
        "color": "#64748B",
        "external_url": getattr(settings, "MARKET_PUBLIC_URL", "http://127.0.0.1:8000/annonces/"),
        "desc": "Marketplace généraliste pour acheter, vendre et louer",
        "category": "commerce",
    },
    {
        "key": "resto",
        "name": "E-Shelle Resto",
        "icon": "🍽️",
        "color": "#F97316",
        "external_url": getattr(settings, "RESTO_PUBLIC_URL", "http://127.0.0.1:8000/resto/"),
        "desc": "Découvrez les restaurants du Cameroun",
        "category": "lifestyle",
    },
    {
        "key": "gaz",
        "name": "E-Shelle Gaz",
        "icon": "🔥",
        "color": "#FF6B00",
        "external_url": getattr(settings, "GAZ_PUBLIC_URL", "http://127.0.0.1:8000/gaz/"),
        "desc": "Livraison de gaz domestique",
        "category": "lifestyle",
    },
    {
        "key": "pharma",
        "name": "E-Shelle Pharma",
        "icon": "💊",
        "color": "#EC4899",
        "external_url": getattr(settings, "PHARMA_PUBLIC_URL", "http://127.0.0.1:8000/pharma/"),
        "desc": "Annuaire pharmacies & médicaments",
        "category": "lifestyle",
    },
    {
        "key": "pressing",
        "name": "Pressing",
        "icon": "👔",
        "color": "#6366F1",
        "external_url": getattr(settings, "PRESSING_PUBLIC_URL", "http://127.0.0.1:8000/pressing/"),
        "desc": "Pressing & blanchisserie à domicile",
        "category": "lifestyle",
    },
    {
        "key": "rencontres",
        "name": "E-Shelle Love",
        "icon": "❤️",
        "color": "#E8436A",
        "external_url": getattr(settings, "LOVE_PUBLIC_URL", "http://127.0.0.1:8000/rencontres/"),
        "desc": "Rencontres sérieuses au Cameroun",
        "category": "lifestyle",
    },
    {
        "key": "njangi",
        "name": "Njangi Digital",
        "icon": "🤝",
        "color": "#1B6CA8",
        "external_url": getattr(settings, "NJANGI_PUBLIC_URL", "http://127.0.0.1:8000/njangi/"),
        "desc": "Tontines & fonds communs numériques",
        "category": "finance",
    },
    {
        "key": "tchaslucpay",
        "name": "Tchaslucpay",
        "icon": "💳",
        "color": "#0FA36B",
        "external_url": getattr(settings, "TCHASLUCPAY_PUBLIC_URL", "http://127.0.0.1:8001/"),
        "desc": "Microfinance digitale, collectes, retraits et reçus PDF",
        "category": "finance",
    },
    {
        "key": "simplo",
        "name": "Simplo",
        "icon": "🏍️",
        "color": "#F59E0B",
        "external_url": getattr(settings, "SIMPLO_PUBLIC_URL", "http://127.0.0.1:8020/"),
        "desc": "Motos, livraisons et courses de quartier par appel ou WhatsApp",
        "category": "terrain",
    },
    {
        "key": "jobs",
        "name": "E-Shelle Jobs",
        "icon": "💼",
        "color": "#2563EB",
        "external_url": getattr(settings, "JOBS_PUBLIC_URL", "http://127.0.0.1:8000/jobs/"),
        "desc": "Emplois, stages et missions vérifiées",
        "category": "business",
    },
    {
        "key": "adgen",
        "name": "AdGen IA",
        "icon": "✨",
        "color": "#6C3FE8",
        "external_url": getattr(settings, "ADGEN_PUBLIC_URL", "http://127.0.0.1:8000/pub/"),
        "desc": "Créez des publicités avec l'intelligence artificielle",
        "category": "business",
    },
    {
        "key": "services",
        "name": "Services Web",
        "icon": "🌐",
        "color": "#3B82F6",
        "external_url": getattr(settings, "SERVICES_PUBLIC_URL", "http://127.0.0.1:8000/services/"),
        "desc": "Sites web, applications, design sur mesure",
        "category": "business",
    },
    {
        "key": "ai",
        "name": "E-Shelle AI",
        "icon": "🤖",
        "color": "#06B6D4",
        "external_url": getattr(settings, "AI_PUBLIC_URL", "http://127.0.0.1:8000/ai/"),
        "desc": "Votre assistant IA personnel intelligent",
        "category": "business",
    },
]

CATEGORY_LABELS = {
    "education": "🎓 Éducation",
    "commerce":  "🛒 Commerce & Marché",
    "lifestyle": "🌟 Lifestyle & Services",
    "finance":   "💰 Finance & Épargne",
    "business":  "💼 Business & IA",
}


@login_required
def index(request):
    """Dashboard principal — admin et formateur gardent leur vue spécifique,
    tous les autres utilisateurs voient le hub unifié."""
    user = request.user
    role = getattr(user, "role", "STUDENT")

    if role in ("SUPERADMIN",) or user.is_superuser:
        return _dashboard_admin(request)
    elif role == "TEACHER":
        return _dashboard_formateur(request)
    else:
        return _dashboard_hub(request)


# ── Hub unifié ────────────────────────────────────────────────────────────────

def _dashboard_hub(request):
    """Dashboard hub — tous les utilisateurs non-admin/non-formateur.
    Affiche les stats personnelles + toutes les apps E-Shelle."""
    user = request.user
    stats = {}  # dict key → valeur pour les stats rapides

    # ── Formations ──────────────────────────────────────────────────────────
    try:
        from formations.models import Inscription, Progression, Certificat
        nb_inscriptions = Inscription.objects.filter(utilisateur=user).count()
        nb_completees   = Progression.objects.filter(utilisateur=user, completee=True).count()
        nb_certificats  = Certificat.objects.filter(utilisateur=user).count()
        stats["formations"] = {
            "label": "Formations",
            "icon": "📚",
            "color": "#8B5CF6",
            "items": [
                {"v": nb_inscriptions, "l": "inscriptions"},
                {"v": nb_certificats,  "l": "certificats"},
            ],
        }
        # Dernières inscriptions pour la section "En cours"
        inscriptions = Inscription.objects.filter(
            utilisateur=user
        ).select_related("formation").order_by("-date_inscription")[:6]
        certificats = Certificat.objects.filter(
            utilisateur=user
        ).select_related("formation")[:3]
    except Exception:
        nb_inscriptions = nb_completees = nb_certificats = 0
        inscriptions = certificats = []

    # ── Boutique ────────────────────────────────────────────────────────────
    try:
        from boutique.models import Commande, Telechargement
        nb_commandes       = Commande.objects.filter(utilisateur=user).count()
        nb_telechargements = Telechargement.objects.filter(utilisateur=user).count()
        telechargements    = Telechargement.objects.filter(
            utilisateur=user
        ).select_related("produit").order_by("-created_at")[:4]
        if nb_commandes or nb_telechargements:
            stats["boutique"] = {
                "label": "Boutique",
                "icon": "🛒",
                "color": "#10B981",
                "items": [
                    {"v": nb_commandes,       "l": "commandes"},
                    {"v": nb_telechargements, "l": "téléchargements"},
                ],
            }
    except Exception:
        nb_commandes = nb_telechargements = 0
        telechargements = []

    # ── Services / Devis ────────────────────────────────────────────────────
    try:
        from services.models import Devis
        nb_devis = Devis.objects.filter(utilisateur=user).count()
        if nb_devis:
            stats["services"] = {
                "label": "Services",
                "icon": "🌐",
                "color": "#3B82F6",
                "items": [{"v": nb_devis, "l": "devis"}],
            }
        devis = Devis.objects.filter(utilisateur=user).order_by("-created_at")[:3]
    except Exception:
        nb_devis = 0
        devis = []

    # ── Njangi Digital ──────────────────────────────────────────────────────
    try:
        from njangi.models import Membre
        nb_groupes = Membre.objects.filter(
            utilisateur=user, statut="actif"
        ).count()
        if nb_groupes:
            stats["njangi"] = {
                "label": "Njangi Digital",
                "icon": "🤝",
                "color": "#1B6CA8",
                "items": [{"v": nb_groupes, "l": "groupes actifs"}],
            }
    except Exception:
        nb_groupes = 0

    # ── AdGen ───────────────────────────────────────────────────────────────
    try:
        from adgen.models import Campaign
        nb_campaigns = Campaign.objects.filter(user=user).count()
        if nb_campaigns:
            stats["adgen"] = {
                "label": "AdGen IA",
                "icon": "✨",
                "color": "#6C3FE8",
                "items": [{"v": nb_campaigns, "l": "campagnes"}],
            }
    except Exception:
        nb_campaigns = 0

    # ── E-Shelle AI ─────────────────────────────────────────────────────────
    try:
        from e_shelle_ai.models import Conversation
        nb_convs = Conversation.objects.filter(user=user).count()
        if nb_convs:
            stats["ai"] = {
                "label": "E-Shelle AI",
                "icon": "🤖",
                "color": "#06B6D4",
                "items": [{"v": nb_convs, "l": "conversations"}],
            }
    except Exception:
        nb_convs = 0

    # ── Rencontres ──────────────────────────────────────────────────────────
    try:
        from rencontres.models.profile import ProfilRencontre
        from rencontres.models.matching import Match
        profil_love = ProfilRencontre.objects.filter(user=user).first()
        if profil_love:
            nb_matchs = Match.objects.filter(
                profil_a=profil_love
            ).count() + Match.objects.filter(
                profil_b=profil_love
            ).count()
            if nb_matchs:
                stats["rencontres"] = {
                    "label": "E-Shelle Love",
                    "icon": "❤️",
                    "color": "#E8436A",
                    "items": [{"v": nb_matchs, "l": "matchs"}],
                }
    except Exception:
        profil_love = None

    # ── Immobilier ──────────────────────────────────────────────────────────
    try:
        from immobilier_cameroun.models import Bien
        nb_biens = Bien.objects.filter(proprietaire=user, statut="PUBLIE").count()
        if nb_biens:
            stats["immobilier"] = {
                "label": "Immobilier",
                "icon": "🏠",
                "color": "#14B8A6",
                "items": [{"v": nb_biens, "l": "biens publiés"}],
            }
    except Exception:
        nb_biens = 0

    # ── Auto Cameroun ───────────────────────────────────────────────────────
    try:
        from auto_cameroun.models import Vehicule
        nb_vehicules = Vehicule.objects.filter(proprietaire=user, statut="PUBLIE").count()
        if nb_vehicules:
            stats["auto"] = {
                "label": "Auto Cameroun",
                "icon": "🚗",
                "color": "#F59E0B",
                "items": [{"v": nb_vehicules, "l": "véhicules publiés"}],
            }
    except Exception:
        nb_vehicules = 0

    # ── Annonces ────────────────────────────────────────────────────────────
    try:
        from annonces_cam.models import Annonce
        nb_annonces = Annonce.objects.filter(vendeur=user, statut="PUBLIEE").count()
        if nb_annonces:
            stats["annonces"] = {
                "label": "E-Shelle Market",
                "icon": "📢",
                "color": "#64748B",
                "items": [{"v": nb_annonces, "l": "offres actives"}],
            }
    except Exception:
        nb_annonces = 0

    # ── Resto (gérant) ──────────────────────────────────────────────────────
    try:
        from resto.models import Restaurant
        nb_restaurants = Restaurant.objects.filter(
            owner=user, is_active=True
        ).count()
        if nb_restaurants:
            stats["resto"] = {
                "label": "E-Shelle Resto",
                "icon": "🍽️",
                "color": "#F97316",
                "items": [{"v": nb_restaurants, "l": "restaurants"}],
            }
    except Exception:
        nb_restaurants = 0

    # ── Gaz (dépôt) ─────────────────────────────────────────────────────────
    try:
        from gaz.models import DepotGaz
        nb_depots = DepotGaz.objects.filter(gerant=user, is_active=True).count()
        if nb_depots:
            stats["gaz"] = {
                "label": "E-Shelle Gaz",
                "icon": "🔥",
                "color": "#FF6B00",
                "items": [{"v": nb_depots, "l": "dépôts actifs"}],
            }
    except Exception:
        nb_depots = 0

    # ── Pharma (pharmacie) ──────────────────────────────────────────────────
    try:
        from pharma.models import Pharmacie
        nb_pharmacies = Pharmacie.objects.filter(gerant=user, is_active=True).count()
        if nb_pharmacies:
            stats["pharma"] = {
                "label": "E-Shelle Pharma",
                "icon": "💊",
                "color": "#EC4899",
                "items": [{"v": nb_pharmacies, "l": "pharmacies"}],
            }
    except Exception:
        nb_pharmacies = 0

    # ── Pressing ────────────────────────────────────────────────────────────
    try:
        from pressing.models import Pressing, CommandePressing
        nb_pressings = Pressing.objects.filter(
            gerant=user, is_active=True
        ).count()
        if nb_pressings:
            nb_cmds_pressing = CommandePressing.objects.filter(
                pressing__gerant=user,
                statut__in=["en_attente", "confirme", "en_cours"]
            ).count()
            stats["pressing"] = {
                "label": "Pressing",
                "icon": "👔",
                "color": "#6366F1",
                "items": [
                    {"v": nb_pressings,      "l": "établissements"},
                    {"v": nb_cmds_pressing,  "l": "commandes en cours"},
                ],
            }
    except Exception:
        nb_pressings = 0

    # ── Regroupement des services par catégorie ──────────────────────────────
    from django.urls import reverse, NoReverseMatch
    services_by_category = {}
    for svc in ESHELLE_SERVICES:
        cat = svc["category"]
        if cat not in services_by_category:
            services_by_category[cat] = {
                "label": CATEGORY_LABELS[cat],
                "services": [],
            }
        # Tenter de résoudre l'URL (certaines apps peuvent ne pas être incluses)
        if svc.get("external_url"):
            url = svc["external_url"]
        else:
            try:
                url = reverse(svc["url_name"])
            except NoReverseMatch:
                url = "#"
        services_by_category[cat]["services"].append({
            **svc,
            "url": url,
            "has_activity": svc["key"] in stats,
        })

    context = {
        "role":               getattr(user, "role", "STUDENT"),
        "stats":              stats,
        "inscriptions":       inscriptions,
        "certificats":        certificats,
        "telechargements":    telechargements,
        "devis":              devis,
        "nb_inscriptions":    nb_inscriptions,
        "nb_completees":      nb_completees,
        "nb_certificats":     nb_certificats,
        "nb_commandes":       nb_commandes,
        "services_by_category": services_by_category,
    }
    return render(request, "dashboard/hub.html", context)


# ── Dashboard Admin ───────────────────────────────────────────────────────────

def _dashboard_admin(request):
    """Dashboard administrateur — vue globale plateforme."""
    from formations.models import Formation, Inscription
    from boutique.models import Commande, Produit
    from accounts.models import CustomUser
    from dashboard.models import Notification
    from payments.models import Transaction

    nb_users      = CustomUser.objects.count()
    nb_formations = Formation.objects.filter(is_published=True).count()
    nb_inscrits   = Inscription.objects.count()
    nb_commandes  = Commande.objects.filter(statut="payee").count()

    date_debut = timezone.now() - timedelta(days=30)
    revenus    = Transaction.objects.filter(
        statut="succes", created_at__gte=date_debut
    ).aggregate(total=Sum("montant"))["total"] or 0

    date_7j   = timezone.now() - timedelta(days=7)
    new_users = CustomUser.objects.filter(date_joined__gte=date_7j).count()

    transactions = Transaction.objects.select_related(
        "utilisateur"
    ).order_by("-created_at")[:10]

    notifications = Notification.objects.filter(
        destinataire=request.user, lue=False
    ).order_by("-created_at")[:5]

    context = {
        "role":          "admin",
        "nb_users":      nb_users,
        "nb_formations": nb_formations,
        "nb_inscrits":   nb_inscrits,
        "nb_commandes":  nb_commandes,
        "revenus":       revenus,
        "new_users":     new_users,
        "transactions":  transactions,
        "notifications": notifications,
    }
    return render(request, "dashboard/admin.html", context)


# ── Dashboard Formateur ───────────────────────────────────────────────────────

def _dashboard_formateur(request):
    """Dashboard formateur — ses cours et leurs stats."""
    from formations.models import Formation, Inscription, AvisFormation

    formations = Formation.objects.filter(
        formateur=request.user
    ).annotate(nb_inscriptions=Count("inscriptions")).order_by("-created_at")

    nb_apprenants = Inscription.objects.filter(
        formation__formateur=request.user
    ).values("utilisateur").distinct().count()

    context = {
        "role":          "formateur",
        "formations":    formations,
        "nb_apprenants": nb_apprenants,
    }
    return render(request, "dashboard/formateur.html", context)


# ── Notifications ─────────────────────────────────────────────────────────────

@login_required
def notifications(request):
    """Page notifications."""
    from dashboard.models import Notification
    notifs = Notification.objects.filter(
        destinataire=request.user
    ).order_by("-created_at")[:50]
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    return render(request, "dashboard/notifications.html", {"notifications": notifs})
