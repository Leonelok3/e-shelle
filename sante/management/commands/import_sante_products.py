from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from sante.models import CategorieSante, ProduitSante, VilleSante


PHONE = "237680625082"
BASE_DIR = Path(r"c:/Users/USER/Downloads")


PRODUCTS = [
    {
        "title": "Vitalux Advanced AREDS2 - 200 comprimes",
        "image": "WhatsApp Image 2026-05-28 at 4.07.21 AM (1).jpeg",
        "category": "Vitamines et complements",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Complement multivitamine oculaire Vitalux Advanced AREDS2. "
            "Produit a commander apres confirmation de disponibilite aupres du vendeur."
        ),
    },
    {
        "title": "Focus Factor - 150 comprimes",
        "image": "WhatsApp Image 2026-05-28 at 4.07.21 AM.jpeg",
        "category": "Vitamines et complements",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Complement nutritionnel Focus Factor pour le bien-etre quotidien. "
            "Disponibilite, conseils d'utilisation et prix a confirmer avec le vendeur."
        ),
    },
    {
        "title": "Polysporin Complete - pommade 3 antibiotiques",
        "image": "WhatsApp Image 2026-05-28 at 4.07.20 AM (1).jpeg",
        "category": "Premiers soins",
        "type": ProduitSante.TypeProduit.HYGIENE,
        "description": (
            "Pommade Polysporin Complete pour premiers soins. "
            "Demandez confirmation de disponibilite et conseils au vendeur avant achat."
        ),
    },
    {
        "title": "Centrum Women - 250 comprimes",
        "image": "WhatsApp Image 2026-05-28 at 4.07.20 AM.jpeg",
        "category": "Vitamines et complements",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Multivitamines et mineraux Centrum Women. Produit disponible sur commande "
            "avec confirmation du vendeur."
        ),
    },
    {
        "title": "Centrum Men 50+ - 250 comprimes",
        "image": "WhatsApp Image 2026-05-28 at 4.07.19 AM (2).jpeg",
        "category": "Vitamines et complements",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Multivitamines et mineraux Centrum Men 50+. "
            "Prix et disponibilite a confirmer directement avec le vendeur."
        ),
    },
    {
        "title": "Kirkland Signature Women 50+ - 365 comprimes",
        "image": "WhatsApp Image 2026-05-28 at 4.07.19 AM (1).jpeg",
        "category": "Vitamines et complements",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Multivitamines et mineraux Kirkland Signature Women 50+. "
            "Produit a commander apres verification de disponibilite."
        ),
    },
    {
        "title": "Webber Naturals Super Prostate - 180 gelules",
        "image": "WhatsApp Image 2026-05-28 at 4.07.19 AM.jpeg",
        "category": "Sante homme",
        "type": ProduitSante.TypeProduit.COMPLEMENT,
        "description": (
            "Complement Webber Naturals Super Prostate. "
            "Demandez conseil au vendeur ou a un professionnel de sante si necessaire."
        ),
    },
    {
        "title": "Boostherb Penis Enlargement Oil - 10 ml",
        "image": "WhatsApp Image 2026-05-25 at 11.52.39 AM.jpeg",
        "category": "Bien-etre homme",
        "type": ProduitSante.TypeProduit.BIEN_ETRE,
        "description": (
            "Huile bien-etre homme Boostherb. Produit reserve aux adultes. "
            "Disponibilite, prix et conditions d'utilisation a confirmer avec le vendeur."
        ),
    },
]


class Command(BaseCommand):
    help = "Importe les produits sante fournis avec leurs images dans la rubrique E-Shelle Sante."

    def handle(self, *args, **options):
        ville, _ = VilleSante.objects.get_or_create(
            slug="douala",
            defaults={"nom": "Douala", "region": "Littoral", "active": True},
        )

        count = 0
        for index, item in enumerate(PRODUCTS):
            categorie, _ = CategorieSante.objects.get_or_create(
                slug=slugify(item["category"]),
                defaults={
                    "nom": item["category"],
                    "type_categorie": CategorieSante.TypeCategorie.PRODUIT,
                    "icone": "+",
                    "description": "Produits sante disponibles sur E-Shelle.",
                    "ordre": 20 + index,
                    "active": True,
                },
            )
            source = BASE_DIR / item["image"]
            if not source.exists():
                self.stdout.write(self.style.WARNING(f"Image introuvable: {source}"))

            product, created = ProduitSante.objects.update_or_create(
                slug=slugify(f"{item['title']}-douala"),
                defaults={
                    "titre": item["title"],
                    "type_produit": item["type"],
                    "categorie": categorie,
                    "description": item["description"],
                    "ville": ville,
                    "vendeur_nom": "Pharmacie Bonamoussadi Conseil",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "prix": 0,
                    "stock_disponible": 10,
                    "livraison": True,
                    "ordonnance_requise": False,
                    "is_active": True,
                    "is_verified": True,
                    "is_featured": index < 4,
                },
            )

            if source.exists():
                with source.open("rb") as image_file:
                    product.image.save(source.name, File(image_file), save=True)

            count += 1
            status = "cree" if created else "mis a jour"
            self.stdout.write(self.style.SUCCESS(f"{product.titre} {status}"))

        self.stdout.write(self.style.SUCCESS(f"{count} produits sante importes."))
