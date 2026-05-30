from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from agro.models import (
    ActeurAgro,
    CategorieAgro,
    PrixMarche,
    ProduitAgro,
    StockProducteur,
    TypeActeur,
)


User = get_user_model()


PRODUITS = [
    ('Manioc', 'Vivriers', 'sac', 18500, 'Yaoundé', 'Centre'),
    ('Maïs jaune', 'Céréales', 'sac', 23000, 'Bafoussam', 'Ouest'),
    ('Banane plantain', 'Vivriers', 'regime', 4200, 'Douala', 'Littoral'),
    ('Arachide décortiquée', 'Céréales', 'kg', 950, 'Garoua', 'Nord'),
    ('Cacao grade I', 'Rente', 'kg', 2100, 'Bertoua', 'Est'),
    ('Café arabica', 'Rente', 'kg', 2800, 'Bamenda', 'Nord-Ouest'),
    ('Huile de palme rouge', 'Transformés', 'litre', 1200, 'Douala', 'Littoral'),
    ('Poisson fumé', 'Transformés', 'carton', 32000, 'Maroua', 'Extrême-Nord'),
]

PRIX = [
    ('Manioc', 'Yaoundé', 19000, 'sac', 'stable'),
    ('Manioc', 'Douala', 21000, 'sac', 'hausse'),
    ('Maïs', 'Bafoussam', 22500, 'sac', 'stable'),
    ('Maïs', 'Garoua', 20500, 'sac', 'baisse'),
    ('Plantain', 'Douala', 4500, 'regime', 'hausse'),
    ('Plantain', 'Bamenda', 3800, 'regime', 'stable'),
    ('Arachide', 'Garoua', 900, 'kg', 'stable'),
    ('Cacao', 'Bertoua', 2150, 'kg', 'hausse'),
    ('Café', 'Bamenda', 2800, 'kg', 'stable'),
    ('Huile de palme', 'Douala', 1250, 'litre', 'hausse'),
    ('Poisson fumé', 'Maroua', 31000, 'carton', 'stable'),
]


class Command(BaseCommand):
    help = "Crée des données demo pour AgroConnect AI Cameroun."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username='agroconnect_demo',
            defaults={'email': 'agroconnect.demo@e-shelle.com'},
        )
        if created:
            user.set_password('demo2026!')
            user.save()

        acteur, _ = ActeurAgro.objects.get_or_create(
            user=user,
            defaults={
                'type_acteur': TypeActeur.COOPERATIVE,
                'nom_entreprise': 'Coopérative AgroConnect Cameroun',
                'nom_contact': 'Marthe Ngono',
                'poste_contact': 'Responsable commerciale',
                'pays': 'Cameroun',
                'region': 'Centre',
                'ville': 'Yaoundé',
                'telephone': '+237 680 625 082',
                'whatsapp': '+237 680 625 082',
                'email_pro': 'agroconnect.demo@e-shelle.com',
                'description': 'Coopérative de démonstration pour tester le hub IA agro.',
                'est_verifie': True,
                'est_premium': True,
                'plan_premium': 'gold',
                'modes_paiement': ['MTN Mobile Money', 'Orange Money', 'Paiement livraison'],
                'langues_travail': ['Français', 'Anglais'],
                'score_confiance': 88,
            },
        )

        categories = {}
        for nom in ['Vivriers', 'Céréales', 'Rente', 'Transformés']:
            categories[nom], _ = CategorieAgro.objects.get_or_create(
                slug=slugify(nom),
                defaults={'nom': nom, 'icone': '🌿', 'est_active': True},
            )

        for nom, categorie, unite, prix, ville, region in PRODUITS:
            produit, _ = ProduitAgro.objects.get_or_create(
                nom=nom,
                acteur=acteur,
                defaults={
                    'categorie': categories[categorie],
                    'description': f'{nom} camerounais disponible pour ventes locales et commandes groupées.',
                    'origine_geographique': f'{region}, Cameroun',
                    'prix_unitaire': Decimal(prix),
                    'devise': 'XAF',
                    'unite_mesure': 'sac' if unite == 'regime' else unite,
                    'quantite_stock': 120,
                    'quantite_min_commande': 1,
                    'conditionnement': unite,
                    'disponibilite': 'en_stock',
                    'statut': 'publie',
                    'est_mis_en_avant': True,
                    'tags': [nom.lower(), ville.lower(), 'cameroun'],
                },
            )
            StockProducteur.objects.get_or_create(
                utilisateur=user,
                produit=produit,
                defaults={'quantite': 120, 'seuil_alerte': 20},
            )

        today = date.today()
        for produit, ville, prix, unite, tendance in PRIX:
            PrixMarche.objects.update_or_create(
                produit=produit,
                ville=ville,
                date_releve=today,
                defaults={'prix_moyen': Decimal(prix), 'unite': unite, 'tendance': tendance},
            )

        self.stdout.write(self.style.SUCCESS(
            "Demo AgroConnect AI créée: produits, prix de marché et stocks. "
            "Compte: agroconnect_demo / demo2026!"
        ))
