from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from salonhub.salons.models import Category, Salon, Service, OpeningHour


class Command(BaseCommand):
    help = "Cree des donnees de demonstration (categories, salon, prestations, horaires)."

    def handle(self, *args, **options):

        from accounts.models import User
        from salons.models import Category, Salon, Service, OpeningHour

        cat_coiffure, _ = Category.objects.get_or_create(name="Coiffure femme", defaults={"icon": "💇‍♀️"})
        cat_barbier, _ = Category.objects.get_or_create(name="Barbier", defaults={"icon": "💈"})
        cat_institut, _ = Category.objects.get_or_create(name="Institut de beauté", defaults={"icon": "💅"})

        User = get_user_model()
        owner, created = User.objects.get_or_create(
            username="demo_owner",
            defaults={"role": User.Role.OWNER, "email": "owner@example.com", "phone": "237690000000"}
        )
        if created:
            owner.set_password("demo1234")
            owner.save()

        salon, _ = Salon.objects.get_or_create(
            slug="eclat-de-reine-yaounde",
            defaults=dict(
                owner=owner, name="Éclat de Reine", kind="salon", category=cat_coiffure,
                description="Salon de coiffure premium spécialisé dans les tresses, tissages et soins capillaires naturels.",
                city="Yaoundé", district="Bastos", address="Rue 1.812, Bastos, Yaoundé",
                whatsapp_number="237690000000", phone_display="690 00 00 00", is_active=True, is_verified=True,
            )
        )

        if not salon.services.exists():
            Service.objects.bulk_create([
                Service(salon=salon, name="Tresses box braids", price=15000, duration_minutes=180, order=1),
                Service(salon=salon, name="Défrisage + Brushing", price=8000, duration_minutes=90, order=2),
                Service(salon=salon, name="Soin profond kératine", price=12000, duration_minutes=60, order=3),
            ])

        if not salon.opening_hours.exists():
            for wd in range(6):  # lundi à samedi
                OpeningHour.objects.create(salon=salon, weekday=wd, start_time="08:30", end_time="18:30")
            OpeningHour.objects.create(salon=salon, weekday=6, is_closed=True, start_time="08:00", end_time="08:00")
        self.stdout.write(self.style.SUCCESS(
            "Seed termine. Compte prestataire demo -> username: demo_owner / mot de passe: demo1234"
        ))
