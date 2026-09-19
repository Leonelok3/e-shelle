"""Read-only WhatsApp diagnostics. Never starts a campaign or sends a message."""
import json
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from whatsapp_agent.models import Campagne


class Command(BaseCommand):
    help = "Verifie WhatsApp sans envoyer de messages ni afficher les secrets."

    def add_arguments(self, parser):
        parser.add_argument("--campaign-id", type=int)
        parser.add_argument("--check-meta", action="store_true")
        parser.add_argument("--waba-id", help="Compte WhatsApp Business pour lire les modeles approuves")
        parser.add_argument("--check-workers", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(json.dumps({
            "simulation": settings.WHATSAPP_DRY_RUN,
            "token_present": bool(settings.WHATSAPP_TOKEN),
            "phone_id_present": bool(settings.WHATSAPP_PHONE_ID),
            "webhook_secret_present": bool(getattr(settings, "WHATSAPP_APP_SECRET", "")),
            "verify_token_present": bool(getattr(settings, "WHATSAPP_VERIFY_TOKEN", "")),
            "default_template": getattr(settings, "WHATSAPP_DEFAULT_TEMPLATE", ""),
            "force_template": getattr(settings, "WHATSAPP_FORCE_TEMPLATE", False),
        }, ensure_ascii=False))
        if options["campaign_id"]:
            campaign = Campagne.objects.filter(pk=options["campaign_id"]).first()
            if not campaign:
                raise CommandError("Campagne introuvable dans cette base.")
            self.stdout.write(json.dumps({"campaign_id": campaign.pk, "status": campaign.statut,
                "messages": list(campaign.messages.values("statut").annotate(count=Count("pk"))),
                "recent_error_codes": [str(error)[:500] for error in campaign.messages.exclude(erreur="").values_list("erreur", flat=True)[:3]],
            }, ensure_ascii=False))
        if options["check_workers"]:
            from edu_cm.celery import app
            try:
                registered = app.control.inspect(timeout=3).registered() or {}
                tasks = {task for names in registered.values() for task in names}
                self.stdout.write(json.dumps({"workers_responding": len(registered),
                    "whatsapp_tasks_registered": sorted(task for task in tasks if task.startswith("whatsapp_agent."))}))
            except Exception as exc:
                raise CommandError(f"Verification Celery impossible ({type(exc).__name__}).") from None
        if options["check_meta"]:
            if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
                raise CommandError("Identifiants Meta absents. Aucun appel effectue.")
            endpoint = urlsplit(settings.WHATSAPP_API_URL)
            if endpoint.scheme != "https" or endpoint.hostname != "graph.facebook.com":
                raise CommandError("Le diagnostic exige un endpoint HTTPS officiel Meta.")
            version = endpoint.path.strip("/").split("/")[0]
            base = f"https://graph.facebook.com/{version}"
            headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
            queries = [(f"{base}/{settings.WHATSAPP_PHONE_ID}", {"fields": "id,display_phone_number,verified_name,quality_rating"})]
            if options["waba_id"]:
                if not options["waba_id"].isdigit():
                    raise CommandError("WABA ID invalide.")
                queries.append((f"{base}/{options['waba_id']}/message_templates",
                    {"fields": "name,status,language", "limit": 100}))
            for url, params in queries:
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    data = response.json()
                except (requests.RequestException, ValueError) as exc:
                    raise CommandError(f"Meta inaccessible ({type(exc).__name__}).") from None
                if response.status_code != 200:
                    error = data.get("error", {})
                    raise CommandError(f"Meta HTTP {response.status_code}, code {error.get('code')}: {error.get('message', '')[:400]}")
                if "data" in data:
                    self.stdout.write(json.dumps({"templates": data["data"],
                        "more_templates": bool(data.get("paging", {}).get("next"))}, ensure_ascii=False))
                else:
                    self.stdout.write(json.dumps({key: data.get(key) for key in
                        ("id", "display_phone_number", "verified_name", "quality_rating")}, ensure_ascii=False))
