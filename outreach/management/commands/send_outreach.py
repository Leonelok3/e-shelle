"""
python manage.py send_outreach --campaign_id 1
python manage.py send_outreach --campaign_id 1 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envoie une campagne outreach par ID."

    def add_arguments(self, parser):
        parser.add_argument("--campaign_id", type=int, required=True)
        parser.add_argument("--dry-run", action="store_true", help="Simulation sans envoi")

    def handle(self, *args, **options):
        from outreach.models import OutreachCampaign
        from outreach.services import send_campaign

        cid = options["campaign_id"]
        dry_run = options["dry_run"]

        try:
            campaign = OutreachCampaign.objects.get(pk=cid)
        except OutreachCampaign.DoesNotExist:
            raise CommandError(f"Campagne ID {cid} introuvable.")

        if campaign.status == "sent" and not dry_run:
            self.stdout.write(self.style.WARNING(f"Campagne '{campaign.name}' déjà envoyée. Utilisez --dry-run pour simuler."))
            return

        mode = "[DRY-RUN]" if dry_run else ""
        self.stdout.write(f"{mode} Envoi de '{campaign.name}' …")

        result = send_campaign(campaign, dry_run=dry_run)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN] {result['total']} contact(s) seraient ciblés."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Terminé — {result['sent']} envoyé(s), {result['failed']} échoué(s) sur {result['total']}."
                )
            )
