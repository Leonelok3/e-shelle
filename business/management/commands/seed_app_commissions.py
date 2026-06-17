from django.core.management.base import BaseCommand

from business.models import AppCommission, PartnerLevel


REF_LINK = "http://127.0.0.1:8025/ref/YRB1RY94/"
BUSINESS_KEY_PRICE_XAF = 9900
PROVIDER_COMMISSION_RATE = 30


def generic_script(label):
    return (
        f"Bonjour, E-Shelle peut aider avec {label}: une vitrine simple, "
        f"un lien WhatsApp, plus de visibilite et des campagnes propres. "
        f"Voulez-vous voir une demo rapide ? Lien: {REF_LINK}"
    )


class Command(BaseCommand):
    help = "Cree le catalogue des commissions Business Key."

    def handle(self, *args, **options):
        apps_data = [
            {
                "app_name": AppCommission.AppName.MARKETPLACE,
                "label": "Marketplace",
                "description": "Vendre des fiches, vitrines et offres marketplace aux commerces locaux.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": False,
                "priority": 10,
                "icon": "M",
                "script_vente": generic_script("la marketplace E-Shelle"),
            },
            {
                "app_name": AppCommission.AppName.LOVE,
                "label": "E-Shelle Love",
                "description": "Rencontres serieuses et profils locaux avec abonnement a 5 000 FCFA/mois.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": True,
                "priority": 20,
                "icon": "L",
                "script_vente": f"Bonjour, E-Shelle Love aide les personnes serieuses a faire des rencontres plus organisees et plus respectueuses. L'abonnement commence a 5 000 FCFA/mois. Voulez-vous voir comment ca marche ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.FORMATIONS,
                "label": "Langues & Formations IA/Marketing",
                "description": "Cours de langue, IA, marketing digital et vente en ligne a partir de 5 000 FCFA/mois.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": False,
                "priority": 30,
                "icon": "F",
                "script_vente": f"Bonjour, E-Shelle propose des cours de langue et formations IA/Marketing a partir de 5 000 FCFA/mois. On apprend a mieux parler, vendre en ligne, utiliser l'IA et creer du contenu. Voulez-vous voir le programme ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.NJANGI,
                "label": "Njangi Tontine",
                "description": "Digitalisation des tontines, cotisations, mains et rapports.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": True,
                "priority": 40,
                "icon": "N",
                "script_vente": f"Bonjour, Njangi digitalise les tontines. Votre groupe peut gerer sa caisse en ligne. Demo gratuite ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.AGRO,
                "label": "Agro B2B/B2C",
                "description": "Connecter producteurs, revendeurs, restaurants et acheteurs.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": False,
                "priority": 50,
                "icon": "A",
                "script_vente": f"Bonjour, E-Shelle Agro connecte producteurs et acheteurs au Cameroun. Voulez-vous voir comment creer votre vitrine agro ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.TCHASLUCPAY,
                "label": "Microfinance Tchaslucpay",
                "description": "Collecte, depot, retrait et suivi terrain pour microfinance.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": True,
                "priority": 60,
                "icon": "T",
                "script_vente": f"Bonjour, Tchaslucpay permet d'envoyer et recevoir de l'argent facilement. Je peux vous activer un compte en 5 minutes ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.TRANSPORT,
                "label": "Transport & Courses",
                "description": "Connecter passagers, conducteurs, coursiers et services locaux.",
                "commission_rate": PROVIDER_COMMISSION_RATE,
                "is_recurring": False,
                "priority": 70,
                "icon": "TR",
                "script_vente": f"Bonjour, E-Shelle Transport connecte passagers et conducteurs a Douala. Interesse pour rejoindre ou utiliser ? Lien: {REF_LINK}",
            },
            {
                "app_name": AppCommission.AppName.PHARMA,
                "label": "Pharma",
                "description": "Vitrine pharmacie, disponibilite produit et contact WhatsApp.",
                "priority": 80,
                "icon": "PH",
                "script_vente": generic_script("les pharmacies et produits de sante"),
            },
            {
                "app_name": AppCommission.AppName.PRESSING,
                "label": "Pressing",
                "description": "Rendre les pressings visibles par ville, quartier et WhatsApp.",
                "priority": 90,
                "icon": "P",
                "script_vente": generic_script("les pressings et services de nettoyage"),
            },
            {
                "app_name": AppCommission.AppName.RESTO,
                "label": "Resto",
                "description": "Fiches restaurants, menus, commandes WhatsApp et campagnes locales.",
                "priority": 100,
                "icon": "R",
                "script_vente": generic_script("les restaurants et menus WhatsApp"),
            },
            {
                "app_name": AppCommission.AppName.IMMOBILIER,
                "label": "Immobilier",
                "description": "Biens, agences, locations et vitrines publiques.",
                "priority": 110,
                "icon": "IM",
                "script_vente": generic_script("l'immobilier et les vitrines de biens"),
            },
            {
                "app_name": AppCommission.AppName.AUTO,
                "label": "Auto",
                "description": "Annonces vehicules, pieces, location et contacts qualifies.",
                "priority": 120,
                "icon": "AU",
                "script_vente": generic_script("les annonces auto"),
            },
            {
                "app_name": AppCommission.AppName.GAZ,
                "label": "Gaz & Livraison",
                "description": "Depot gaz, disponibilite, livraison et demandes WhatsApp.",
                "priority": 130,
                "icon": "G",
                "script_vente": generic_script("les depots de gaz et livraisons"),
            },
            {
                "app_name": AppCommission.AppName.JOBS,
                "label": "Jobs",
                "description": "Offres d'emploi, missions et opportunites locales.",
                "priority": 140,
                "icon": "J",
                "script_vente": generic_script("les emplois et missions"),
            },
            {
                "app_name": AppCommission.AppName.ADGEN,
                "label": "AdGen",
                "description": "Generation de publicites, accroches et scripts marketing IA.",
                "priority": 150,
                "icon": "AD",
                "script_vente": generic_script("les publicites IA AdGen"),
            },
            {
                "app_name": AppCommission.AppName.EDU,
                "label": "EduCam Pro",
                "description": "Education, examens camerounais, revision et contenus utiles.",
                "priority": 160,
                "icon": "ED",
                "script_vente": generic_script("l'education et les examens"),
            },
            {
                "app_name": AppCommission.AppName.SANTE,
                "label": "Sante",
                "description": "Produits, services et orientation sante.",
                "priority": 170,
                "icon": "S",
                "script_vente": generic_script("les services sante"),
            },
            {
                "app_name": AppCommission.AppName.SIMPLO,
                "label": "Simplo",
                "description": "Outils simples pour organiser services, clients et operations.",
                "priority": 180,
                "icon": "SI",
                "script_vente": generic_script("Simplo et l'organisation digitale"),
            },
            {
                "app_name": AppCommission.AppName.MARKET,
                "label": "Market general",
                "description": "Achat, vente et annonces generales E-Shelle.",
                "priority": 190,
                "icon": "MG",
                "script_vente": generic_script("le market general E-Shelle"),
            },
            {
                "app_name": AppCommission.AppName.SERVICES_WEB,
                "label": "Sites Web & Logiciels",
                "description": "Sites vitrines, boutiques, catalogues et logiciels personnalises pour PME.",
                "priority": 200,
                "icon": "SW",
                "script_vente": f"Bonjour, E-Shelle peut creer un site web, une boutique, un catalogue ou un logiciel personnalise pour votre activite. On peut commencer par une page vitrine avec WhatsApp et SEO local. Voulez-vous une estimation ? Lien: {REF_LINK}",
            },
        ]

        created = 0
        for data in apps_data:
            data.setdefault("commission_rate", PROVIDER_COMMISSION_RATE)
            data.setdefault("commission_fixe", 0)
            data.setdefault("is_recurring", False)
            data.setdefault("is_active", True)
            _, was_created = AppCommission.objects.update_or_create(
                app_name=data["app_name"],
                defaults=data,
            )
            created += int(was_created)

        all_apps = list(AppCommission.objects.filter(is_active=True))
        app_by_name = {app.app_name: app for app in all_apps}
        level_data = [
            {
                "level": PartnerLevel.Level.GRATUIT,
                "label": "Gratuit",
                "prix_fcfa": 0,
                "description": "Commencer avec les scripts de base et le lien partenaire.",
                "bonus_description": "Ideal pour tester le terrain sans depense.",
                "apps": ["marketplace", "resto", "pressing", "gaz"],
            },
            {
                "level": PartnerLevel.Level.BUSINESS_KEY,
                "label": "Business Key",
                "prix_fcfa": BUSINESS_KEY_PRICE_XAF,
                "description": "Prix unique avec acces complet aux outils marketing et IA E-Shelle.",
                "bonus_description": "50% sur partenaires Business Key, 30% sur frais prestataires valides.",
                "apps": [app.app_name for app in all_apps],
            },
            {
                "level": PartnerLevel.Level.AMBASSADEUR,
                "label": "Ambassadeur Pro",
                "prix_fcfa": BUSINESS_KEY_PRICE_XAF,
                "description": "Ancien niveau conserve pour compatibilite. Meme acces complet que Business Key.",
                "bonus_description": "Acces complet, prix unique et commissions simplifiees.",
                "apps": [
                    "marketplace",
                    "resto",
                    "pressing",
                    "gaz",
                    "pharma",
                    "agro",
                    "adgen",
                    "services_web",
                    "immobilier",
                    "auto",
                    "jobs",
                    "formations",
                    "love",
                ],
            },
            {
                "level": PartnerLevel.Level.MULTI_APP,
                "label": "Multi-App Master",
                "prix_fcfa": BUSINESS_KEY_PRICE_XAF,
                "description": "Ancien niveau conserve pour compatibilite. Acces complet au prix unique.",
                "bonus_description": "Vision multi-app et commissions 50/30.",
                "apps": [app.app_name for app in all_apps],
            },
        ]

        for data in level_data:
            apps = [app_by_name[name] for name in data.pop("apps") if name in app_by_name]
            level, _ = PartnerLevel.objects.update_or_create(
                level=data["level"],
                defaults=data,
            )
            level.apps_accessibles.set(apps)

        self.stdout.write(self.style.SUCCESS(f"Catalogue Business Key pret: {created} nouvelle(s) app(s)."))
