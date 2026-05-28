import urllib.parse

from django.conf import settings
from django.core.management.base import BaseCommand

from business.models import BusinessProfile
from business.reporting import business_report_context


class Command(BaseCommand):
    help = "Prepare les rapports WhatsApp hebdomadaires pour les prestataires E-Shelle."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, choices=[7, 30, 90, 365])
        parser.add_argument("--module", type=str, default="")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = options["days"]
        qs = BusinessProfile.objects.filter(is_active=True).exclude(phone="", whatsapp="")
        if options["module"]:
            qs = qs.filter(module=options["module"])
        qs = qs.order_by("-leads_count", "-views_count", "name")[: options["limit"]]

        base_url = getattr(settings, "SITE_URL", "").rstrip("/")
        count = 0
        for business in qs:
            number = _clean_number(business.whatsapp or business.phone)
            if not number:
                continue
            context = business_report_context(business, days)
            report_url = f"{base_url}/business/report/{business.id}/?days={days}" if base_url else f"/business/report/{business.id}/?days={days}"
            message = (
                f"Bonjour {business.name}, voici votre rapport E-Shelle des {days} derniers jours:\n"
                f"- {context['views']} vues\n"
                f"- {context['contacts']} contacts\n"
                f"- {context['details']} clics detail\n\n"
                f"Rapport complet: {report_url}\n"
                "Conseil: gardez vos visuels et offres premium a jour pour convertir plus de clients."
            )
            whatsapp_url = f"https://wa.me/{number}?text={urllib.parse.quote(message)}"
            count += 1

            if options["dry_run"]:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] {business.name}: {whatsapp_url}"))
            else:
                # Sans API WhatsApp officielle configuree, la commande prepare les liens.
                # Elle peut etre branchee plus tard a un provider WhatsApp Business.
                self.stdout.write(f"{business.name}: {whatsapp_url}")

        self.stdout.write(self.style.SUCCESS(f"{count} rapport(s) hebdomadaire(s) prepare(s)."))


def _clean_number(value: str) -> str:
    number = (value or "").replace("+", "").replace(" ", "").replace("-", "")
    if not number:
        return ""
    if not number.startswith("237"):
        number = f"237{number}"
    return number
