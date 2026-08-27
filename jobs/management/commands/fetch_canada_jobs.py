from __future__ import annotations

import hashlib
import json
import logging
import re
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, search_duckduckgo
from ai_engine.services.openai_adapter import call_openai, call_openai_json
from jobs.models import CanadaJobOffer

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


class Command(BaseCommand):
    help = "Cherche et importe les nouvelles offres d'emploi d'employeurs canadiens qui recrutent à l'étranger (EIMT/LMIA)"

    def handle(self, *args, **options):
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
                self.stdout.write("OpenAI actif. Recherche web via DuckDuckGo puis extraction IA...")
                ddg_results = search_duckduckgo("site:jobbank.gc.ca OR site:guichetemplois.gc.ca EIMT LMIA Canada foreign workers jobs", max_results=12)
                if not ddg_results:
                    self.stderr.write("Aucun résultat DuckDuckGo exploitable.")
                    return
                search_results = call_openai(
                    "Tu es un analyste emploi Canada. Analyse les résultats web fournis et conserve uniquement les offres Job Bank/Guichet Emplois utiles.",
                    f"{search_prompt}\n\nRésultats web:\n{ddg_results}",
                    temperature=0.2,
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
                title = job.get("title", "").strip()
                company = job.get("company", "").strip()
                city = job.get("city", "").strip()
                url_apply = job.get("url_apply", "").strip()
                lmia_status = job.get("lmia_status", "Non précisé").strip()

                if not title or not company or not url_apply:
                    self.stdout.write(f"Offre ignorée car champs obligatoires manquants : {job}")
                    continue

                # Vérification stricte du domaine de l'URL pour n'accepter que Guichet Emplois (Canada Job Bank)
                url_lower = url_apply.lower()
                if not ("guichetemplois.gc.ca" in url_lower or "jobbank.gc.ca" in url_lower):
                    self.stdout.write(f"Offre ignorée car l'URL ne provient pas de Guichet Emplois : {url_apply}")
                    continue

                # Check if the url_apply is active (returns 200/300 status code, not 404 or 410)
                if not _is_url_active(url_apply):
                    self.stdout.write(f"Offre ignorée car le lien url_apply est inactif ou renvoie un 404 : {url_apply}")
                    continue

                # Filet de sécurité supplémentaire : on n'affiche que les offres
                # explicitement ouvertes aux candidats étrangers.
                allowed_status = (
                    "eimt" in lmia_status.lower()
                    or "lmia" in lmia_status.lower()
                    or "francophone" in lmia_status.lower()
                    or "exempt" in lmia_status.lower()
                )
                if not allowed_status:
                    self.stdout.write(f"Offre ignorée car statut LMIA '{lmia_status}' non autorisé : {title} ({company})")
                    continue

                ref_nr = _stable_ref_nr(company, title, city)

                offer, created = CanadaJobOffer.objects.update_or_create(
                    ref_nr=ref_nr,
                    defaults={
                        "title": title,
                        "company": company,
                        "city": city,
                        "province": job.get("province", "").strip(),
                        "lmia_status": lmia_status,
                        "salary": job.get("salary", "Non précisé").strip(),
                        "deadline": job.get("deadline", "Non précisé").strip(),
                        "description": job.get("description", "").strip(),
                        "url_apply": url_apply,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Supprimer définitivement les offres dont la date limite est dépassée
            expired_count = 0
            for offer in CanadaJobOffer.objects.filter(is_active=True).exclude(deadline=""):
                deadline_date = _parse_deadline(offer.deadline)
                if deadline_date and deadline_date < timezone.localdate():
                    offer.delete()
                    expired_count += 1

            # Supprimer définitivement les offres non revues depuis 14 jours
            # (l'IA ne les retrouve plus sur le web => probablement pourvues/retirées)
            cutoff = timezone.now() - timezone.timedelta(days=14)
            stale_qs = CanadaJobOffer.objects.filter(last_seen__lt=cutoff)
            stale_count = stale_qs.count()
            stale_qs.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation terminée ! +{created_count} nouvelles offres, "
                    f"{updated_count} mises à jour, {expired_count} supprimées (date limite dépassée), "
                    f"{stale_count} supprimées (non revues depuis 14 jours)."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")
