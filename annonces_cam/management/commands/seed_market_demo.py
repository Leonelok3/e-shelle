from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from annonces_cam.models import (
    Annonce,
    Categorie,
    DeviseAnnonce,
    EtatProduit,
    ModeContact,
    PhotoAnnonce,
    ProfilVendeur,
    StatutAnnonce,
    TypeCompteVendeur,
)


PHONE = "+237 680 625 082"


def svg_image(title, subtitle, accent="#f97316", dark="#14532d"):
    safe_title = title.replace("&", "&amp;")
    safe_subtitle = subtitle.replace("&", "&amp;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="0 0 1200 820">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{dark}"/>
      <stop offset=".52" stop-color="#365314"/>
      <stop offset="1" stop-color="{accent}"/>
    </linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity=".92"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity=".22"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="820" fill="url(#bg)"/>
  <circle cx="1000" cy="120" r="220" fill="#fff" opacity=".08"/>
  <circle cx="120" cy="720" r="260" fill="#fff" opacity=".08"/>
  <rect x="150" y="140" width="900" height="540" rx="42" fill="url(#card)"/>
  <rect x="235" y="235" width="265" height="265" rx="28" fill="#0f172a" opacity=".16"/>
  <rect x="540" y="235" width="425" height="54" rx="27" fill="#0f172a" opacity=".16"/>
  <rect x="540" y="325" width="360" height="34" rx="17" fill="#0f172a" opacity=".12"/>
  <rect x="540" y="390" width="290" height="34" rx="17" fill="#0f172a" opacity=".12"/>
  <rect x="540" y="500" width="190" height="58" rx="29" fill="{accent}"/>
  <text x="275" y="385" fill="#fff" font-family="Arial, sans-serif" font-size="96" font-weight="900">E</text>
  <text x="600" y="710" text-anchor="middle" fill="#ffffff" font-family="Arial, sans-serif" font-size="56" font-weight="900">{safe_title}</text>
  <text x="600" y="762" text-anchor="middle" fill="#f8fafc" font-family="Arial, sans-serif" font-size="29" font-weight="700">{safe_subtitle}</text>
</svg>"""


class Command(BaseCommand):
    help = "Ajoute des annonces demo pour E-Shelle Market sans modifier le style."

    def handle(self, *args, **options):
        User = get_user_model()
        vendeur, _ = User.objects.get_or_create(
            username="demo_market_premium",
            defaults={
                "email": "demo_market_premium@e-shelle.local",
                "first_name": "E-Shelle",
                "last_name": "Market Premium",
                "is_active": True,
            },
        )
        vendeur.set_password("Demo@12345")
        vendeur.save()

        profil, _ = ProfilVendeur.objects.get_or_create(user=vendeur)
        profil.nom_boutique = "E-Shelle Market Premium"
        profil.description_boutique = "Boutique demo avec produits et services disponibles a Douala et Yaounde."
        profil.telephone = PHONE
        profil.whatsapp = PHONE
        profil.ville = "Douala"
        profil.compte_type = TypeCompteVendeur.PREMIUM
        profil.date_expiration_premium = date.today() + timedelta(days=60)
        profil.est_verifie = True
        profil.note_moyenne = Decimal("4.8")
        profil.nombre_avis = 18
        profil.nombre_ventes_reussies = 42
        if not profil.photo_profil:
            profil.photo_profil.save(
                "demo-market-vendeur.svg",
                ContentFile(svg_image("Market Premium", "Boutique verifiee").encode("utf-8")),
                save=False,
            )
        profil.save()

        parents = {
            "electronique": ("Electronique", "fa-mobile-screen", "#2563eb"),
            "maison": ("Maison", "fa-house", "#10b981"),
            "mode": ("Mode", "fa-shirt", "#ec4899"),
            "services": ("Services", "fa-briefcase", "#f97316"),
        }
        categories = {}
        for slug, (name, icon, color) in parents.items():
            parent, _ = Categorie.objects.get_or_create(
                slug=slug,
                defaults={"nom": name, "icone": icon, "couleur_hex": color, "est_active": True, "ordre": len(categories)},
            )
            sub, _ = Categorie.objects.get_or_create(
                slug=f"{slug}-divers",
                defaults={
                    "nom": f"{name} divers",
                    "parent": parent,
                    "icone": icon,
                    "couleur_hex": color,
                    "est_active": True,
                    "ordre": len(categories) + 10,
                },
            )
            categories[slug] = sub

        data = [
            ("iPhone 13 Pro 256 Go", "electronique", "Douala", "Akwa", 285000, EtatProduit.COMME_NEUF, "#2563eb"),
            ("Laptop HP Core i5 8Go RAM", "electronique", "Douala", "Bonamoussadi", 220000, EtatProduit.BON_ETAT, "#0f172a"),
            ("Canape salon 7 places", "maison", "Yaoundé", "Bastos", 180000, EtatProduit.BON_ETAT, "#10b981"),
            ("Robe de soiree premium", "mode", "Douala", "Makepe", 35000, EtatProduit.NEUF, "#ec4899"),
            ("Pack community manager 30 jours", "services", "Douala", "En ligne", 75000, EtatProduit.NON_APPLICABLE, "#f97316"),
            ("Congelateur vitrine occasion", "maison", "Douala", "Bonaberi", 160000, EtatProduit.ETAT_CORRECT, "#84cc16"),
        ]

        for index, (title, cat_slug, city, district, price, condition, accent) in enumerate(data):
            annonce, created = Annonce.objects.update_or_create(
                slug=slugify(f"{title}-{city}"),
                defaults={
                    "titre": title,
                    "categorie": categories[cat_slug],
                    "sous_categorie": categories[cat_slug],
                    "description": (
                        f"{title} disponible sur E-Shelle Market. Produit de demonstration "
                        "avec photo, contact WhatsApp, fiche detaillee et boutique vendeur partageable."
                    ),
                    "prix": Decimal(price),
                    "devise": DeviseAnnonce.XAF,
                    "prix_a_debattre": index in (1, 5),
                    "gratuit": False,
                    "etat_produit": condition,
                    "ville": city,
                    "quartier": district,
                    "adresse_precise": f"{district}, {city}",
                    "vendeur": vendeur,
                    "telephone_contact": PHONE,
                    "whatsapp_contact": PHONE,
                    "mode_contact": ModeContact.TOUS,
                    "statut": StatutAnnonce.PUBLIEE,
                    "est_mise_en_avant": index < 3,
                    "est_urgente": index in (0, 4),
                    "est_coup_de_coeur": index in (0, 2),
                    "publiee_par_admin": True,
                    "date_expiration": date.today() + timedelta(days=45),
                    "date_publication": timezone.now(),
                    "date_derniere_remontee": timezone.now(),
                    "vues": 210 - index * 19,
                    "nombre_contacts": 12 - index,
                    "nombre_favoris": 8 - min(index, 6),
                    "meta_description": f"{title} a {city} sur E-Shelle Market.",
                },
            )

            if not annonce.photos.exists():
                PhotoAnnonce.objects.create(
                    annonce=annonce,
                    image=ContentFile(
                        svg_image(title, f"{city} - {annonce.prix_formate}", accent).encode("utf-8"),
                        name=f"{annonce.slug}.svg",
                    ),
                    legende=title,
                    est_photo_principale=True,
                    ordre=0,
                )

            try:
                from business.services import ensure_business_for_object

                profile = ensure_business_for_object(
                    annonce,
                    "market",
                    {"owner": vendeur, "city": city, "district": district},
                )
                profile.activate_plan("business", 30)
                profile.activate_boost(7 if index < 2 else 3)
                profile.save()
            except Exception:
                pass

            self.stdout.write(self.style.SUCCESS(f"{annonce.titre} {'cree' if created else 'mis a jour'}"))

        self.stdout.write(self.style.SUCCESS("6 annonces market demo pretes."))
        self.stdout.write(self.style.SUCCESS("/annonces/boutique/demo_market_premium/"))
