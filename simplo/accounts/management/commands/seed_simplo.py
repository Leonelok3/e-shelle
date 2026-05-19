from decimal import Decimal

from django.core.management.base import BaseCommand

from simplo.accounts.models import ClientProfile, CustomUser, PrestataireProfile


class Command(BaseCommand):
    help = "Injecte un jeu de données réaliste pour tester Simplo en local."

    PASSWORD = "Simplo2026!"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation des données Simplo...")
        self._create_clients()
        self._create_providers()
        self.stdout.write(self.style.SUCCESS("Seed Simplo terminé."))
        self.stdout.write(f"Mot de passe test prestataires : {self.PASSWORD}")

    def _create_clients(self):
        clients = [
            ("client_akwa", "Nadia", "Mballa", "+237690300001", "Douala", "Akwa"),
            ("client_bastos", "Samuel", "Talla", "+237690300002", "Yaoundé", "Bastos"),
        ]

        for username, first_name, last_name, phone, ville, quartier in clients:
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone_number": phone,
                    "role": CustomUser.Role.CLIENT,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(self.PASSWORD)
                user.save(update_fields=["password"])

            ClientProfile.objects.update_or_create(
                user=user,
                defaults={
                    "nom": user.get_full_name(),
                    "telephone": phone,
                    "ville": ville,
                    "quartier": quartier,
                },
            )

    def _create_providers(self):
        providers = [
            ("moto_akwa_1", "Jean", "Moto", "+237690000001", "Douala", "Akwa", "MOTO", "Moto Boxer", "4.80", 12, 184, "Akwa, Bonapriso, Bali", "06h00 - 23h00"),
            ("moto_bonamoussadi_1", "Ariel", "Rapide", "+237690000002", "Douala", "Bonamoussadi", "MOTO", "Moto TVS", "4.75", 21, 236, "Bonamoussadi, Makepe, Denver", "05h30 - 22h30"),
            ("moto_deido_1", "Patrick", "Express", "+237690000003", "Douala", "Deido", "MOTO", "Moto", "4.70", 8, 97, "Deido, Akwa Nord, Bessengue", "06h00 - 21h30"),
            ("moto_bastos_1", "Junior", "Bastos", "+237690000004", "Yaoundé", "Bastos", "MOTO", "Moto", "4.90", 16, 151, "Bastos, Golf, Nlongkak", "06h00 - 22h00"),
            ("moto_biyem_1", "Roland", "Carrefour", "+237690000005", "Yaoundé", "Biyem-Assi", "MOTO", "Moto", "4.65", 9, 88, "Biyem-Assi, Melen, Mendong", "06h30 - 21h00"),
            ("livreur_akwa_1", "Brice", "Colis", "+237690000006", "Douala", "Akwa", "LIVRAISON", "Moto livraison", "4.82", 18, 202, "Akwa, Bonanjo, Bali", "08h00 - 20h00"),
            ("livreur_makepe_1", "Yvan", "Livraison", "+237690000007", "Douala", "Makepe", "LIVRAISON", "Moto cargo", "4.76", 14, 144, "Makepe, Bonamoussadi, Logpom", "08h00 - 21h00"),
            ("livreur_mokolo_1", "Cedric", "Dispatch", "+237690000008", "Yaoundé", "Mokolo", "LIVRAISON", "Moto livraison", "4.60", 11, 81, "Mokolo, Mvog-Mbi, Tsinga", "08h00 - 19h30"),
            ("courses_akwa_1", "Mireille", "Service", "+237690000009", "Douala", "Akwa", "COURSES", "Assistant courses", "4.95", 33, 268, "Akwa, Bonapriso, Marché Congo", "07h00 - 18h30"),
            ("courses_bonapriso_1", "Carine", "Marché", "+237690000010", "Douala", "Bonapriso", "COURSES", "Assistant courses", "4.88", 19, 174, "Bonapriso, Bali, Bonanjo", "07h00 - 19h00"),
            ("courses_essos_1", "Daniel", "Courses", "+237690000011", "Yaoundé", "Essos", "COURSES", "Assistant courses", "4.72", 10, 73, "Essos, Mvog-Ada, Mimboman", "07h30 - 18h00"),
            ("enfants_bastos_1", "Estelle", "Confiance", "+237690000012", "Yaoundé", "Bastos", "ENFANTS", "Accompagnement école", "4.91", 27, 119, "Bastos, Golf, Nlongkak", "06h00 - 17h30"),
            ("enfants_biyem_1", "Marc", "Ecole", "+237690000013", "Yaoundé", "Biyem-Assi", "ENFANTS", "Accompagnement école", "4.67", 7, 48, "Biyem-Assi, Mendong, Melen", "06h00 - 17h00"),
            ("enfants_bonamoussadi_1", "Nadine", "Kids", "+237690000014", "Douala", "Bonamoussadi", "ENFANTS", "Accompagnement école", "4.85", 15, 102, "Bonamoussadi, Makepe, Denver", "06h00 - 17h30"),
            ("livreur_newbell_1", "Serge", "Depot", "+237690000015", "Douala", "New Bell", "LIVRAISON", "Moto livraison", "4.58", 6, 61, "New Bell, Nkololoun, Village", "08h00 - 20h00"),
        ]

        service_map = {
            "MOTO": PrestataireProfile.ServiceType.MOTO,
            "LIVRAISON": PrestataireProfile.ServiceType.LIVRAISON,
            "COURSES": PrestataireProfile.ServiceType.COURSES,
            "ENFANTS": PrestataireProfile.ServiceType.ENFANTS,
        }

        for username, first_name, last_name, phone, ville, quartier, service, vehicule, note, avis, courses, zone, horaires in providers:
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone_number": phone,
                    "role": CustomUser.Role.PRESTATAIRE,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(self.PASSWORD)
                user.save(update_fields=["password"])

            PrestataireProfile.objects.update_or_create(
                user=user,
                defaults={
                    "nom": user.get_full_name(),
                    "telephone": phone,
                    "ville": ville,
                    "quartier_base": quartier,
                    "type_service": service_map[service],
                    "type_vehicule": vehicule,
                    "zone_couverte": zone,
                    "horaires": horaires,
                    "statut": PrestataireProfile.Status.DISPONIBLE,
                    "note": Decimal(note),
                    "nombre_avis": avis,
                    "nombre_courses": courses,
                    "is_verified": True,
                    "is_active": True,
                },
            )
