from __future__ import annotations

import logging
import re
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import CanadaJobOffer, CanadaScholarship, CanadaVisitorOpportunity, CanadaNews

logger = logging.getLogger(__name__)

_FR_MONTHS = {
    "janvier": "january", "février": "february", "fevrier": "february",
    "mars": "march", "avril": "april", "mai": "may", "juin": "june",
    "juillet": "july", "août": "august", "aout": "august",
    "septembre": "september", "octobre": "october",
    "novembre": "november", "décembre": "december", "decembre": "december",
}


def _is_url_active(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    if "example.com" in url or "localhost" in url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if resp.status_code in [404, 410]:
            return False
        if resp.status_code < 400 or resp.status_code == 403:
            return True
        resp = requests.get(url, headers=headers, timeout=5, allow_redirects=True, stream=True)
        if resp.status_code in [404, 410]:
            return False
        return resp.status_code < 400
    except Exception:
        return False


def _parse_deadline(deadline_str: str):
    if not deadline_str:
        return None
    text = deadline_str.strip().lower()
    if not text or "précisé" in text or "precise" in text or "non " in text:
        return None

    for fr, en in _FR_MONTHS.items():
        text = re.sub(rf"\b{fr}\b", en, text)

    try:
        from dateutil import parser as date_parser
        parsed = date_parser.parse(text, dayfirst=True, fuzzy=True)
        return parsed.date()
    except Exception:
        return None


class Command(BaseCommand):
    help = "Vérifie les liens d'offres d'emploi, bourses, opportunités et actualités pour désactiver ou supprimer les liens morts ou expirés"

    def handle(self, *args, **options):
        self.stdout.write("--- Début de la vérification de cohérence des offres (Canada) ---")

        # 1. Vérification des offres d'emploi Canada
        job_offers = CanadaJobOffer.objects.filter(is_active=True)
        self.stdout.write(f"Vérification de {job_offers.count()} offres d'emploi active(s)...")
        deactivated_jobs = 0
        for offer in job_offers:
            # Vérifier date limite
            deadline_date = _parse_deadline(offer.deadline)
            if deadline_date and deadline_date < timezone.localdate():
                offer.is_active = False
                offer.save(update_fields=["is_active"])
                deactivated_jobs += 1
                self.stdout.write(f"[-] Offre d'emploi '{offer.title}' désactivée : Date limite dépassée ({offer.deadline})")
                continue

            # Vérifier l'activité du lien URL
            if not _is_url_active(offer.url_apply):
                offer.is_active = False
                offer.save(update_fields=["is_active"])
                deactivated_jobs += 1
                self.stdout.write(f"[-] Offre d'emploi '{offer.title}' désactivée : URL inaccessible ou renvoyant 404 ({offer.url_apply})")

        # 2. Vérification des bourses d'études Canada
        scholarships = CanadaScholarship.objects.filter(is_active=True)
        self.stdout.write(f"Vérification de {scholarships.count()} bourses d'études active(s)...")
        deactivated_scholarships = 0
        for sc in scholarships:
            deadline_date = _parse_deadline(sc.deadline)
            if deadline_date and deadline_date < timezone.localdate():
                sc.is_active = False
                sc.save(update_fields=["is_active"])
                deactivated_scholarships += 1
                self.stdout.write(f"[-] Bourse '{sc.title}' désactivée : Date limite dépassée ({sc.deadline})")
                continue

            if not _is_url_active(sc.url_apply):
                sc.is_active = False
                sc.save(update_fields=["is_active"])
                deactivated_scholarships += 1
                self.stdout.write(f"[-] Bourse '{sc.title}' désactivée : URL inaccessible ou renvoyant 404 ({sc.url_apply})")

        # 3. Vérification des opportunités de visa visiteur Canada
        opportunities = CanadaVisitorOpportunity.objects.filter(is_active=True)
        self.stdout.write(f"Vérification de {opportunities.count()} opportunités active(s)...")
        deactivated_opps = 0
        for opp in opportunities:
            deadline_date = _parse_deadline(opp.deadline)
            if deadline_date and deadline_date < timezone.localdate():
                opp.is_active = False
                opp.save(update_fields=["is_active"])
                deactivated_opps += 1
                self.stdout.write(f"[-] Opportunité '{opp.title}' désactivée : Date limite dépassée ({opp.deadline})")
                continue

            if not _is_url_active(opp.url_apply):
                opp.is_active = False
                opp.save(update_fields=["is_active"])
                deactivated_opps += 1
                self.stdout.write(f"[-] Opportunité '{opp.title}' désactivée : URL inaccessible ou renvoyant 404 ({opp.url_apply})")

        # 4. Vérification des actualités/sources Canada
        news_items = CanadaNews.objects.filter(is_active=True)
        self.stdout.write(f"Vérification de {news_items.count()} actualités active(s)...")
        deactivated_news = 0
        for item in news_items:
            if not _is_url_active(item.url_source):
                item.is_active = False
                item.save(update_fields=["is_active"])
                deactivated_news += 1
                self.stdout.write(f"[-] Actualité '{item.title}' désactivée : URL de source inaccessible ({item.url_source})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Vérification terminée avec succès !\n"
                f"Offres d'emploi désactivées : {deactivated_jobs}\n"
                f"Bourses d'études désactivées : {deactivated_scholarships}\n"
                f"Opportunités touristiques désactivées : {deactivated_opps}\n"
                f"Actualités désactivées : {deactivated_news}"
            )
        )
