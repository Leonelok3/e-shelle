"""
Taches Celery pour germany_opportunities.
- fetch_ausbildung_offers : quotidien (6h), appelle l'API Bundesagentur
- enrich_offers_with_ai : enrichit les nouvelles offres avec un resume IA en francais
- fetch_daad_scholarships : hebdomadaire, scrape les bourses DAAD Afrique
"""
import logging
import requests
from datetime import date

from celery import shared_task
from django.utils import timezone

log = logging.getLogger(__name__)

# ── Constantes API Bundesagentur ──────────────────────────────────────────────
BA_BASE_URL  = "https://rest.arbeitsagentur.de/infosysbub/absuche/pc/v1/ausbildungssuche"
BA_API_KEY   = "infosysbub-absuche"

# Secteurs prioritaires pour le public africain en quete d'Ausbildung
SECTORS_QUERY = [
    "Gesundheit",
    "Pflege",
    "Informatik",
    "Elektrotechnik",
    "Mechatronik",
    "Bau",
    "Hotel",
    "Logistik",
    "Kaufmann",
    "Erziehung",
]

SECTOR_MAP = {
    "gesundheit": ["Gesundheit", "Pflege", "Medizin"],
    "it":         ["Informatik", "IT", "Software", "Daten"],
    "elektro":    ["Elektro", "Mechatronik", "Metall"],
    "bau":        ["Bau", "Handwerk", "Sanitaer", "Holz"],
    "hotellerie": ["Hotel", "Gastro", "Koch", "Restaurant"],
    "logistik":   ["Logistik", "Lager", "Transport"],
    "kaufmann":   ["Kaufmann", "Buero", "Verwaltung"],
    "soziales":   ["Erzieher", "Sozial", "Kinder"],
}


def _guess_sector(title: str) -> str:
    title_lower = title.lower()
    for sector, keywords in SECTOR_MAP.items():
        if any(k.lower() in title_lower for k in keywords):
            return sector
    return "andere"


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def fetch_ausbildung_offers(self):
    """
    Tache Celery quotidienne : recupere les offres Ausbildung depuis l'API
    officielle de la Bundesagentur fuer Arbeit et les stocke en base.
    Programmee via django-celery-beat.
    """
    from .models import AusbildungOffer

    headers = {
        "X-API-Key": BA_API_KEY,
        "Accept": "application/json",
        "User-Agent": "EShelle-Platform/1.0 (contact@e-shelle.com)",
    }

    created_count = 0
    updated_count = 0
    errors = 0
    seen_refs = set()

    for keyword in SECTORS_QUERY:
        params = {
            "suchbegriffe": keyword,
            "angebotsart":  4,            # 4 = Ausbildung
            "page":         0,
            "size":         50,
        }
        try:
            resp = requests.get(BA_BASE_URL, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                offers = data.get("ausbildungsangebote", []) or data.get("stellenangebote", []) or []
                for item in offers:
                    ref_nr = item.get("refnr") or item.get("referenznummer", "")
                    if not ref_nr or ref_nr in seen_refs:
                        continue
                    seen_refs.add(ref_nr)

                    title   = item.get("titel", "")
                    company = (item.get("arbeitgeber") or {}).get("name", "")
                    ort     = (item.get("arbeitsort") or {})
                    city    = ort.get("ort", "")
                    plz     = ort.get("plz", "")
                    region  = ort.get("region", "")

                    # Date debut
                    beginn = item.get("ausbildungsbeginn") or item.get("eintrittsdatum")
                    start  = None
                    if beginn:
                        try:
                            from datetime import datetime
                            start = datetime.strptime(beginn[:10], "%Y-%m-%d").date()
                        except Exception:
                            pass

                    url_apply = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}"

                    obj, created = AusbildungOffer.objects.update_or_create(
                        ref_nr=ref_nr,
                        defaults={
                            "title":      title,
                            "company":    company,
                            "city":       city,
                            "postal_code": plz,
                            "region":     region,
                            "sector":     _guess_sector(title),
                            "start_date": start,
                            "url_apply":  url_apply,
                            "is_active":  True,
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            elif resp.status_code in (429, 503):
                # Rate limit — retry
                raise self.retry(countdown=600)
        except requests.RequestException as exc:
            log.warning(f"API BA error for keyword '{keyword}': {exc}")
            errors += 1

    # Desactiver les offres qui n'ont plus ete vues depuis 7 jours
    stale_cutoff = timezone.now() - timezone.timedelta(days=7)
    deactivated = AusbildungOffer.objects.filter(
        last_seen__lt=stale_cutoff, is_active=True
    ).update(is_active=False)

    log.info(
        f"fetch_ausbildung_offers: +{created_count} new, {updated_count} updated, "
        f"{deactivated} deactivated, {errors} errors"
    )
    return {
        "created": created_count, "updated": updated_count,
        "deactivated": deactivated, "errors": errors
    }


@shared_task
def enrich_offers_with_ai():
    """
    Enrichit les nouvelles offres Ausbildung sans resume IA avec un resume
    en francais genere par GPT-4o-mini, adapte au public africain.
    """
    from django.conf import settings
    from .models import AusbildungOffer

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        log.warning("enrich_offers_with_ai: OPENAI_API_KEY manquant")
        return

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        return

    # Traiter les 20 dernieres offres sans resume
    offers = AusbildungOffer.objects.filter(ai_summary_fr="", is_active=True).order_by("-fetched_at")[:20]

    SYSTEM = (
        "Tu es un conseiller en immigration en Allemagne pour des candidats africains "
        "(principalement Cameroun, Senegal, Cote d'Ivoire). "
        "Resumes cette offre d'Ausbildung en 3-4 phrases en francais simple et motivant. "
        "Mentionne : le metier, la ville, le salaire si connu, et pourquoi c'est une bonne opportunite "
        "pour quelqu'un venant d'Afrique. Ajoute 2 conseils de candidature specifiques a ce metier."
    )

    for offer in offers:
        user_msg = (
            f"Offre : {offer.title}\n"
            f"Entreprise : {offer.company}\n"
            f"Ville : {offer.city} ({offer.region})\n"
            f"Secteur : {offer.get_sector_display()}\n"
            f"Salaire : {offer.salary_display}\n"
            f"Description : {offer.description[:800]}"
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.5,
                max_tokens=400,
            )
            summary = resp.choices[0].message.content.strip()
            offer.ai_summary_fr = summary
            offer.save(update_fields=["ai_summary_fr"])
        except Exception as exc:
            log.warning(f"AI enrichment failed for offer {offer.ref_nr}: {exc}")

    log.info(f"enrich_offers_with_ai: {offers.count()} offres enrichies")
