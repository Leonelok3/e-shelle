"""
python manage.py seed_canada_programs

Peuple la table ImmigrationProgram avec les 6 programmes Canada RP.
Idempotent : ne crée pas de doublons si le slug existe déjà.
"""
from django.core.management.base import BaseCommand
from permanent_residence.models import ImmigrationProgram
from permanent_residence.programs_config import CANADA_PROGRAM_DETAILS


PROGRAMS_DATA = [
    {
        "slug": "entree-express-fsw",
        "name": "Travailleurs qualifiés fédéraux (FSW)",
        "country": "CA",
        "category": "Entrée Express",
        "short_label": "Entrée Express – FSW",
        "summary": "La voie principale pour les travailleurs qualifiés sans expérience canadienne. Score CRS ~490–540. CLB 7 minimum. 1 an d'expérience TEER 0/1/2/3 requis.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/travailleurs-qualifies-federaux.html",
    },
    {
        "slug": "entree-express-cec",
        "name": "Expérience canadienne (CEC)",
        "country": "CA",
        "category": "Entrée Express",
        "short_label": "Entrée Express – CEC",
        "summary": "Pour les travailleurs temporaires et diplômés étrangers ayant déjà de l'expérience au Canada. Score CRS plus bas (~450–490). Traitement 4–8 mois.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/experience-canadienne.html",
    },
    {
        "slug": "entree-express-fst",
        "name": "Travailleurs de métiers spécialisés (FST)",
        "country": "CA",
        "category": "Entrée Express",
        "short_label": "Entrée Express – FST",
        "summary": "Pour les travailleurs dans les métiers spécialisés (construction, électricité, soudure…). CLB 5 minimum. Offre d'emploi ou certificat provincial requis.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/travailleurs-metiers-specialises.html",
    },
    {
        "slug": "pnp-general",
        "name": "Programmes des candidats des provinces (PNP)",
        "country": "CA",
        "category": "PNP",
        "short_label": "PNP – Nomination provinciale",
        "summary": "Chaque province sélectionne ses immigrants selon ses besoins. Nomination = +600 pts CRS. Délai 12–18 mois. 9 provinces + 2 territoires actifs.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/programmes-candidats-provinces.html",
    },
    {
        "slug": "quebec-pnp",
        "name": "Immigration au Québec (Arrima / PEQ)",
        "country": "CA",
        "category": "PNP – Québec",
        "short_label": "Québec – Arrima / PEQ",
        "summary": "Le Québec gère sa propre sélection. Français obligatoire. PEQ (~5 mois) si déjà au Québec. PRTQ via Arrima pour candidats à l'étranger (24–36 mois).",
        "official_url": "https://www.quebec.ca/immigration/travailleurs-qualifies",
    },
    {
        "slug": "francophones-hors-quebec",
        "name": "Tirages ciblés francophones (Entrée Express)",
        "country": "CA",
        "category": "Francophone",
        "short_label": "Francophones hors Québec",
        "summary": "Tirages spéciaux pour francophones hors Québec avec seuil CRS réduit (~360–430). Voie la plus accessible pour les Africains francophones. CLB 7 en français requis.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles/avis/2023/entree-express-invitations-nouvelles-categories.html",
    },
    {
        "slug": "regroupement-familial",
        "name": "Regroupement familial",
        "country": "CA",
        "category": "Famille",
        "short_label": "Parrainage familial",
        "summary": "Citoyens canadiens et résidents permanents peuvent parrainer conjoint, enfants, parents. Engagement financier du parrain. Délai 12–48 mois selon la relation.",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/famille/parrainer-membre-famille.html",
    },
]


class Command(BaseCommand):
    help = "Peuple les programmes de Résidence Permanente Canada dans la BDD"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in PROGRAMS_DATA:
            obj, is_new = ImmigrationProgram.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "country": data["country"],
                    "category": data["category"],
                    "short_label": data["short_label"],
                    "summary": data["summary"],
                    "official_url": data["official_url"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Créé : {obj.name}"))
            else:
                updated += 1
                self.stdout.write(f"  ~ Mis à jour : {obj.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {created} programme(s) créé(s), {updated} mis à jour."
        ))
