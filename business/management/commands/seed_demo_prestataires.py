from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from business.services import ensure_business_for_object


PHONE = "237680625082"
DISTRICTS = ["Bonamoussadi", "Kotto", "Bonaberi", "Makepe", "Akwa"]


class Command(BaseCommand):
    help = "Ajoute des prestataires demo dans les modules prioritaires E-Shelle."

    def handle(self, *args, **options):
        User = get_user_model()
        owner, _ = User.objects.get_or_create(
            username="demo_prestataire",
            defaults={"email": "demo_prestataire@e-shelle.local", "is_active": True},
        )
        owner.set_password("Demo@12345")
        owner.save()

        counts = {
            "resto": self.seed_resto(owner),
            "gaz": self.seed_gaz(owner),
            "pressing": self.seed_pressing(owner),
            "sante": self.seed_sante(owner),
            "jobs": self.seed_jobs(owner),
            "formation": self.seed_formations(owner),
        }

        for module, count in counts.items():
            self.stdout.write(self.style.SUCCESS(f"{module}: {count} elements prets"))
        self.stdout.write(self.style.SUCCESS("Demo E-Shelle prete pour le chat IA."))

    def seed_resto(self, owner):
        from resto.models import City, FoodCategory, Neighborhood, Restaurant

        city, _ = City.objects.get_or_create(slug="douala", defaults={"name": "Douala", "is_active": True})
        categories = []
        for idx, name in enumerate(["Grillades", "Cuisine camerounaise", "Fast food"]):
            cat, _ = FoodCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "icon": "R", "order": idx},
            )
            categories.append(cat)

        data = [
            ("Mama Ndole Bonamoussadi", "Bonamoussadi", "Ndole, eru, poisson braise et plats maison."),
            ("Le Coin du Poulet Kotto", "Kotto", "Poulet DG, brochettes et accompagnements rapides."),
            ("Saveurs de Bonaberi", "Bonaberi", "Cuisine locale, plats du jour et grillades."),
            ("Maquis Makepe Express", "Makepe", "Maquis convivial pour dejeuner et diner."),
            ("Akwa Lunch House", "Akwa", "Repas de bureau, jus naturels et service rapide."),
        ]
        count = 0
        for idx, (name, district, desc) in enumerate(data):
            neigh, _ = Neighborhood.objects.get_or_create(
                city=city,
                slug=slugify(district),
                defaults={"name": district},
            )
            restaurant, _ = Restaurant.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "owner": owner,
                    "name": name,
                    "description": desc,
                    "city": city,
                    "neighborhood": neigh,
                    "address": f"{district}, Douala",
                    "phone": "+237 680 625 082",
                    "whatsapp": "+237 680 625 082",
                    "status": "open",
                    "opening_time": time(8, 0),
                    "closing_time": time(22, 30),
                    "is_approved": True,
                    "is_featured": idx < 2,
                    "is_active": True,
                    "views_count": 120 - idx * 10,
                },
            )
            restaurant.categories.set(categories)
            profile = ensure_business_for_object(restaurant, "resto", {"owner": owner})
            profile.activate_plan("business", 30)
            profile.activate_boost(7 if idx < 2 else 3)
            profile.ai_credits = max(profile.ai_credits, 20)
            profile.save()
            count += 1
        return count

    def seed_gaz(self, owner):
        from gaz.models import DepotGaz, MarqueGaz, QuartierGaz, VilleGaz

        ville, _ = VilleGaz.objects.get_or_create(slug="douala", defaults={"nom": "Douala", "region": "Littoral", "active": True})
        marques = []
        for name in ["Tradex", "Bocom", "TotalEnergies"]:
            marque, _ = MarqueGaz.objects.get_or_create(slug=slugify(name), defaults={"nom": name, "active": True})
            marques.append(marque)

        data = [
            ("Gaz Express Bonamoussadi", "Bonamoussadi", 6500, 13500),
            ("Depot Gaz Kotto Service", "Kotto", 6400, 13200),
            ("Bonaberi Gaz Rapide", "Bonaberi", 6500, 13400),
            ("Makepe Gaz Livraison", "Makepe", 6450, 13300),
            ("Akwa Gaz Minute", "Akwa", 6600, 13600),
        ]
        count = 0
        for idx, (name, district, p6, p12) in enumerate(data):
            quartier, _ = QuartierGaz.objects.get_or_create(
                ville=ville,
                slug=slugify(f"douala-{district}"),
                defaults={"nom": district, "active": True},
            )
            depot, _ = DepotGaz.objects.update_or_create(
                slug=slugify(f"{name}-douala"),
                defaults={
                    "nom": name,
                    "description": "Livraison de gaz domestique a domicile, paiement a la reception.",
                    "ville": ville,
                    "quartier": quartier,
                    "adresse": f"{district}, Douala",
                    "zone_livraison": f"{district}, Bonaberie, Bonaberi, Makepe, Akwa, Bonamoussadi",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "tailles": ["6kg", "12kg", "15kg"],
                    "prix_6kg": p6,
                    "prix_12kg": p12,
                    "prix_15kg": p12 + 2500,
                    "livraison_rapide": True,
                    "delai_livraison": "30-45 min",
                    "livraison_nuit": idx in (0, 2),
                    "abonnement_actif": True,
                    "abonnement_expire_le": date.today() + timedelta(days=30),
                    "plan_actif": "pro",
                    "montant_paye": 5000,
                    "is_active": True,
                    "is_verified": True,
                    "is_featured": idx < 2,
                    "gerant": owner,
                    "note_moyenne": 4.8 - idx * 0.1,
                    "nb_avis": 12 - idx,
                },
            )
            depot.marques.set(marques)
            profile = ensure_business_for_object(depot, "gaz", {"owner": owner})
            profile.activate_plan("business", 30)
            profile.activate_boost(7 if idx < 2 else 3)
            profile.ai_credits = max(profile.ai_credits, 20)
            profile.save()
            count += 1
        return count

    def seed_pressing(self, owner):
        from pressing.models import CategoriePressing, Pressing, QuartierPressing, VillePressing

        ville, _ = VillePressing.objects.get_or_create(slug="douala", defaults={"nom": "Douala", "region": "Littoral", "active": True})
        categories = []
        for idx, name in enumerate(["Lavage", "Repassage", "Costumes"]):
            cat, _ = CategoriePressing.objects.get_or_create(slug=slugify(name), defaults={"nom": name, "icone": "P", "ordre": idx})
            categories.append(cat)

        data = [
            ("Pressing Clean Bonamoussadi", "Bonamoussadi"),
            ("Kotto Pressing Express", "Kotto"),
            ("Bonaberi Linge Pro", "Bonaberi"),
            ("Makepe Wash Service", "Makepe"),
            ("Akwa Pressing Bureau", "Akwa"),
        ]
        count = 0
        for idx, (name, district) in enumerate(data):
            quartier, _ = QuartierPressing.objects.get_or_create(
                ville=ville,
                slug=slugify(f"douala-{district}"),
                defaults={"nom": district, "active": True},
            )
            pressing, _ = Pressing.objects.update_or_create(
                slug=slugify(f"{name}-douala"),
                defaults={
                    "nom": name,
                    "description": "Lavage, repassage, collecte et livraison a domicile.",
                    "gerant": owner,
                    "ville": ville,
                    "quartier": quartier,
                    "adresse": f"{district}, Douala",
                    "zone_livraison": f"{district}, Bonaberi, Bonaberie, Makepe, Akwa",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "collecte_domicile": True,
                    "livraison_domicile": True,
                    "express": idx < 3,
                    "delai_traitement": "24h",
                    "delai_livraison": "2-4h",
                    "abonnement_actif": True,
                    "abonnement_expire_le": date.today() + timedelta(days=30),
                    "plan_actif": "pro",
                    "montant_paye": 5000,
                    "is_active": True,
                    "is_verified": True,
                    "is_featured": idx < 2,
                    "note_moyenne": 4.7 - idx * 0.1,
                    "nb_avis": 10 - idx,
                },
            )
            pressing.categories.set(categories)
            profile = ensure_business_for_object(pressing, "pressing", {"owner": owner})
            profile.activate_plan("business", 30)
            profile.activate_boost(7 if idx < 2 else 3)
            profile.ai_credits = max(profile.ai_credits, 20)
            profile.save()
            count += 1
        return count

    def seed_sante(self, owner):
        from sante.models import CategorieSante, ProfessionnelSante, VilleSante

        ville, _ = VilleSante.objects.get_or_create(slug="douala", defaults={"nom": "Douala", "region": "Littoral", "active": True})
        cat, _ = CategorieSante.objects.get_or_create(
            slug="pharmacie",
            defaults={"nom": "Pharmacie", "type_categorie": CategorieSante.TypeCategorie.SPECIALITE, "icone": "+"},
        )
        data = [
            ("Pharmacie Bonamoussadi Conseil", "Bonamoussadi"),
            ("Centre Sante Kotto Plus", "Kotto"),
            ("Pharma Bonaberi Service", "Bonaberi"),
            ("Clinique Makepe Assistance", "Makepe"),
            ("Pharmacie Akwa Express", "Akwa"),
        ]
        count = 0
        for idx, (name, district) in enumerate(data):
            pro, _ = ProfessionnelSante.objects.update_or_create(
                slug=slugify(f"{name}-douala"),
                defaults={
                    "nom": name,
                    "type_pro": ProfessionnelSante.TypePro.CLINIQUE if "Clinique" in name or "Centre" in name else ProfessionnelSante.TypePro.BIEN_ETRE,
                    "ville": ville,
                    "quartier": district,
                    "adresse": f"{district}, Douala",
                    "description": "Service sante de proximite. Contactez le professionnel pour confirmer disponibilite et rendez-vous.",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "horaires": "Lun-Dim 8h-21h",
                    "urgence": idx in (0, 3),
                    "teleconsultation": idx == 3,
                    "is_active": True,
                    "is_verified": True,
                    "is_featured": idx < 2,
                    "auteur": owner,
                },
            )
            pro.specialites.set([cat])
            profile = ensure_business_for_object(pro, "sante", {"owner": owner, "district": district})
            profile.activate_plan("business", 30)
            profile.activate_boost(7 if idx < 2 else 3)
            profile.ai_credits = max(profile.ai_credits, 20)
            profile.save()
            count += 1
        return count

    def seed_jobs(self, owner):
        from jobs.models import OffreJob, SecteurJob, VilleJob

        ville, _ = VilleJob.objects.get_or_create(slug="douala", defaults={"nom": "Douala", "region": "Littoral", "active": True})
        secteur, _ = SecteurJob.objects.get_or_create(slug="services", defaults={"nom": "Services", "active": True})
        data = [
            ("Livreur gaz moto", "Gaz Express Bonamoussadi", "Bonamoussadi", 80000, 120000),
            ("Serveuse restaurant", "Mama Ndole Bonamoussadi", "Bonamoussadi", 70000, 100000),
            ("Agent pressing", "Kotto Pressing Express", "Kotto", 65000, 90000),
            ("Community manager junior", "E-Shelle Business", "Akwa", 100000, 150000),
            ("Commercial terrain", "E-Shelle Douala", "Bonaberi", 100000, 250000),
        ]
        count = 0
        for idx, (title, company, district, smin, smax) in enumerate(data):
            job, _ = OffreJob.objects.update_or_create(
                slug=slugify(f"{title}-{company}"),
                defaults={
                    "titre": title,
                    "entreprise": company,
                    "secteur": secteur,
                    "ville": ville,
                    "quartier": district,
                    "type_contrat": OffreJob.TypeContrat.MISSION if "Commercial" in title else OffreJob.TypeContrat.CDD,
                    "mode_travail": OffreJob.ModeTravail.SUR_SITE,
                    "salaire_min": smin,
                    "salaire_max": smax,
                    "description": "Offre de demonstration pour E-Shelle Jobs. Contact WhatsApp pour postuler.",
                    "missions": "Servir les clients, respecter les horaires et communiquer rapidement.",
                    "profil_recherche": "Personne serieuse, dynamique et disponible a Douala.",
                    "avantages": "Paiement mensuel, primes selon performance.",
                    "telephone": PHONE,
                    "whatsapp": PHONE,
                    "date_limite": date.today() + timedelta(days=21),
                    "is_active": True,
                    "is_verified": True,
                    "is_featured": idx < 2,
                    "auteur": owner,
                },
            )
            profile = ensure_business_for_object(job, "jobs", {"owner": owner, "district": district, "name": company})
            profile.activate_plan("pro", 30)
            profile.activate_boost(3)
            profile.ai_credits = max(profile.ai_credits, 5)
            profile.save()
            count += 1
        return count

    def seed_formations(self, owner):
        from formations.models import Categorie, Formation

        cat, _ = Categorie.objects.get_or_create(slug="concours-cameroun", defaults={"nom": "Concours Cameroun", "icone": "F", "active": True})
        data = [
            ("Preparation concours ENAM 2026", "ENAM, culture generale, droit public et methodologie."),
            ("Anglais pratique pour entretien", "Parler anglais simplement pour entretien et travail."),
            ("Marketing digital pour commerce local", "Facebook, TikTok, WhatsApp et vente locale."),
            ("Initiation intelligence artificielle", "Utiliser l'IA pour creer textes, visuels et business."),
            ("Comptabilite simple pour petit commerce", "Suivre recettes, depenses et benefices."),
        ]
        count = 0
        for idx, (title, desc) in enumerate(data):
            formation, _ = Formation.objects.update_or_create(
                slug=slugify(title),
                defaults={
                    "titre": title,
                    "description": desc,
                    "description_courte": desc,
                    "categorie": cat,
                    "formateur": owner,
                    "niveau": "debutant" if idx else "intermediaire",
                    "langue": "fr",
                    "prix": Decimal("0.00") if idx == 0 else Decimal("5000.00"),
                    "prix_barre": Decimal("10000.00") if idx else None,
                    "is_published": True,
                    "is_featured": idx < 2,
                    "nb_lecons": 8 + idx,
                    "duree_totale": 120 + idx * 30,
                    "nb_inscrits": 30 - idx * 3,
                    "note_moyenne": 4.8 - idx * 0.1,
                    "objectifs": ["Apprendre vite", "Pratiquer", "Obtenir des resultats"],
                    "prerequis": ["Telephone ou ordinateur", "Connexion internet"],
                },
            )
            profile = ensure_business_for_object(formation, "formation", {"owner": owner, "city": "Douala", "district": "En ligne"})
            profile.activate_plan("business", 30)
            profile.ai_credits = max(profile.ai_credits, 20)
            profile.save()
            count += 1
        return count
