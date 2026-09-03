"""
python manage.py seed_plans

Crée tous les plans tarifaires initiaux de la plateforme E-Shelle.
Idempotent : peut être relancé sans créer de doublons (basé sur le slug).
"""

from django.core.management.base import BaseCommand
from accounts.models import AppPlan


PLANS = [
    # ─── AdGen — Générateur de publicités IA ─────────────────────
    {
        "app_key":      "adgen",
        "slug":         "adgen-pro",
        "name":         "AdGen Pro",
        "level":        "pro",
        "description":  "Accès payant aux campagnes publicitaires IA et vidéos AdGen.",
        "price_xaf":    3000,
        "price_eur":    5,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        1,
        "features": [
            "50 campagnes / mois",
            "Tous les modules (Social, TikTok, Chatbot)",
            "Vidéos publicitaires IA 15s optimisées",
            "10 pays africains",
            "Export JSON + PDF",
            "Historique illimité",
            "Support prioritaire",
        ],
    },

    # ─── E-Shelle Resto ──────────────────────────────────────────
    {
        "app_key":      "resto",
        "slug":         "resto-trial",
        "name":         "Resto Free Trial",
        "level":        "trial",
        "description":  "30 jours pour tester E-Shelle Resto gratuitement.",
        "price_xaf":    0,
        "duration_days": 30,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "Page restaurant complète",
            "Menu en ligne illimité",
            "Bouton WhatsApp & Appel",
            "30 jours offerts",
        ],
    },
    {
        "app_key":      "resto",
        "slug":         "resto-basic",
        "name":         "Resto Basic",
        "level":        "starter",
        "description":  "Visibilité en ligne pour votre restaurant.",
        "price_xaf":    5000,
        "price_eur":    8,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   False,
        "order":        2,
        "features": [
            "Page restaurant + menu",
            "Analytics basiques (vues, clics)",
            "Gestion des avis clients",
            "Dashboard restaurateur",
        ],
    },
    {
        "app_key":      "resto",
        "slug":         "resto-premium",
        "name":         "Resto Premium",
        "level":        "pro",
        "description":  "Maximisez votre visibilité et vos commandes.",
        "price_xaf":    15000,
        "price_eur":    23,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        3,
        "features": [
            "Mise en avant sur la page d'accueil",
            "Bannière hero (slideshow)",
            "Analytics avancés (7 jours, export)",
            "Badge Premium",
            "Notifications en temps réel",
            "Support prioritaire",
        ],
    },

    # ─── E-Shelle Love — Rencontres ──────────────────────────────
    {
        "app_key":      "rencontres",
        "slug":         "rencontres-free",
        "name":         "Love Gratuit",
        "level":        "free",
        "description":  "Commencez à rencontrer gratuitement.",
        "price_xaf":    0,
        "duration_days": 0,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "10 likes / jour",
            "5 messages / jour",
            "Voir les profils publics",
            "1 photo de profil",
        ],
    },
    {
        "app_key":      "rencontres",
        "slug":         "rencontres-silver",
        "name":         "Love Silver",
        "level":        "starter",
        "description":  "Plus de likes, messagerie sans limites.",
        "price_xaf":    2500,
        "price_eur":    4,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   False,
        "order":        2,
        "features": [
            "50 likes / jour",
            "Messages illimités",
            "3 photos de profil",
            "Filtres de recherche avancés",
        ],
    },
    {
        "app_key":      "rencontres",
        "slug":         "rencontres-gold",
        "name":         "Love Gold",
        "level":        "pro",
        "description":  "Voir qui vous a liké, super likes et plus.",
        "price_xaf":    5000,
        "price_eur":    8,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        3,
        "features": [
            "Likes illimités",
            "5 super likes / jour",
            "Voir qui vous a liké",
            "Rembobiner le dernier profil",
            "6 photos de profil",
            "Badge Gold",
        ],
    },
    {
        "app_key":      "rencontres",
        "slug":         "rencontres-platinum",
        "name":         "Love Platinum",
        "level":        "enterprise",
        "description":  "L'expérience rencontres la plus complète.",
        "price_xaf":    10000,
        "price_eur":    15,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   False,
        "order":        4,
        "features": [
            "Tout Gold inclus",
            "1 boost profil / semaine",
            "Mode incognito",
            "Filtres diaspora & international",
            "Photos illimitées",
            "Support 24/7",
            "Badge Platinum",
        ],
    },

    # ─── Njangi Digital ──────────────────────────────────────────
    {
        "app_key":      "njangi",
        "slug":         "njangi-free",
        "name":         "Njangi Gratuit",
        "level":        "free",
        "description":  "Gérez votre première tontine gratuitement.",
        "price_xaf":    0,
        "duration_days": 0,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "1 groupe de tontine",
            "Max 20 membres",
            "Cotisations & séances",
            "Prêts entre membres",
        ],
    },
    {
        "app_key":      "njangi",
        "slug":         "njangi-pro",
        "name":         "Njangi Pro",
        "level":        "pro",
        "description":  "Gérez plusieurs groupes sans limites.",
        "price_xaf":    2000,
        "price_eur":    3,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        2,
        "features": [
            "Groupes illimités",
            "Membres illimités",
            "Export rapports PDF",
            "Notifications SMS",
            "Statistiques avancées",
            "Support prioritaire",
        ],
    },

    # ─── EduCam Pro ──────────────────────────────────────────────
    {
        "app_key":      "edu",
        "slug":         "edu-quarterly",
        "name":         "EduCam Trimestriel",
        "level":        "starter",
        "description":  "Accès complet pendant 3 mois.",
        "price_xaf":    5000,
        "price_eur":    8,
        "duration_days": 90,
        "is_free":      False,
        "is_popular":   False,
        "order":        1,
        "features": [
            "Tous les sujets & corrections",
            "Téléchargement PDF illimité",
            "Vidéos & ressources audio",
            "1 appareil",
            "Valide 90 jours",
        ],
    },
    {
        "app_key":      "edu",
        "slug":         "edu-annual",
        "name":         "EduCam Annuel",
        "level":        "pro",
        "description":  "La meilleure valeur pour toute l'année scolaire.",
        "price_xaf":    15000,
        "price_eur":    23,
        "duration_days": 365,
        "is_free":      False,
        "is_popular":   True,
        "order":        2,
        "features": [
            "Tout le plan Trimestriel",
            "Valide 365 jours",
            "Mises à jour des sujets incluses",
            "Support par email",
        ],
    },

    # ─── E-Shelle Agro ───────────────────────────────────────────
    {
        "app_key":      "agro",
        "slug":         "agro-free",
        "name":         "Agro Gratuit",
        "level":        "free",
        "description":  "Publiez vos produits agroalimentaires gratuitement.",
        "price_xaf":    0,
        "duration_days": 0,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "5 annonces actives",
            "3 photos par annonce",
            "Visibilité standard",
        ],
    },
    {
        "app_key":      "agro",
        "slug":         "agro-pro",
        "name":         "Agro Pro",
        "level":        "pro",
        "description":  "Maximisez vos ventes agricoles.",
        "price_xaf":    3000,
        "price_eur":    5,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        2,
        "features": [
            "Annonces illimitées",
            "10 photos par annonce",
            "Mise en avant en page d'accueil",
            "Badge Vendeur Vérifié",
            "Analytics ventes",
        ],
    },
    # ─── E-Shelle Allemand ──────────────────────────────────────────
    {
        "app_key":      "allemand",
        "slug":         "allemand-free",
        "name":         "Allemand Gratuit",
        "level":        "free",
        "description":  "Découvrez les simulations d'entretien d'Ausbildung.",
        "price_xaf":    0,
        "duration_days": 0,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "1 simulation d'essai gratuit",
            "Secteur Autre / Candidature spontanée",
            "Correction IA basique",
        ],
    },
    {
        "app_key":      "allemand",
        "slug":         "allemand-pro",
        "name":         "Allemand Premium",
        "level":        "pro",
        "description":  "Préparez sereinement votre départ pour l'Allemagne.",
        "price_xaf":    9000,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        2,
        "features": [
            "Simulations illimitées par secteur",
            "Correction linguistique détaillée",
            "Vocabulaire recommandé & Conseils RH",
            "CV Lebenslauf officiel illimité",
        ],
    },
    # ─── E-Shelle Français (TEF/TCF) ──────────────────────────────
    {
        "app_key":      "prep",
        "slug":         "prep-free",
        "name":         "Français Gratuit",
        "level":        "free",
        "description":  "Accédez aux bases de la préparation.",
        "price_xaf":    0,
        "duration_days": 0,
        "is_free":      True,
        "is_popular":   False,
        "order":        1,
        "features": [
            "Sujets d'évaluation de base",
            "Visibilité standard",
        ],
    },
    {
        "app_key":      "prep",
        "slug":         "prep-pro",
        "name":         "Français Premium",
        "level":        "pro",
        "description":  "Réussissez vos examens blancs officiels TEF/TCF.",
        "price_xaf":    9000,
        "duration_days": 30,
        "is_free":      False,
        "is_popular":   True,
        "order":        2,
        "features": [
            "Examen blanc type examen officiel (TEF / TCF Canada)",
            "Coach de correction IA illimité (24h/7)",
            "Génération de CV canadien conforme (ATS-friendly)",
            "Adaptation de votre CV aux offres d'emploi en 1 clic",
            "Groupe WhatsApp d'accompagnement E-Shelle",
            "Préparation aux tests assistée par IA",
            "Derniers sujets d'examens réels avec correction complète",
            "Accès illimité : Toutes les offres d'emploi Canada",
            "Accès illimité : Bourses d'études & opportunités de visa Canada",
            "Vérification de l'éligibilité (Calculateur CRS)",
            "Accès à la liste exclusive des employeurs canadiens (EIMT)",
            "Préparation intensive aux entretiens d'embauche",
            "Coach IA pour l'immigration Canada",
        ],
    },
]


class Command(BaseCommand):
    help = "Initialise tous les plans tarifaires de la plateforme E-Shelle."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for data in PLANS:
            features = data.pop("features", [])
            obj, is_new = AppPlan.objects.update_or_create(
                slug=data["slug"],
                defaults={**data, "features": features},
            )
            if is_new:
                created += 1
                self.stdout.write(f"  CREE   {obj.name}")
            else:
                updated += 1
                self.stdout.write(f"  OK     {obj.name}")

        self.stdout.write(
            f"\nTermine : {created} plan(s) cree(s), {updated} mis a jour."
        )
        self.stdout.write(f"Total plans en base : {AppPlan.objects.count()}")
