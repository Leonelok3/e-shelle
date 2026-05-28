from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from auto_cameroun.models import (
    DeviseAuto,
    EtatVehicule,
    PeriodePrixAuto,
    PhotoVehicule,
    ProfilAuto,
    RoleVendeur,
    StatutVehicule,
    TypeBoite,
    TypeCarburant,
    TypeCarrosserie,
    TypeCompteAuto,
    TypeTransaction,
    Vehicule,
)


PHONE = "+237 680 625 082"


def svg_image(title, subtitle, accent="#2563eb", dark="#0f172a"):
    safe_title = title.replace("&", "&amp;")
    safe_subtitle = subtitle.replace("&", "&amp;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="0 0 1200 820">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}"/>
      <stop offset="0.55" stop-color="#111827"/>
      <stop offset="1" stop-color="{dark}"/>
    </linearGradient>
    <linearGradient id="car" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity=".92"/>
      <stop offset="1" stop-color="#dbeafe" stop-opacity=".64"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="820" fill="url(#bg)"/>
  <circle cx="1000" cy="125" r="220" fill="#ffffff" opacity=".08"/>
  <circle cx="150" cy="720" r="250" fill="#ffffff" opacity=".08"/>
  <rect x="155" y="445" width="890" height="120" rx="60" fill="url(#car)"/>
  <path d="M320 445 L455 300 H760 L895 445 Z" fill="url(#car)"/>
  <rect x="482" y="330" width="230" height="95" rx="18" fill="#0f172a" opacity=".32"/>
  <rect x="730" y="350" width="120" height="75" rx="16" fill="#0f172a" opacity=".28"/>
  <circle cx="355" cy="575" r="70" fill="#0f172a"/>
  <circle cx="355" cy="575" r="32" fill="#e5e7eb"/>
  <circle cx="842" cy="575" r="70" fill="#0f172a"/>
  <circle cx="842" cy="575" r="32" fill="#e5e7eb"/>
  <rect x="245" y="210" width="270" height="46" rx="23" fill="{accent}"/>
  <text x="280" y="240" fill="#fff" font-family="Arial, sans-serif" font-size="23" font-weight="800">E-Shelle Auto</text>
  <text x="600" y="680" text-anchor="middle" fill="#ffffff" font-family="Arial, sans-serif" font-size="58" font-weight="900">{safe_title}</text>
  <text x="600" y="735" text-anchor="middle" fill="#e2e8f0" font-family="Arial, sans-serif" font-size="30" font-weight="700">{safe_subtitle}</text>
</svg>"""


class Command(BaseCommand):
    help = "Ajoute un vendeur auto demo avec véhicules de vente et location."

    def handle(self, *args, **options):
        User = get_user_model()
        vendeur, _ = User.objects.get_or_create(
            username="demo_auto_premium",
            defaults={
                "email": "demo_auto_premium@e-shelle.local",
                "first_name": "E-Shelle",
                "last_name": "Auto Premium",
                "is_active": True,
            },
        )
        vendeur.set_password("Demo@12345")
        vendeur.save()

        profil, _ = ProfilAuto.objects.get_or_create(user=vendeur)
        profil.role = RoleVendeur.CONCESSIONNAIRE
        profil.compte_type = TypeCompteAuto.PREMIUM
        profil.telephone = PHONE
        profil.ville = "Douala"
        profil.description = (
            "Vendeur auto premium pour voitures en vente et location a Douala et Yaounde. "
            "Cette vitrine regroupe tout le parc partageable aux clients."
        )
        profil.est_verifie = True
        profil.date_expiration_premium = date.today() + timedelta(days=60)
        if not profil.photo_profil:
            profil.photo_profil.save(
                "demo-vendeur-auto.svg",
                ContentFile(svg_image("Vendeur Auto", "Parc premium", "#f97316").encode("utf-8")),
                save=False,
            )
        profil.save()

        vehicules = [
            {
                "marque": "Toyota",
                "modele": "RAV4",
                "annee": 2021,
                "transaction": TypeTransaction.VENTE,
                "carrosserie": TypeCarrosserie.SUV,
                "prix": Decimal("18500000"),
                "periode": PeriodePrixAuto.GLOBAL,
                "ville": "Douala",
                "quartier": "Bonamoussadi",
                "km": 52000,
                "carburant": TypeCarburant.ESSENCE,
                "boite": TypeBoite.AUTOMATIQUE,
                "accent": "#2563eb",
            },
            {
                "marque": "Mercedes-Benz",
                "modele": "C300",
                "annee": 2020,
                "transaction": TypeTransaction.VENTE,
                "carrosserie": TypeCarrosserie.BERLINE,
                "prix": Decimal("24500000"),
                "periode": PeriodePrixAuto.GLOBAL,
                "ville": "Yaoundé",
                "quartier": "Bastos",
                "km": 43000,
                "carburant": TypeCarburant.ESSENCE,
                "boite": TypeBoite.AUTOMATIQUE,
                "accent": "#111827",
            },
            {
                "marque": "Hyundai",
                "modele": "Tucson",
                "annee": 2022,
                "transaction": TypeTransaction.LOCATION,
                "carrosserie": TypeCarrosserie.SUV,
                "prix": Decimal("45000"),
                "periode": PeriodePrixAuto.PAR_JOUR,
                "ville": "Douala",
                "quartier": "Akwa",
                "km": 28000,
                "carburant": TypeCarburant.DIESEL,
                "boite": TypeBoite.AUTOMATIQUE,
                "accent": "#10b981",
            },
            {
                "marque": "Toyota",
                "modele": "Hilux",
                "annee": 2019,
                "transaction": TypeTransaction.LOCATION,
                "carrosserie": TypeCarrosserie.PICKUP,
                "prix": Decimal("60000"),
                "periode": PeriodePrixAuto.PAR_JOUR,
                "ville": "Douala",
                "quartier": "Bonaberi",
                "km": 69000,
                "carburant": TypeCarburant.DIESEL,
                "boite": TypeBoite.MANUELLE,
                "accent": "#f97316",
            },
            {
                "marque": "Honda",
                "modele": "Civic",
                "annee": 2018,
                "transaction": TypeTransaction.VENTE,
                "carrosserie": TypeCarrosserie.BERLINE,
                "prix": Decimal("7800000"),
                "periode": PeriodePrixAuto.GLOBAL,
                "ville": "Douala",
                "quartier": "Makepe",
                "km": 84000,
                "carburant": TypeCarburant.ESSENCE,
                "boite": TypeBoite.AUTOMATIQUE,
                "accent": "#7c3aed",
            },
        ]

        for index, item in enumerate(vehicules):
            titre = f"{item['marque']} {item['modele']} {item['annee']} - {'location' if item['transaction'] == TypeTransaction.LOCATION else 'vente'}"
            slug = slugify(f"{item['marque']}-{item['modele']}-{item['annee']}-{item['ville']}-{item['transaction']}")
            vehicule, created = Vehicule.objects.update_or_create(
                slug=slug,
                defaults={
                    "proprietaire": vendeur,
                    "titre": titre,
                    "type_transaction": item["transaction"],
                    "type_carrosserie": item["carrosserie"],
                    "etat": EtatVehicule.TRES_BON if index != 4 else EtatVehicule.BON,
                    "marque": item["marque"],
                    "modele": item["modele"],
                    "annee": item["annee"],
                    "version": "Demo E-Shelle Premium",
                    "couleur": ["Noir", "Gris", "Blanc", "Orange", "Bleu"][index],
                    "carburant": item["carburant"],
                    "boite": item["boite"],
                    "puissance_cv": 9 + index,
                    "kilometrage": item["km"],
                    "nombre_places": 5,
                    "nombre_portes": 4,
                    "ville": item["ville"],
                    "quartier": item["quartier"],
                    "adresse_complete": f"{item['quartier']}, {item['ville']}",
                    "prix": item["prix"],
                    "devise": DeviseAuto.XAF,
                    "periode_prix": item["periode"],
                    "prix_negociable": True,
                    "description": (
                        f"{item['marque']} {item['modele']} {item['annee']} disponible sur E-Shelle Auto. "
                        "Annonce de demonstration avec galerie, contact WhatsApp, demande d'essai "
                        "et vitrine vendeur partageable."
                    ),
                    "options_equipements": "Climatisation\nCamera de recul\nBluetooth\nAirbags\nJantes aluminium",
                    "statut": StatutVehicule.PUBLIE,
                    "est_mis_en_avant": index < 3,
                    "est_coup_de_coeur": index in (0, 2),
                    "publie_par_admin": True,
                    "est_dedouane": True,
                    "garantie": "Verification garage disponible",
                    "premiere_main": index in (0, 2),
                    "vues": 170 - index * 21,
                    "date_disponibilite": date.today(),
                    "date_publication": timezone.now(),
                    "meta_description": f"{titre} a {item['ville']} sur E-Shelle Auto.",
                },
            )

            if not vehicule.photos.exists():
                PhotoVehicule.objects.create(
                    vehicule=vehicule,
                    image=ContentFile(
                        svg_image(
                            f"{item['marque']} {item['modele']}",
                            f"{item['ville']} - {vehicule.prix_formate}",
                            item["accent"],
                        ).encode("utf-8"),
                        name=f"{slug}.svg",
                    ),
                    legende=titre,
                    est_photo_principale=True,
                    ordre=0,
                )

            try:
                from business.services import ensure_business_for_object

                profile = ensure_business_for_object(
                    vehicule,
                    "auto",
                    {"owner": vendeur, "city": item["ville"], "district": item["quartier"]},
                )
                profile.activate_plan("business", 30)
                profile.activate_boost(7 if index < 2 else 3)
                profile.save()
            except Exception:
                pass

            self.stdout.write(self.style.SUCCESS(f"{vehicule.titre} {'cree' if created else 'mis a jour'}"))

        self.stdout.write(self.style.SUCCESS("5 vehicules auto demo prets."))
        self.stdout.write(self.style.SUCCESS("/auto/vendeur/demo_auto_premium/"))
