from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from ocd_live.models import LivePackage, LiveSlot


class Command(BaseCommand):
    help = "Initialise les packages officiels OCD Live et génère des créneaux de test pour les 14 prochains jours."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🚀 Initialisation des Packages Live OCD..."))

        packages_data = [
            {
                "nom": "Pass Découverte",
                "slug": "pass-decouverte",
                "duree_minutes": 60,
                "prix_xaf": Decimal("10000.00"),
                "description": "Présentation simple produit/service. Idéal pour faire connaître une nouveauté ou tester l'audience.",
                "est_recommande": False,
                "actif": True,
                "ordre": 1,
            },
            {
                "nom": "Pass Business",
                "slug": "pass-business",
                "duree_minutes": 120,
                "prix_xaf": Decimal("20000.00"),
                "description": "Présentation + démo + questions live. La formule recommandée pour convertir et vendre en direct.",
                "est_recommande": True,
                "actif": True,
                "ordre": 2,
            },
            {
                "nom": "Pass Premium",
                "slug": "pass-premium",
                "duree_minutes": 180,
                "prix_xaf": Decimal("30000.00"),
                "description": "Présentation + démo + interview exclusive + mise en avant premium sur les canaux E-Shelle.",
                "est_recommande": False,
                "actif": True,
                "ordre": 3,
            },
            {
                "nom": "Pass Marathon",
                "slug": "pass-marathon",
                "duree_minutes": 300,
                "prix_xaf": Decimal("50000.00"),
                "description": "Événement complet (5h), plusieurs produits/services présentés, invités et prise de commandes continue.",
                "est_recommande": False,
                "actif": True,
                "ordre": 4,
            },
        ]

        created_packages = 0
        updated_packages = 0
        for data in packages_data:
            pkg, created = LivePackage.objects.update_or_create(
                slug=data["slug"],
                defaults=data,
            )
            if created:
                created_packages += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Créé: {pkg.nom} - {pkg.duree_display} - {pkg.prix_formate}"))
            else:
                updated_packages += 1
                self.stdout.write(self.style.WARNING(f"  ↺ Mis à jour: {pkg.nom} - {pkg.duree_display} - {pkg.prix_formate}"))

        self.stdout.write(self.style.NOTICE("\n📅 Génération des créneaux (slots) pour les 14 prochains jours..."))
        
        today = timezone.localdate()
        heures_creneaux = [
            (time(10, 0), time(12, 0)),
            (time(14, 0), time(16, 0)),
            (time(17, 0), time(19, 0)),
            (time(20, 0), time(22, 0)),
        ]

        created_slots = 0
        for day_offset in range(1, 15):
            slot_date = today + timedelta(days=day_offset)
            for heure_deb, heure_f in heures_creneaux:
                slot, created = LiveSlot.objects.get_or_create(
                    date=slot_date,
                    heure_debut=heure_deb,
                    defaults={
                        "heure_fin": heure_f,
                        "capacite": 1,
                        "est_disponible": True,
                        "est_bloque_admin": False,
                    },
                )
                if created:
                    created_slots += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Succès ! Packages: {created_packages} créés, {updated_packages} mis à jour. Créneaux: {created_slots} nouveaux créneaux ajoutés sur les 14 prochains jours."
            )
        )

