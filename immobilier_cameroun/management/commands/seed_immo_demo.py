from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from immobilier_cameroun.models import (
    Bien,
    EquipementBien,
    NomEquipement,
    PeriodePrix,
    PhotoBien,
    ProfilImmo,
    RoleImmo,
    StatutBien,
    TypeBien,
    TypeCompte,
    TypeTransaction,
)


PHONE = "+237 680 625 082"


def svg_image(title, subtitle, accent="#10b981", dark="#0f172a"):
    safe_title = title.replace("&", "&amp;")
    safe_subtitle = subtitle.replace("&", "&amp;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="0 0 1200 820">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}"/>
      <stop offset="0.52" stop-color="#1e293b"/>
      <stop offset="1" stop-color="{dark}"/>
    </linearGradient>
    <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity=".88"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity=".18"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="820" fill="url(#bg)"/>
  <circle cx="970" cy="120" r="210" fill="#ffffff" opacity=".08"/>
  <circle cx="160" cy="720" r="260" fill="#ffffff" opacity=".08"/>
  <rect x="120" y="170" width="960" height="520" rx="36" fill="url(#glass)" opacity=".92"/>
  <rect x="190" y="300" width="820" height="290" rx="28" fill="#0f172a" opacity=".18"/>
  <path d="M260 570 L430 410 L560 520 L690 365 L940 570 Z" fill="#ffffff" opacity=".55"/>
  <rect x="260" y="240" width="250" height="42" rx="21" fill="{accent}"/>
  <text x="292" y="268" fill="#ffffff" font-family="Arial, sans-serif" font-size="22" font-weight="800">E-Shelle Immo</text>
  <text x="600" y="650" text-anchor="middle" fill="#ffffff" font-family="Arial, sans-serif" font-size="58" font-weight="900">{safe_title}</text>
  <text x="600" y="707" text-anchor="middle" fill="#e2e8f0" font-family="Arial, sans-serif" font-size="30" font-weight="700">{safe_subtitle}</text>
</svg>"""


class Command(BaseCommand):
    help = "Ajoute des agents immobiliers demo avec leurs vitrines publiques et biens tests."

    def handle(self, *args, **options):
        User = get_user_model()
        agent, _ = User.objects.get_or_create(
            username="demo_immo_premium",
            defaults={
                "email": "demo_immo_premium@e-shelle.local",
                "first_name": "E-Shelle",
                "last_name": "Immo Premium",
                "is_active": True,
            },
        )
        agent.set_password("Demo@12345")
        agent.save()

        profil, _ = ProfilImmo.objects.get_or_create(user=agent)
        profil.role = RoleImmo.AGENT
        profil.compte_type = TypeCompte.PREMIUM
        profil.telephone = PHONE
        profil.whatsapp = PHONE
        profil.ville = "Douala"
        profil.quartier = "Bonamoussadi"
        profil.bio = (
            "Agence immobiliere specialisee dans les appartements, villas et terrains "
            "a Douala. Toutes les offres actives sont regroupees sur cette vitrine partageable."
        )
        profil.date_expiration_premium = date.today() + timedelta(days=60)
        profil.est_verifie = True
        if not profil.photo_profil:
            profil.photo_profil.save(
                "demo-agent-immo.svg",
                ContentFile(svg_image("Agent Immo", "Vitrine premium", "#f59e0b").encode("utf-8")),
                save=False,
            )
        profil.save()

        biens = [
            {
                "titre": "Appartement meuble moderne a Bonamoussadi",
                "type_bien": TypeBien.APPARTEMENT_MEUBLE,
                "type_transaction": TypeTransaction.LOCATION,
                "prix": Decimal("350000"),
                "periode": PeriodePrix.PAR_MOIS,
                "ville": "Douala",
                "quartier": "Bonamoussadi",
                "surface": 92,
                "pieces": 4,
                "chambres": 3,
                "bains": 2,
                "accent": "#10b981",
                "equipements": [NomEquipement.WIFI, NomEquipement.CLIMATISATION, NomEquipement.PARKING, NomEquipement.GARDIEN],
            },
            {
                "titre": "Villa familiale avec jardin a Kotto",
                "type_bien": TypeBien.VILLA,
                "type_transaction": TypeTransaction.LOCATION,
                "prix": Decimal("750000"),
                "periode": PeriodePrix.PAR_MOIS,
                "ville": "Douala",
                "quartier": "Kotto",
                "surface": 240,
                "pieces": 6,
                "chambres": 4,
                "bains": 3,
                "accent": "#2563eb",
                "equipements": [NomEquipement.PARKING, NomEquipement.JARDIN if hasattr(NomEquipement, "JARDIN") else NomEquipement.TERRASSE, NomEquipement.GARDIEN, NomEquipement.CITERNE_EAU],
            },
            {
                "titre": "Terrain titre foncier a vendre a PK13",
                "type_bien": TypeBien.TERRAIN,
                "type_transaction": TypeTransaction.VENTE,
                "prix": Decimal("18000000"),
                "periode": PeriodePrix.PRIX_FIXE,
                "ville": "Douala",
                "quartier": "PK13",
                "surface": 500,
                "pieces": 1,
                "chambres": 0,
                "bains": 0,
                "accent": "#84cc16",
                "equipements": [NomEquipement.EAU_COURANTE],
            },
            {
                "titre": "Studio haut standing a Bastos",
                "type_bien": TypeBien.STUDIO,
                "type_transaction": TypeTransaction.LOCATION,
                "prix": Decimal("280000"),
                "periode": PeriodePrix.PAR_MOIS,
                "ville": "Yaoundé",
                "quartier": "Bastos",
                "surface": 48,
                "pieces": 2,
                "chambres": 1,
                "bains": 1,
                "accent": "#8b5cf6",
                "equipements": [NomEquipement.WIFI, NomEquipement.CLIMATISATION, NomEquipement.MEUBLE_COMPLET],
            },
            {
                "titre": "Bureau vitrine a Akwa centre",
                "type_bien": TypeBien.BUREAU,
                "type_transaction": TypeTransaction.LOCATION,
                "prix": Decimal("500000"),
                "periode": PeriodePrix.PAR_MOIS,
                "ville": "Douala",
                "quartier": "Akwa",
                "surface": 110,
                "pieces": 3,
                "chambres": 0,
                "bains": 1,
                "accent": "#f97316",
                "equipements": [NomEquipement.PARKING, NomEquipement.GARDIEN, NomEquipement.GROUPE_ELECTROGENE],
            },
        ]

        created_count = 0
        for index, item in enumerate(biens):
            slug = slugify(item["titre"])
            bien, created = Bien.objects.update_or_create(
                slug=slug,
                defaults={
                    "titre": item["titre"],
                    "type_bien": item["type_bien"],
                    "type_transaction": item["type_transaction"],
                    "description": (
                        f"{item['titre']} disponible via E-Shelle Immo. "
                        "Bien de demonstration avec photos, contact WhatsApp, demande de visite "
                        "et rattachement a une vitrine agent partageable."
                    ),
                    "prix": item["prix"],
                    "periode_prix": item["periode"],
                    "surface": item["surface"],
                    "nombre_pieces": item["pieces"],
                    "nombre_chambres": item["chambres"],
                    "nombre_salles_bain": item["bains"],
                    "ville": item["ville"],
                    "quartier": item["quartier"],
                    "adresse_complete": f"{item['quartier']}, {item['ville']}",
                    "statut": StatutBien.PUBLIE,
                    "est_mis_en_avant": index < 3,
                    "est_coup_de_coeur": index in (0, 1),
                    "date_disponibilite": date.today(),
                    "proprietaire": agent,
                    "publie_par_admin": True,
                    "date_publication": timezone.now(),
                    "vues": 140 - index * 17,
                    "meta_description": f"{item['titre']} - {item['quartier']}, {item['ville']} sur E-Shelle Immo.",
                },
            )
            bien.equipements.all().delete()
            for equipment in item["equipements"]:
                EquipementBien.objects.get_or_create(bien=bien, nom=equipment)

            if not bien.photos.exists():
                PhotoBien.objects.create(
                    bien=bien,
                    image=ContentFile(
                        svg_image(item["titre"], f"{item['quartier']}, {item['ville']}", item["accent"]).encode("utf-8"),
                        name=f"{slug}-photo.svg",
                    ),
                    legende=item["titre"],
                    est_photo_principale=True,
                    ordre=0,
                )

            try:
                from business.services import ensure_business_for_object

                profile = ensure_business_for_object(
                    bien,
                    "immobilier",
                    {"owner": agent, "city": item["ville"], "district": item["quartier"]},
                )
                profile.activate_plan("business", 30)
                profile.activate_boost(7 if index < 2 else 3)
                profile.save()
            except Exception:
                pass

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"{bien.titre} {'cree' if created else 'mis a jour'}"))

        self.stdout.write(self.style.SUCCESS(f"{created_count} biens demo prets."))
        self.stdout.write(self.style.SUCCESS("/immobilier/agent/demo_immo_premium/"))
