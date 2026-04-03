"""
Commande : cleanup_expired_subscriptions
Passe en 'expired' tous les codes d'accès dont la date d'expiration est dépassée.
À lancer en cron daily : 0 2 * * * python manage.py cleanup_expired_subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from edu_platform.models import AccessCode


class Command(BaseCommand):
    help = 'Passe les codes d\'accès expirés au statut "expired"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Affiche les codes qui seraient expirés sans les modifier'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        expired_codes = AccessCode.objects.filter(
            status='active',
            expires_at__lt=now
        )

        count = expired_codes.count()

        if dry_run:
            self.stdout.write(f'[DRY-RUN] {count} code(s) seraient expirés.')
            for code in expired_codes[:20]:
                self.stdout.write(f'  - {code.code} (expiré le {code.expires_at})')
            return

        updated = expired_codes.update(status='expired')
        self.stdout.write(
            self.style.SUCCESS(f'{updated} code(s) passé(s) au statut "expired".')
        )
