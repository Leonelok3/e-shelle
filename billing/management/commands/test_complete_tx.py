# billing/management/commands/test_complete_tx.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model

from billing.models import Transaction, SubscriptionPlan

User = get_user_model()

class Command(BaseCommand):
    help = "Crée une transaction factice et appelle Transaction.complete() pour tester la création d'abonnement/commission."

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, required=True, help='ID de l utilisateur (ex: 1)')
        parser.add_argument('--plan', type=str, required=True, help='slug du plan (ex: decouverte-24h)')

    def handle(self, *args, **options):
        user_id = options['user']
        plan_slug = options['plan']

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Utilisateur id={user_id} n'existe pas."))
            return

        try:
            plan = SubscriptionPlan.objects.get(slug=plan_slug)
        except SubscriptionPlan.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Plan slug='{plan_slug}' introuvable."))
            return

        tx = Transaction.objects.create(
            user=user,
            plan=plan,
            amount=plan.price_usd,
            currency='USD',
            type='CREDIT',
            status='PENDING',
            description='Transaction de test via management command',
            external_transaction_id=f"TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )
        self.stdout.write(self.style.SUCCESS(f"Transaction créée id={tx.id}, status={tx.status}"))

        # Appel de la méthode complete()
        tx.complete()
        tx.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f"Transaction id={tx.id} après complete() => status={tx.status}"))
        if tx.related_subscription:
            self.stdout.write(self.style.SUCCESS(f"Subscription créée id={tx.related_subscription.id} expires_at={tx.related_subscription.expires_at}"))
        else:
            self.stdout.write(self.style.WARNING("Aucune subscription créée. Vérifie le champ plan lié."))
