from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from artisans.models import MetierArtisan, ProfilArtisan, RealisationArtisan, VilleArtisan


PHONE = "+237 680 625 082"


def svg_image(title, subtitle, accent="#16a34a"):
    safe_title = title.replace("&", "&amp;")
    safe_subtitle = subtitle.replace("&", "&amp;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="0 0 1200 820">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{accent}"/><stop offset=".6" stop-color="#052e1b"/><stop offset="1" stop-color="#f97316"/></linearGradient></defs>
  <rect width="1200" height="820" fill="url(#bg)"/><circle cx="980" cy="120" r="220" fill="#fff" opacity=".08"/><circle cx="160" cy="710" r="260" fill="#fff" opacity=".08"/>
  <rect x="170" y="180" width="860" height="450" rx="42" fill="#fff" opacity=".84"/>
  <path d="M330 515 L515 330 L620 435 L710 345 L895 515" fill="none" stroke="#052e1b" stroke-width="44" stroke-linecap="round" stroke-linejoin="round" opacity=".45"/>
  <rect x="250" y="240" width="285" height="52" rx="26" fill="{accent}"/><text x="285" y="274" fill="#fff" font-family="Arial" font-size="26" font-weight="800">E-Shelle Artisans</text>
  <text x="600" y="700" text-anchor="middle" fill="#fff" font-family="Arial" font-size="58" font-weight="900">{safe_title}</text>
  <text x="600" y="752" text-anchor="middle" fill="#f8fafc" font-family="Arial" font-size="30" font-weight="700">{safe_subtitle}</text>
</svg>"""


class Command(BaseCommand):
    help = "Ajoute des artisans demo pour le module travaux E-Shelle."

    def handle(self, *args, **options):
        User = get_user_model()
        villes = {}
        for nom, region in [("Douala", "Littoral"), ("Yaoundé", "Centre"), ("Bafoussam", "Ouest")]:
            villes[nom], _ = VilleArtisan.objects.get_or_create(slug=slugify(nom), defaults={"nom": nom, "region": region, "active": True})

        metiers_data = [
            ("Plombier", "Réparation fuites, installation sanitaires, dépannage urgence"),
            ("Électricien", "Installation, dépannage, tableaux électriques et câblage"),
            ("Maçon", "Construction, rénovation, fondations et murs"),
            ("Carreleur", "Pose carreaux, faïence, salles de bain et terrasses"),
            ("Peintre", "Peinture bâtiment, enduit, finitions intérieures"),
            ("Menuisier", "Portes, meubles, placards, travaux bois"),
            ("Manœuvre", "Main-d'œuvre chantier et assistance travaux"),
        ]
        metiers = {}
        for idx, (nom, desc) in enumerate(metiers_data):
            metiers[nom], _ = MetierArtisan.objects.get_or_create(
                slug=slugify(nom),
                defaults={"nom": nom, "description": desc, "icone": "tools", "ordre": idx, "active": True},
            )

        data = [
            ("Douala Plomberie Express", "demo_artisan_plombier", "Douala", "Bonamoussadi", ["Plombier"], "#0ea5e9", True),
            ("Kotto Electricité Pro", "demo_artisan_electricien", "Douala", "Kotto", ["Électricien"], "#facc15", True),
            ("Bastos Maçonnerie Service", "demo_artisan_macon", "Yaoundé", "Bastos", ["Maçon", "Manœuvre"], "#f97316", False),
            ("Makepe Carrelage Premium", "demo_artisan_carrelage", "Douala", "Makepe", ["Carreleur"], "#16a34a", False),
            ("Bafoussam Peinture Plus", "demo_artisan_peintre", "Bafoussam", "Tamdja", ["Peintre"], "#8b5cf6", False),
            ("Menuiserie Moderne Akwa", "demo_artisan_menuisier", "Douala", "Akwa", ["Menuisier"], "#92400e", False),
        ]

        for index, (name, username, city, district, jobs, accent, emergency) in enumerate(data):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@e-shelle.local", "first_name": name.split()[0], "last_name": "Artisan", "is_active": True},
            )
            user.set_password("Demo@12345")
            user.save()
            artisan, created = ProfilArtisan.objects.update_or_create(
                user=user,
                defaults={
                    "nom_public": name,
                    "ville": villes[city],
                    "quartier": district,
                    "zone_intervention": f"{district}, centre-ville et quartiers proches",
                    "description": f"{name} intervient rapidement pour les besoins de travaux, dépannage, entretien et rénovation. Profil demo E-Shelle Artisans.",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "compte_type": ProfilArtisan.TypeCompte.BUSINESS if index < 3 else ProfilArtisan.TypeCompte.PREMIUM,
                    "date_expiration_premium": date.today() + timedelta(days=60),
                    "est_verifie": True,
                    "disponible_urgence": emergency,
                    "intervention_domicile": True,
                    "note_moyenne": "4.8",
                    "nombre_avis": 18 - index,
                    "vues": 130 - index * 11,
                    "contacts": 20 - index,
                    "is_active": True,
                },
            )
            artisan.metiers.set([metiers[job] for job in jobs])
            if not artisan.photo:
                artisan.photo.save(f"{artisan.slug or slugify(name)}.svg", ContentFile(svg_image(name, f"{district}, {city}", accent).encode("utf-8")), save=True)
            if not artisan.realisations.exists():
                RealisationArtisan.objects.create(
                    artisan=artisan,
                    titre=f"Réalisation {name}",
                    image=ContentFile(svg_image("Travaux réalisés", name, accent).encode("utf-8"), name=f"realisation-{slugify(name)}.svg"),
                    description="Exemple de réalisation visible sur le profil artisan.",
                )
            try:
                from business.services import ensure_business_for_object
                profile = ensure_business_for_object(artisan, "services", {"owner": user, "city": city, "district": district})
                profile.activate_plan("business", 30)
                profile.activate_boost(7 if index < 2 else 3)
                profile.save()
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS(f"{artisan.nom_public} {'cree' if created else 'mis a jour'}"))

        self.stdout.write(self.style.SUCCESS("6 artisans demo prets."))
        self.stdout.write(self.style.SUCCESS("/artisans/"))
