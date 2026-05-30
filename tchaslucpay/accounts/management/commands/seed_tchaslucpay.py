from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save

from tchaslucpay.accounts.models import ClientProfile, CollecteurProfile, UserRole
from tchaslucpay.transactions.models import AccountBalance, Transaction
from tchaslucpay.notifications.signals import notify_transaction_validated
from tchaslucpay.transactions.services import creer_transaction


class Command(BaseCommand):
    help = "Genere un jeu de donnees de demonstration pour Tchaslucpay."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._clear_demo_data()
            admin = self._create_admin()
            collecteurs = self._create_collecteurs()
            clients = self._create_clients(collecteurs)

        post_save.disconnect(notify_transaction_validated, sender=Transaction)
        try:
            self._create_transactions(clients, collecteurs)
        finally:
            post_save.connect(notify_transaction_validated, sender=Transaction)

        self._sync_account_balances()

        self.stdout.write(self.style.SUCCESS("Seed Tchaslucpay termine."))
        self.stdout.write("Admin: admin_tchaslucpay / Admin12345!")
        self.stdout.write(f"Collecteurs: {', '.join(c.user.username for c in collecteurs)}")
        self.stdout.write(f"Clients: {ClientProfile.objects.filter(user__username__startswith='client_demo_').count()}")
        self.stdout.write(f"Transactions: {Transaction.objects.count()}")

    def _clear_demo_data(self):
        User = get_user_model()
        demo_usernames = [
            "admin_tchaslucpay",
            "collecteur_central",
            "collecteur_mokolo",
            "client_demo_1",
            "client_demo_2",
            "client_demo_3",
            "client_demo_4",
            "client_demo_5",
        ]
        Transaction.objects.filter(
            account__username__in=demo_usernames,
            collector__username__in=demo_usernames,
        ).delete()
        AccountBalance.objects.filter(user__username__in=demo_usernames).delete()
        ClientProfile.objects.filter(user__username__in=demo_usernames).delete()
        CollecteurProfile.objects.filter(user__username__in=demo_usernames).delete()
        User.objects.filter(username__in=demo_usernames).delete()

    def _create_admin(self):
        User = get_user_model()
        admin = User.objects.create_user(
            username="admin_tchaslucpay",
            email="admin@tchaslucpay.local",
            password="Admin12345!",
            first_name="Admin",
            last_name="Tchaslucpay",
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        return admin

    def _create_collecteurs(self):
        specs = [
            {
                "username": "collecteur_central",
                "first_name": "Martial",
                "last_name": "Essomba",
                "employee_code": "COL-CENTRAL-001",
                "zone": "Marche Central",
                "phone_number": "+237690100001",
            },
            {
                "username": "collecteur_mokolo",
                "first_name": "Aline",
                "last_name": "Ngono",
                "employee_code": "COL-MOKOLO-002",
                "zone": "Mokolo",
                "phone_number": "+237690100002",
            },
        ]
        collecteurs = []
        User = get_user_model()
        for spec in specs:
            user = User.objects.create_user(
                username=spec["username"],
                email=f"{spec['username']}@tchaslucpay.local",
                password="Collecteur123!",
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                role=UserRole.COLLECTEUR,
                phone_number=spec["phone_number"],
            )
            collecteurs.append(
                CollecteurProfile.objects.create(
                    user=user,
                    employee_code=spec["employee_code"],
                    zone=spec["zone"],
                    city="Yaounde",
                    phone_number=spec["phone_number"],
                )
            )
        return collecteurs

    def _create_clients(self, collecteurs):
        specs = [
            ("client_demo_1", "Colette", "Ndzie", "Boutique vivres frais", Decimal("45000.00"), collecteurs[0]),
            ("client_demo_2", "Serge", "Mbarga", "Quincaillerie express", Decimal("80000.00"), collecteurs[0]),
            ("client_demo_3", "Mireille", "Tchana", "Depot boissons", Decimal("125000.00"), collecteurs[0]),
            ("client_demo_4", "Jacques", "Fouda", "Etal legumes", Decimal("30000.00"), collecteurs[1]),
            ("client_demo_5", "Nadine", "Mballa", "Cosmetiques Mokolo", Decimal("65000.00"), collecteurs[1]),
        ]
        clients = []
        User = get_user_model()
        for index, (username, first_name, last_name, commerce, solde, collecteur) in enumerate(specs, start=1):
            user = User.objects.create_user(
                username=username,
                email=f"{username}@tchaslucpay.local",
                password="Client123!",
                first_name=first_name,
                last_name=last_name,
                role=UserRole.CLIENT,
                phone_number=f"+23769120000{index}",
            )
            clients.append(
                ClientProfile.objects.create(
                    user=user,
                    account_number=f"TLP-2026-000{index}",
                    national_id=f"CNI-DEMO-{index:03d}",
                    national_id_expiry="2031-12-31",
                    city="Yaounde",
                    quarter=commerce,
                    phone_number=user.phone_number,
                    solde=solde,
                    trusted_collecteur=collecteur,
                )
            )
        return clients

    def _create_transactions(self, clients, collecteurs):
        operations = [
            (clients[0], collecteurs[0], "DEPOT", Decimal("15000.00"), "Depot ouverture journee"),
            (clients[2], collecteurs[0], "DEPOT", Decimal("35000.00"), "Depot ventes grossiste"),
            (clients[3], collecteurs[1], "DEPOT", Decimal("10000.00"), "Depot caisse matin"),
            (clients[1], collecteurs[0], "DEPOT", Decimal("50000.00"), "Depot recette"),
            (clients[4], collecteurs[1], "DEPOT", Decimal("25000.00"), "Depot fin de journee"),
            (clients[0], collecteurs[0], "DEPOT", Decimal("12000.00"), "Depot complementaire"),
            (clients[3], collecteurs[1], "DEPOT", Decimal("5000.00"), "Depot marche"),
        ]
        for client, collecteur, type_op, montant, note in operations:
            creer_transaction(client.pk, collecteur.pk, type_op, montant, note=note)

    def _sync_account_balances(self):
        for client in ClientProfile.objects.select_related("user"):
            AccountBalance.objects.update_or_create(
                user=client.user,
                defaults={"available_balance": client.solde, "locked_balance": Decimal("0.00"), "currency": "XAF"},
            )
