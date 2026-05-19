from django.core.management.base import BaseCommand

from sante.models import CategorieSante, ProduitSante, ProfessionnelSante, VilleSante


class Command(BaseCommand):
    help = "Initialise E-Shelle Santé avec villes, catégories, produits et professionnels démo."

    def handle(self, *args, **options):
        villes_data = [
            ("Yaoundé", "Centre"),
            ("Douala", "Littoral"),
            ("Bafoussam", "Ouest"),
            ("Buea", "Sud-Ouest"),
            ("Garoua", "Nord"),
            ("Bertoua", "Est"),
        ]
        villes = {}
        for ordre, (nom, region) in enumerate(villes_data, start=1):
            ville, _ = VilleSante.objects.update_or_create(
                nom=nom,
                defaults={"region": region, "active": True, "ordre": ordre},
            )
            villes[nom] = ville

        cats_data = [
            ("Consultation générale", CategorieSante.TypeCategorie.SERVICE, "CG", "Médecins généralistes et consultations rapides"),
            ("Laboratoire", CategorieSante.TypeCategorie.SERVICE, "LB", "Analyses médicales et prélèvements"),
            ("Nutrition", CategorieSante.TypeCategorie.SPECIALITE, "NT", "Diététique, compléments et suivi nutritionnel"),
            ("Maman & bébé", CategorieSante.TypeCategorie.PRODUIT, "BB", "Soins, hygiène et maternité"),
            ("Matériel médical", CategorieSante.TypeCategorie.PRODUIT, "MM", "Tensiomètres, thermomètres et consommables"),
            ("Bien-être naturel", CategorieSante.TypeCategorie.PRODUIT, "BN", "Produits de bien-être et hygiène quotidienne"),
            ("Kinésithérapie", CategorieSante.TypeCategorie.SPECIALITE, "KN", "Rééducation, mobilité et douleurs"),
        ]
        cats = {}
        for ordre, (nom, typ, icone, desc) in enumerate(cats_data, start=1):
            cat, _ = CategorieSante.objects.update_or_create(
                nom=nom,
                defaults={
                    "type_categorie": typ,
                    "icone": icone,
                    "description": desc,
                    "active": True,
                    "ordre": ordre,
                },
            )
            cats[nom] = cat

        pros = [
            {
                "nom": "Clinique Santé Verte Bastos",
                "type_pro": ProfessionnelSante.TypePro.CLINIQUE,
                "ville": villes["Yaoundé"],
                "quartier": "Bastos",
                "adresse": "Avenue principale Bastos",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "horaires": "Lun-Dim 7h-22h",
                "description": "Centre de soins généralistes avec consultation, petite urgence et suivi familial.",
                "urgence": True,
                "teleconsultation": True,
                "specialites": ["Consultation générale", "Nutrition"],
                "is_featured": True,
            },
            {
                "nom": "Labo Express Akwa",
                "type_pro": ProfessionnelSante.TypePro.LABO,
                "ville": villes["Douala"],
                "quartier": "Akwa",
                "adresse": "Boulevard de la République",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "horaires": "Lun-Sam 6h30-18h",
                "description": "Analyses courantes, bilans de santé, prélèvements à domicile sur rendez-vous.",
                "consultation_domicile": True,
                "specialites": ["Laboratoire"],
                "is_featured": True,
            },
            {
                "nom": "Cabinet Kiné Mobilité",
                "type_pro": ProfessionnelSante.TypePro.KINE,
                "ville": villes["Bafoussam"],
                "quartier": "Kamkop",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "description": "Rééducation, récupération sportive et accompagnement post-traumatique.",
                "consultation_domicile": True,
                "specialites": ["Kinésithérapie"],
                "is_featured": False,
            },
        ]
        for data in pros:
            specialites = data.pop("specialites")
            pro, _ = ProfessionnelSante.objects.update_or_create(
                nom=data["nom"],
                ville=data["ville"],
                defaults={**data, "is_active": True, "is_verified": True},
            )
            pro.specialites.set([cats[name] for name in specialites if name in cats])

        produits = [
            {
                "titre": "Tensiomètre digital bras",
                "type_produit": ProduitSante.TypeProduit.MATERIEL,
                "categorie": cats["Matériel médical"],
                "ville": villes["Douala"],
                "vendeur_nom": "Santé Market Akwa",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "prix": 18500,
                "prix_barre": 22500,
                "stock_disponible": 8,
                "livraison": True,
                "description": "Tensiomètre électronique fiable pour suivi de tension à domicile.",
                "is_featured": True,
            },
            {
                "titre": "Thermomètre infrarouge sans contact",
                "type_produit": ProduitSante.TypeProduit.MATERIEL,
                "categorie": cats["Matériel médical"],
                "ville": villes["Yaoundé"],
                "vendeur_nom": "Clinique Santé Verte",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "prix": 9500,
                "stock_disponible": 15,
                "livraison": True,
                "description": "Thermomètre rapide pour famille, clinique, école et entreprise.",
                "is_featured": True,
            },
            {
                "titre": "Pack hygiène bébé premium",
                "type_produit": ProduitSante.TypeProduit.BEBE,
                "categorie": cats["Maman & bébé"],
                "ville": villes["Yaoundé"],
                "vendeur_nom": "Maman Plus",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "prix": 12500,
                "stock_disponible": 10,
                "livraison": True,
                "description": "Kit hygiène bébé avec produits doux pour usage quotidien.",
                "is_featured": True,
            },
            {
                "titre": "Complément vitamine C + zinc",
                "type_produit": ProduitSante.TypeProduit.COMPLEMENT,
                "categorie": cats["Nutrition"],
                "ville": villes["Buea"],
                "vendeur_nom": "Wellness Buea",
                "telephone": "+237680625082",
                "whatsapp": "237680625082",
                "prix": 4500,
                "stock_disponible": 30,
                "livraison": False,
                "description": "Complément alimentaire pour soutien nutritionnel. Demandez conseil à un professionnel si besoin.",
                "is_featured": False,
            },
        ]
        created = 0
        for data in produits:
            _, was_created = ProduitSante.objects.update_or_create(
                titre=data["titre"],
                ville=data["ville"],
                defaults={**data, "is_active": True, "is_verified": True},
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"E-Shelle Santé prêt: {created} nouveau(x) produit(s)."))
