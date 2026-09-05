from __future__ import annotations

import hashlib
import json
import logging
import re
import requests
from html import unescape
from urllib.parse import urlencode, urljoin
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from ai_engine.services.openai_adapter import call_openai, call_openai_json, call_openai_web, search_duckduckgo
from jobs.models import CanadaJobOffer

logger = logging.getLogger(__name__)

JOBBANK_TFW_SEARCH_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"
JOBBANK_DETAIL_URL = "https://www.jobbank.gc.ca/jobsearch/jobposting/{job_number}"
GUICHET_SEARCH_URL = "https://www.guichetemplois.gc.ca/jobsearch/rechercheemplois"
GUICHET_EIMT_FILTERS = (
    ("101020", "EIMT approuvée"),
    ("101010", "EIMT demandée"),
)
PROVINCE_LABELS = {
    "AB": "Alberta",
    "BC": "Colombie-Britannique",
    "MB": "Manitoba",
    "NB": "Nouveau-Brunswick",
    "NL": "Terre-Neuve-et-Labrador",
    "NS": "Nouvelle-Écosse",
    "NT": "Territoires du Nord-Ouest",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Île-du-Prince-Édouard",
    "QC": "Québec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

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


def _stable_ref_nr(company: str, title: str, city: str) -> str:
    """
    Identifiant stable basé sur (company, title, city) plutôt que sur l'ID
    fourni par l'IA (qui change d'un run à l'autre, ex: 'ca-job-1' à chaque
    exécution) — indispensable pour que update_or_create() reconnaisse une
    offre déjà vue la veille au lieu de créer un doublon chaque matin.
    """
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{city.strip().lower()}"
    return "ca-job-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _parse_deadline(deadline_str: str):
    """
    Essaie de convertir une date limite en français (ex: '31 mars 2026') en objet date.
    Retourne None si la date est absente, non précisée ou non interprétable.
    """
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
    except (ValueError, OverflowError, TypeError):
        return None


def _fetch_guichet_detail_metadata(url: str) -> dict:
    if "guichetemplois.gc.ca" not in (url or "").lower():
        return {}
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-CA,fr;q=0.9,en-CA;q=0.7,en;q=0.6",
        "User-Agent": "Mozilla/5.0 (compatible; EShelleCanadaJobs/1.0; +https://e-shelle.com)",
    }
    response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    if response.status_code in [404, 410] or "jobpostingexpired" in response.url.lower():
        return {"is_active": False}

    text = _clean_page_text(response.text)
    deadline = "Non précisé"
    deadline_match = re.search(r"Publiée jusqu[’']au\s+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if deadline_match:
        deadline = deadline_match.group(1)

    posted_label = ""
    posted_match = re.search(r"Publiée le\s+(.+?)\s+par", text, re.IGNORECASE)
    if posted_match:
        posted_label = posted_match.group(1).strip()

    return {
        "is_active": True,
        "deadline": deadline,
        "source_posted_date": _parse_deadline(posted_label),
    }


def _generate_content_with_retry(client, model, contents, config, retries=4, initial_delay=5):
    import time
    for i in range(retries):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and i < retries - 1:
                sleep_time = initial_delay * (2 ** i)
                time.sleep(sleep_time)
                continue
            raise e


def _clean_page_text(raw_html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_fragment(raw_html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+class="[^"]*\bwb-inv\b[^"]*"[^>]*>.*?</[^>]+>', " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_guichet_page(page: int, fskl: str) -> str:
    params = {
        "page": page,
        "sort": "D",
        "fskl": fskl,
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-CA,fr;q=0.9,en-CA;q=0.7,en;q=0.6",
        "User-Agent": "Mozilla/5.0 (compatible; EShelleCanadaJobs/1.0; +https://e-shelle.com)",
    }
    response = requests.get(f"{GUICHET_SEARCH_URL}?{urlencode(params)}", headers=headers, timeout=20)
    response.raise_for_status()
    return response.text


def _extract_article_field(article: str, css_class: str) -> str:
    match = re.search(
        rf'<(?P<tag>[a-z0-9]+)[^>]+class="{re.escape(css_class)}"[^>]*>(.*?)</(?P=tag)>',
        article,
        re.DOTALL | re.IGNORECASE,
    )
    return _clean_fragment(match.group(2)) if match else ""


def _parse_guichet_html(html: str, lmia_status: str) -> list[dict]:
    jobs: list[dict] = []
    seen_urls = set()
    article_pattern = re.compile(
        r'<article[^>]+class="[^"]*action-buttons[^"]*"[^>]*>\s*'
        r'<a\s+href="(?P<href>[^"]+)"[^>]*class="[^"]*resultJobItem[^"]*"[^>]*>'
        r'(?P<body>.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in article_pattern.finditer(html):
        href = unescape(match.group("href")).split(";jsessionid=")[0]
        body = match.group("body")
        url_apply = urljoin("https://www.guichetemplois.gc.ca", href)
        if url_apply in seen_urls:
            continue
        seen_urls.add(url_apply)

        title = _extract_article_field(body, "noctitle")
        company = _extract_article_field(body, "business")
        location_raw = _extract_article_field(body, "location")
        salary = _extract_article_field(body, "salary").replace("Salaire :", "").strip() or "Non précisé"
        posted_date = _extract_article_field(body, "date")

        city = location_raw
        province = ""
        loc_match = re.search(r"(.+?)\s*\(([A-Z]{2})\)", location_raw)
        if loc_match:
            city = loc_match.group(1).strip()
            province = PROVINCE_LABELS.get(loc_match.group(2), loc_match.group(2))

        if not title or not company or not url_apply:
            continue

        jobs.append(
            {
                "title": title,
                "company": company,
                "city": city,
                "province": province,
                "lmia_status": lmia_status,
                "salary": salary,
                "deadline": "Non précisé",
                "description": (
                    f"Offre publiée sur le Guichet-Emplois avec {lmia_status}. "
                    f"Le poste de {title} chez {company} est destiné aux candidats qui veulent postuler "
                    "auprès d'un employeur canadien qui recrute des travailleurs étrangers."
                ),
                "url_apply": url_apply,
                "posted_date": posted_date,
            }
        )
    return jobs


def _fetch_jobbank_page(page: int) -> str:
    params = {
        "fsrc": "32",       # Temporary Foreign Workers
        "sort": "D",        # date posted first
        "page": page,
        "wbdisable": "true",
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-CA,en;q=0.9,fr-CA;q=0.8,fr;q=0.7",
        "User-Agent": "Mozilla/5.0 (compatible; EShelleCanadaJobs/1.0; +https://e-shelle.com)",
    }
    response = requests.get(f"{JOBBANK_TFW_SEARCH_URL}?{urlencode(params)}", headers=headers, timeout=20)
    response.raise_for_status()
    return _clean_page_text(response.text)


def _parse_jobbank_search_text(text: str) -> list[dict]:
    pattern = re.compile(
        r"(?P<lmia>LMIA requested|Approved LMIA)?\s*Job Bank\s+"
        r"(?P<title>.+?)\s+"
        r"(?P<posted>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2})\s+"
        r"(?P<company>.+?)\s+Location\s+"
        r"(?P<city>.+?)\s+\((?P<province>[A-Z]{2})\)\s+"
        r"Salary\s+(?P<salary>.+?)\s+Job Bank Job number:\s*(?P<job_number>\d+)",
        re.IGNORECASE,
    )
    results = []
    seen_numbers = set()
    for match in pattern.finditer(text):
        data = {key: (value or "").strip() for key, value in match.groupdict().items()}
        job_number = data["job_number"]
        if job_number in seen_numbers:
            continue
        seen_numbers.add(job_number)
        province_code = data["province"].upper()
        lmia_text = data.get("lmia") or "LMIA requested"
        results.append(
            {
                "title": data["title"].strip(" -"),
                "company": data["company"].strip(" -"),
                "city": data["city"].strip(" -"),
                "province": PROVINCE_LABELS.get(province_code, province_code),
                "lmia_status": "EIMT approuvée" if "approved" in lmia_text.lower() else "EIMT demandée",
                "salary": data["salary"].strip(" -") or "Non précisé",
                "deadline": "Non précisé",
                "description": (
                    f"Cette offre Job Bank est publiée dans le volet Travailleurs étrangers temporaires. "
                    f"Le poste de {data['title']} chez {data['company']} peut intéresser un candidat international "
                    "qui prépare un projet professionnel au Canada avec EIMT/LMIA."
                ),
                "url_apply": JOBBANK_DETAIL_URL.format(job_number=job_number),
            }
        )
    return results


def _clean_jobbank_title(value: str) -> str:
    title = (value or "").strip()
    markers = [
        "LMIA requested Job Bank ",
        "Approved LMIA Job Bank ",
        "Job Bank ",
    ]
    for marker in markers:
        if marker in title:
            title = title.split(marker)[-1].strip()
    return re.sub(r"\s+", " ", title).strip(" -")


def _import_job_offer(job: dict, *, verify_url: bool = True) -> tuple[bool, bool, str]:
    def limit(value: str, max_length: int) -> str:
        return (value or "").strip()[:max_length]

    title = limit(_clean_jobbank_title(job.get("title") or ""), 300)
    company = limit(job.get("company") or "", 200)
    city = limit(job.get("city") or "", 100)
    province = limit(job.get("province") or "", 100)
    url_apply = limit(job.get("url_apply") or "", 500)
    lmia_status = limit(job.get("lmia_status") or "Non précisé", 50)
    salary = limit(job.get("salary") or "Non précisé", 100)
    deadline = limit(job.get("deadline") or "Non précisé", 100)

    if not title or not company or not url_apply:
        return False, False, f"champs obligatoires manquants : {job}"

    url_lower = url_apply.lower()
    if not ("guichetemplois.gc.ca" in url_lower or "jobbank.gc.ca" in url_lower):
        return False, False, f"URL non officielle : {url_apply}"

    from jobs.canada_validation import check_offer, parse_deadline
    status, reason, source_deadline = check_offer(url_apply)
    if status != "active":
        return False, False, f"source non valide : {reason} ({url_apply})"
    if source_deadline:
        deadline = source_deadline.isoformat()
    deadline_date = parse_deadline(deadline)
    if deadline_date and deadline_date < timezone.localdate():
        return False, False, f"date limite dépassée : {deadline}"
    source_posted_date = _parse_deadline(job.get("posted_date") or "")
    if "guichetemplois.gc.ca" in url_lower:
        try:
            metadata = _fetch_guichet_detail_metadata(url_apply)
            source_posted_date = metadata.get("source_posted_date") or source_posted_date
        except requests.RequestException:
            pass

    allowed_status = (
        "eimt" in lmia_status.lower()
        or "lmia" in lmia_status.lower()
        or "francophone" in lmia_status.lower()
        or "exempt" in lmia_status.lower()
    )
    if not allowed_status:
        return False, False, f"statut LMIA non autorisé : {lmia_status} - {title} ({company})"

    ref_nr = _stable_ref_nr(company, title, city)
    try:
        _, created = CanadaJobOffer.objects.update_or_create(
            ref_nr=ref_nr,
            defaults={
                "title": title,
                "company": company,
                "city": city,
                "province": province,
                "lmia_status": lmia_status,
                "salary": salary,
                "deadline": deadline,
                **({"source_posted_date": source_posted_date} if source_posted_date else {}),
                "description": (job.get("description") or "").strip(),
                "url_apply": url_apply,
                "is_active": True,
            },
        )
    except Exception as exc:
        return False, False, f"erreur base de données : {exc} - {title} ({company})"
    return created, not created, ""


class Command(BaseCommand):
    help = "Cherche et importe les nouvelles offres d'emploi d'employeurs canadiens qui recrutent à l'étranger (EIMT/LMIA)"

    def add_arguments(self, parser):
        parser.add_argument("--target", type=int, default=48, help="Nombre cible minimal d'offres actives à garder.")
        parser.add_argument("--pages", type=int, default=5, help="Nombre de pages Job Bank TFW à parcourir.")
        parser.add_argument("--skip-ai", action="store_true", help="Importer seulement depuis Job Bank, sans complément IA.")

    def handle(self, *args, **options):
        target = max(1, options["target"])
        pages = max(1, options["pages"])
        skip_ai = options["skip_ai"]

        direct_created = 0
        direct_updated = 0
        direct_seen = 0
        self.stdout.write("Lecture directe Guichet-Emplois - EIMT approuvée et demandée...")
        for fskl, lmia_status in GUICHET_EIMT_FILTERS:
            for page in range(1, pages + 1):
                try:
                    page_html = _fetch_guichet_page(page, fskl)
                    page_jobs = _parse_guichet_html(page_html, lmia_status)
                    self.stdout.write(
                        f"Page Guichet-Emplois {lmia_status} {page}: {len(page_jobs)} offre(s) détectée(s)."
                    )
                    for job in page_jobs:
                        created, updated, reason = _import_job_offer(job, verify_url=True)
                        if reason:
                            self.stdout.write(f"Offre ignorée: {reason}")
                            continue
                        direct_seen += 1
                        if created:
                            direct_created += 1
                        elif updated:
                            direct_updated += 1
                except Exception as direct_error:
                    logger.warning("Import direct Guichet-Emplois %s page %s échoué: %s", lmia_status, page, direct_error)
                    self.stdout.write(f"Page Guichet-Emplois {lmia_status} {page}: erreur {direct_error}")

        active_after_direct = CanadaJobOffer.objects.filter(is_active=True).count()
        self.stdout.write(
            f"Import direct Guichet-Emplois EIMT: +{direct_created}, {direct_updated} mises à jour, "
            f"{direct_seen} valides, {active_after_direct} actives."
        )
        if skip_ai or active_after_direct >= target:
            self._cleanup_old_offers()
            self.stdout.write(self.style.SUCCESS("Importation Canada terminée depuis Guichet-Emplois."))
            return

        use_openai = bool(getattr(settings, "OPENAI_API_KEY", ""))
        self.stdout.write("Initialisation du client GenAI...")
        client = None
        if not use_openai:
            client, err = get_vertex_client()
            if err or not client:
                self.stdout.write(f"Vertex AI non disponible ou erreur : {err}. Tentative avec Gemini Developer API...")
                from e_shelle_ai.services.tools.google_media_generator import get_genai_studio_client
                client, err = get_genai_studio_client()

            if err or not client:
                self.stderr.write(f"Erreur d'initialisation du client GenAI : {err}")
                return

        self.stdout.write("Recherche globale des offres d'emploi Canada avec EIMT...")

        # Pass 1: Google Search Grounding to find actual job links and details
        search_prompt = (
            "Recherche des offres d'emploi réelles et récentes au Canada publiées sur le site officiel du gouvernement du Canada : Guichet Emplois (guichetemplois.gc.ca) ou Job Bank (jobbank.gc.ca) qui recrutent à l'étranger (EIMT/LMIA demandée ou approuvée).\n"
            "Liste au moins 8 offres d'emploi avec : le titre du poste, l'entreprise recruteuse, la ville, la province, le statut de l'EIMT/LMIA, le salaire et l'URL source directe exacte (ex: https://www.jobbank.gc.ca/jobsearch/jobposting/3646940)."
        )

        try:
            if use_openai:
                self.stdout.write("OpenAI actif. Recherche web OpenAI puis extraction IA...")
                try:
                    search_results = call_openai_web(
                        "Tu es un analyste emploi Canada. Utilise le web et privilégie les sources officielles Job Bank / Guichet Emplois.",
                        search_prompt,
                    )
                except Exception as web_error:
                    logger.warning("OpenAI web search indisponible: %s", web_error)
                    ddg_results = search_duckduckgo("site:jobbank.gc.ca jobposting LMIA Canada foreign workers", max_results=12)
                    if not ddg_results:
                        ddg_results = search_duckduckgo("site:guichetemplois.gc.ca offre emploi EIMT travailleurs étrangers Canada", max_results=12)
                    search_results = ddg_results or (
                        "Source officielle principale: https://www.jobbank.gc.ca/landing-tfw-international.xhtml\n"
                        "Cette page Job Bank regroupe les offres d'employeurs canadiens ayant obtenu ou demandé une LMIA/EIMT "
                        "et souhaitant recruter des travailleurs étrangers temporaires. Ne crée pas de fausses offres; "
                        "si tu ne peux pas identifier d'offres précises, retourne une liste JSON vide."
                    )
            else:
                try:
                    response_search = _generate_content_with_retry(
                        client=client,
                        model="gemini-3.6-flash",
                        contents=search_prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=0.2,
                        )
                    )
                    search_results = response_search.text
                except Exception as se:
                    err_str = str(se).lower()
                    if "quota" not in err_str and "429" not in err_str and "billing" not in err_str and "limit" not in err_str and "permission" not in err_str:
                        raise
                    self.stdout.write("Google Search Grounding non disponible (quota/billing/limite). Bascule sur DuckDuckGo...")
                    ddg_results = search_duckduckgo("site:jobbank.gc.ca EIMT LMIA recruiting foreign")
                    if not ddg_results:
                        raise
                    fallback_prompt = (
                        f"Voici les résultats de recherche web pour les offres d'emploi Canada EIMT :\n\n{ddg_results}\n\n"
                        "Analyse ces résultats et liste au moins 8 offres d'emploi réelles et récentes avec : "
                        "le titre du poste, l'entreprise recruteuse, la ville, la province, le statut de l'EIMT/LMIA (approuvé, en cours, etc.), le salaire et l'URL source directe exacte."
                    )
                    response_search = _generate_content_with_retry(
                        client=client,
                        model="gemini-3.6-flash",
                        contents=fallback_prompt,
                        config=types.GenerateContentConfig(temperature=0.2)
                    )
                    search_results = response_search.text

            self.stdout.write(f"Résultats de recherche récupérés (taille={len(search_results)}). Conversion en JSON...")

            # Pass 2: Controlled JSON extraction
            json_prompt = (
                "Analyse les offres d'emploi récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "RÈGLES CRITIQUES : Exclus strictement toute offre dont l'URL 'url_apply' ne provient pas de guichetemplois.gc.ca ou jobbank.gc.ca.\n"
                "N'inclus QUE des offres accessibles à des candidats situés à l'étranger (EIMT approuvé, EIMT en cours, EIMT demandée, "
                "Mobilité Francophone ou exemption explicite). Exclus toute offre destinée uniquement aux candidats déjà "
                "au Canada. Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- title: le titre de l'emploi en français (ex: Ouvrier Agricole)\n"
                "- company: le nom de l'entreprise\n"
                "- city: la ville canadienne\n"
                "- province: la province (ex: Québec, Alberta, Ontario)\n"
                "- lmia_status: le statut réglementaire (valeurs typiques : 'EIMT approuvé', 'EIMT en cours', 'EIMT demandée', 'Mobilité Francophone', 'Exempté' ou 'Non précisé')\n"
                "- salary: le salaire (ex: 20 $/heure) ou 'Non précisé'\n"
                "- deadline: la date limite de candidature (ex: 31 mars 2026) ou 'Non précisé'\n"
                "- description: une explication concise (2-3 sentences) en français du rôle et pourquoi c'est idéal pour un candidat étranger\n"
                "- url_apply: le vrai lien web direct sur Guichet Emplois (commençant obligatoirement par https://www.guichetemplois.gc.ca/ ou https://www.jobbank.gc.ca/)\n\n"
                f"Offres brutes :\n{search_results}"
            )

            if use_openai:
                jobs_list = call_openai_json(
                    "Tu es un extracteur JSON strict. Retourne uniquement une liste JSON valide, sans markdown.",
                    json_prompt,
                    temperature=0.1,
                )
                self.stdout.write(f"JSON reçu de l'IA (éléments={len(jobs_list) if isinstance(jobs_list, list) else 'non-liste'})")
            else:
                response_json = _generate_content_with_retry(
                    client=client,
                    model="gemini-3.6-flash",
                    contents=json_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    )
                )

                self.stdout.write(f"JSON brut reçu de l'IA (taille={len(response_json.text)})")

                try:
                    jobs_list = json.loads(response_json.text)
                except json.JSONDecodeError as je:
                    self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                    return

            if not isinstance(jobs_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste d'offres.")
                return

            self.stdout.write(f"Nombre d'offres extraites par l'IA : {len(jobs_list)}")

            created_count = 0
            updated_count = 0

            for job in jobs_list:
                created, updated, reason = _import_job_offer(job)
                if reason:
                    self.stdout.write(f"Offre ignorée car {reason}")
                    continue
                if created:
                    created_count += 1
                elif updated:
                    updated_count += 1

            expired_count, stale_count = self._cleanup_old_offers()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation terminée ! Job Bank direct +{direct_created}/{direct_updated}, "
                    f"IA +{created_count}/{updated_count}, {expired_count} supprimées (date limite dépassée), "
                    f"{stale_count} supprimées (non revues depuis 14 jours)."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")

    def _cleanup_old_offers(self) -> tuple[int, int]:
        from django.core.management import call_command
        call_command("clean_expired_canada_jobs", stdout=self.stdout)
        return 0, 0
