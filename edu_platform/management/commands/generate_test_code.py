"""
Commande : generate_test_code
Génère un code de test pour l'admin (dev/staging uniquement).
Usage : python manage.py generate_test_code --plan-id 1
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Génère un code de test (DEBUG uniquement)'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True, help='ID du plan d\'abonnement')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Cette commande est réservée au mode DEBUG.')

        from edu_platform.models import SubscriptionPlan
        from edu_platform.services.code_generator import generate_test_code

        try:
            plan = SubscriptionPlan.objects.get(pk=options['plan_id'])
        except SubscriptionPlan.DoesNotExist:
            raise CommandError(f"Plan ID {options['plan_id']} introuvable.")

        code = generate_test_code(plan)
        self.stdout.write(self.style.SUCCESS(
            f'\nCode de test généré :\n'
            f'  Code   : {code.code}\n'
            f'  Plan   : {plan.name}\n'
            f'  Statut : {code.status}\n'
            f'\nActivez-le sur : http://localhost:8000/edu/activate/'
        ))
