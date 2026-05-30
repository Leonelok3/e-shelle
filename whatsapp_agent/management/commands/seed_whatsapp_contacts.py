from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cree des utilisateurs de test avec numeros WhatsApp pour les campagnes E-Shelle."

    CONTACTS = [
        ("client_douala", "client.douala@e-shelle.local", "Aline", "Douala", "CLIENT", "+237690000001"),
        ("client_yaounde", "client.yaounde@e-shelle.local", "Brice", "Yaounde", "CLIENT", "+237690000002"),
        ("vendeur_douala", "vendeur.douala@e-shelle.local", "Carine", "Douala", "VENDOR", "+237690000003"),
        ("vendeur_bafoussam", "vendeur.bafoussam@e-shelle.local", "David", "Bafoussam", "VENDOR", "+237690000004"),
        ("premium_yaounde", "premium.yaounde@e-shelle.local", "Estelle", "Yaounde", "CLIENT", "+237690000005"),
        ("resto_kribi", "resto.kribi@e-shelle.local", "Franck", "Kribi", "VENDOR", "+237690000006"),
    ]

    def handle(self, *args, **options):
        User = get_user_model()
        created = 0
        updated = 0
        for username, email, first_name, ville, role, whatsapp in self.CONTACTS:
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "role": role,
                    "ville": ville,
                    "whatsapp": whatsapp,
                    "is_active": True,
                },
            )
            user.email = email
            user.first_name = first_name
            user.role = role
            user.ville = ville
            user.whatsapp = whatsapp
            user.is_active = True
            user.set_password("Test@2026!")
            user.save()
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Contacts WhatsApp prets: {created} crees, {updated} mis a jour."))
