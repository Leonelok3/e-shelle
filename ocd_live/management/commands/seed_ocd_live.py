from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from ocd_live.models import OpportunityCategory, Opportunity, LiveSession, OCDPackage, Slot


class Command(BaseCommand):
    help = "Initialise les données de démarrage pour OCD LIVE (Opportunités, Sessions, Pass)"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation des données OCD LIVE...")

        # 1. Catégories d'opportunités
        categories_data = [
            ("Agrobusiness & Élevage", "agrobusiness", "🌿", 1),
            ("Immobilier & Foncier", "immobilier", "🏢", 2),
            ("Commerce & Import-Export", "import-export", "📦", 3),
            ("Transport & Logistique", "transport-logistique", "🚚", 4),
            ("Énergie Solaire & Eau", "energie-eau", "⚡", 5),
            ("Tech & IA Locale", "tech-ia", "🤖", 6),
        ]
        cat_map = {}
        for name, slug, icon, order in categories_data:
            cat, _ = OpportunityCategory.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "icon": icon, "order": order},
            )
            cat_map[slug] = cat
        self.stdout.write(f"✓ {len(cat_map)} catégories configurées.")

        # 2. Opportunités de terrain
        opps_data = [
            {
                "title": "Ferme Moderne d'Élevage Porcin & Volaille à Bafia",
                "slug": "ferme-elevage-bafia-rentable",
                "category": cat_map["agrobusiness"],
                "country": "Cameroun",
                "city": "Bafia / Centre",
                "summary": "Projet d'extension d'une ferme de 2 hectares avec chaîne d'approvisionnement directe pour les marchés de Yaoundé. Cycle court et forte demande.",
                "full_description": "Ce projet d'élevage porcin semi-intensif et poulets de chair dispose déjà du foncier titré, de forages en eau et d'un bâtiment opérationnel de 500m².\n\nBesoin d'investissement : extension des cheptels et automatisation de l'alimentation.\nRentabilité observée : rotation tous les 45 jours pour la volaille, 6 mois pour les porcs.\nContrat de débouchés sécurisé avec 8 restaurants partenaires à Yaoundé et Douala.",
                "min_capital_xaf": Decimal("1500000.00"),
                "estimated_roi": "35% - 45% / an",
                "timeframe": "6 à 12 mois",
                "risk_level": Opportunity.RiskLevel.MODERATE,
                "status": Opportunity.Status.VERIFIED,
                "is_featured": True,
            },
            {
                "title": "Lotissement Sécurisé & Terrains Titrés en Bordure de Route à Kribi",
                "slug": "terrains-titres-kribi-zone-portuaire",
                "category": cat_map["immobilier"],
                "country": "Cameroun",
                "city": "Kribi / Sud",
                "summary": "Parcelles de 500m² à 1 000m² avec titre foncier direct en zone d'expansion portuaire et touristique. Plus-value garantie à court terme.",
                "full_description": "Dans le sillage du Port Autonome de Kribi et des complexes hôteliers, ce lotissement dispose d'un titre foncier mère en règle, certificat de propriété vérifié par nos juristes.\n\nPrix d'acquisition négocié en gros pour les membres OCD Live. Possibilité de revente par tranches ou de construction de bungalows locatifs.",
                "min_capital_xaf": Decimal("3000000.00"),
                "estimated_roi": "40% à 60% sur 2 ans",
                "timeframe": "12 à 24 mois",
                "risk_level": Opportunity.RiskLevel.LOW,
                "status": Opportunity.Status.VERIFIED,
                "is_featured": True,
            },
            {
                "title": "Conteneur Groupé Produits Cosmétiques & Électronique depuis la Chine",
                "slug": "conteneur-groupe-chine-douala-negoce",
                "category": cat_map["import-export"],
                "country": "Cameroun",
                "city": "Douala",
                "summary": "Co-financement d'un conteneur de marchandises à rotation rapide pour le marché de Douala/Bafoussam. Dédouanement et distribution pris en charge.",
                "full_description": "Groupement d'achats piloté par des transitaires expérimentés. Les produits ont été présélectionnés sur la base des tendances de vente du trimestre à Douala (Akwa, Marché Central).\n\nLe capital est garanti par le stock physique entreposé dans notre dépôt sécurisé à Akwa avant distribution aux grossistes.",
                "min_capital_xaf": Decimal("1000000.00"),
                "estimated_roi": "25% net par rotation (90 jours)",
                "timeframe": "3 mois renouvelable",
                "risk_level": Opportunity.RiskLevel.MODERATE,
                "status": Opportunity.Status.IN_PROGRESS,
                "is_featured": True,
            },
            {
                "title": "Flotte de Tricycles & Livraison Urbaine Dernier Kilomètre",
                "slug": "flotte-tricycles-livraison-douala",
                "category": cat_map["transport-logistique"],
                "country": "Cameroun",
                "city": "Douala / Yaoundé",
                "summary": "Acquisition de 5 tricycles utilitaires neufs loués en leasing journalier à des livreurs affiliés avec suivi GPS et assurance tous risques.",
                "full_description": "Face à la saturation du trafic urbain, le transport de marchandises légères par tricycles génère un revenu quotidien net régulier.\n\nModèle : Versement fixe journalier de 7 000 FCFA par véhicule, maintenance gérée par l'opérateur technique référent OCD Live. Retour sur investissement en moins de 10 mois.",
                "min_capital_xaf": Decimal("2200000.00"),
                "estimated_roi": "30% annuel net",
                "timeframe": "10 à 18 mois",
                "risk_level": Opportunity.RiskLevel.LOW,
                "status": Opportunity.Status.VERIFIED,
                "is_featured": False,
            },
        ]

        for o in opps_data:
            Opportunity.objects.get_or_create(slug=o["slug"], defaults=o)
        self.stdout.write(f"✓ {len(opps_data)} opportunités de terrain injectées.")

        # 3. Sessions Live & Masterclasses
        now = timezone.now()
        lives_data = [
            {
                "title": "Masterclass Terrain : Comment Lancer un Élevage Rentable au Cameroun avec 1 Million de FCFA",
                "slug": "masterclass-elevage-1m-fcfa-cameroun",
                "subtitle": "Budget détaillé, erreurs coûteuses à éviter et réseau de vente immédiat.",
                "description": "Durant cette masterclass immersive de 90 minutes en direct, notre expert de terrain vous ouvre les comptes réels d'une exploitation agricole rentabilisée.\n\nAu programme :\n1. Choix de la race et constitution de l'enclos à coût maîtrisé\n2. Optimisation de l'aliment pour diviser vos charges par deux\n3. Les contrats de distribution avec les restaurants et grossistes\n4. Session de Questions & Réponses directes avec les participants.",
                "speaker_name": "Jean-Paul Kemgne",
                "speaker_title": "Agri-entrepreneur & Consultant Fermes Durables",
                "scheduled_at": now + timedelta(days=2, hours=4),
                "duration_minutes": 90,
                "stream_provider": LiveSession.StreamProvider.YOUTUBE,
                "access_tier": LiveSession.AccessTier.PASS_REQUIRED,
                "ticket_price_xaf": Decimal("2500.00"),
                "is_live_now": False,
            },
            {
                "title": "Immobilier en Afrique : Repérer les Terrains à Forte Plus-Value Avant Tout le Monde",
                "slug": "immobilier-afrique-terrains-forte-plus-value",
                "subtitle": "Les zones d'extension urbaine à Douala, Kribi et Yaoundé décortiquées.",
                "description": "Le foncier reste l'un des investissements les plus sûrs en Afrique, à condition de savoir vérifier les titres et d'anticiper les voies de communication.\n\nUne analyse cartographique et juridique complète des opportunités actuelles.",
                "speaker_name": "Maître Stéphane Nguemo",
                "speaker_title": "Juriste Foncier & Développeur Immobilier",
                "scheduled_at": now + timedelta(days=6, hours=2),
                "duration_minutes": 100,
                "stream_provider": LiveSession.StreamProvider.YOUTUBE,
                "access_tier": LiveSession.AccessTier.PASS_REQUIRED,
                "ticket_price_xaf": Decimal("5000.00"),
                "is_live_now": False,
            },
        ]

        for s in lives_data:
            session, _ = LiveSession.objects.get_or_create(slug=s["slug"], defaults=s)
            
            # Créneaux 1-to-1 associés
            Slot.objects.get_or_create(
                session=session,
                title=f"Consultation Privée avec {session.speaker_name}",
                defaults={
                    "expert_name": session.speaker_name,
                    "start_time": session.scheduled_at + timedelta(days=1),
                    "end_time": session.scheduled_at + timedelta(days=1, minutes=45),
                    "capacity": 1,
                    "price_xaf": Decimal("15000.00"),
                },
            )
        self.stdout.write(f"✓ {len(lives_data)} sessions live configurées.")

        # 4. Formules & Pass d'Accès OCD Live
        packages_data = [
            {
                "name": "Pass Ticket 1 Live",
                "slug": "pass-ticket-unitaire",
                "code": "ocd_ticket",
                "price_xaf": Decimal("2500.00"),
                "duration_days": 15,
                "can_access_all_lives": False,
                "private_coaching_credits": 0,
                "full_opportunities_dossier": False,
                "description": "Accès direct à 1 session Live de votre choix\nAccès au Replay officiel pendant 15 jours\nRappel et lien de diffusion direct sur WhatsApp\nQuestions posées en direct à l'intervenant",
                "is_popular": False,
                "order": 1,
            },
            {
                "name": "Pass Membre Mensuel",
                "slug": "pass-membre-mensuel",
                "code": "ocd_monthly",
                "price_xaf": Decimal("15000.00"),
                "duration_days": 30,
                "can_access_all_lives": True,
                "private_coaching_credits": 0,
                "full_opportunities_dossier": True,
                "description": "Accès illimité à tous les Lives du mois\nBibliothèque complète des Replays illimitée\nTous les dossiers d'audit des opportunités\nGroupe privé WhatsApp des investisseurs terrain\nAlertes prioritaires avant publication publique",
                "is_popular": True,
                "order": 2,
            },
            {
                "name": "Pass VIP Investisseur & Business",
                "slug": "pass-vip-investisseur",
                "code": "ocd_vip",
                "price_xaf": Decimal("50000.00"),
                "duration_days": 90,
                "can_access_all_lives": True,
                "private_coaching_credits": 2,
                "full_opportunities_dossier": True,
                "description": "Tous les avantages du Pass Membre pendant 3 mois\n2 consultations privées 1-to-1 avec nos experts\nMise en relation directe avec les porteurs de projets\nAudit juridique et foncier personnalisé\nAccompagnement terrain sur site lors des visites",
                "is_popular": False,
                "order": 3,
            },
        ]

        for p in packages_data:
            OCDPackage.objects.get_or_create(code=p["code"], defaults=p)
        self.stdout.write(f"✓ {len(packages_data)} pass et formules OCD Live créés.")

        self.stdout.write(self.style.SUCCESS("🎉 Seeding OCD LIVE terminé avec succès !"))

