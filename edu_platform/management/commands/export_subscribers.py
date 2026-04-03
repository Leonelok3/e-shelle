"""
Commande : export_subscribers
Exporte les abonnés actifs en CSV.
Usage : python manage.py export_subscribers > abonnes.csv
"""
import csv
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from edu_platform.models import AccessCode


class Command(BaseCommand):
    help = 'Exporte les abonnés actifs en CSV'

    def handle(self, *args, **options):
        writer = csv.writer(sys.stdout)
        writer.writerow(['Nom', 'Email', 'Téléphone', 'Plan', 'Activé le', 'Expire le', 'Appareil'])

        codes = AccessCode.objects.filter(
            status='active',
            expires_at__gt=timezone.now()
        ).select_related('activated_by', 'plan').order_by('-activated_at')

        count = 0
        for code in codes:
            user = code.activated_by
            if not user:
                continue
            try:
                phone = user.edu_profile.phone_number
            except Exception:
                phone = ''
            binding = code.device_bindings.filter(is_primary=True).first()
            device_label = binding.device_label if binding else ''

            writer.writerow([
                user.get_full_name() or user.username,
                user.email,
                phone,
                code.plan.name,
                code.activated_at.strftime('%d/%m/%Y') if code.activated_at else '',
                code.expires_at.strftime('%d/%m/%Y') if code.expires_at else '',
                device_label,
            ])
            count += 1

        self.stderr.write(f'{count} abonnés exportés.')
