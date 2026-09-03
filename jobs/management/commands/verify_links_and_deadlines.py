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
        
    # Liste de domaines de confiance pour tolérer les erreurs de connexion temporaires (timeouts/WAF)
    trusted_domains = [
        "gc.ca", "canada.ca", "quebec.ca", "mcgill.ca", "ubc.ca", 
        "umontreal.ca", "ulaval.ca", "uottawa.ca", "alberta.ca",
        "utoronto.ca", "jobbank.gc.ca", "guichet-emplois.gc.ca",
        "indeed.ca", "workopolis.com", "randstad.ca", "jobillico.com",
        "monster.ca", "emploisquebec.gouv.qc.ca", "linkedin.com"
    ]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # On utilise GET avec stream=True pour pouvoir suivre les redirections et analyser l'URL finale
        resp = requests.get(url, headers=headers, timeout=5, allow_redirects=True, stream=True)
        
        # 1. Vérification du code d'erreur HTTP (ex: 404 de Google redirect)
        if resp.status_code in [404, 410]:
            return False
            
        # 2. Détection de redirection vers une page d'expiration (Job Bank redirect)
        final_url = resp.url.lower()
        if "jobpostingexpired" in final_url or "job-expired" in final_url:
            return False
            
        # 3. Validation pour les codes valides ou d'accès restreint
        if resp.status_code < 400 or resp.status_code in [401, 403, 503]:
            return True
            
        return resp.status_code < 400
    except Exception:
        # En cas d'erreur de connexion, on tolère uniquement si le domaine est de confiance
        if any(domain in url.lower() for domain in trusted_domains):
            return True
        return False


def _is_official_jobbank_url(url: str) -> bool:
    url = (url or "").lower()
    return "jobbank.gc.ca/jobsearch/jobposting/" in url or "guichetemplois.gc.ca/rechercheemplois/offredemploi/" in url


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
                if _is_official_jobbank_url(offer.url_apply):
                    self.stdout.write(
                        f"[!] Offre d'emploi officielle conservée malgré vérification HTTP impossible : {offer.url_apply}"
                    )
                    continue
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
