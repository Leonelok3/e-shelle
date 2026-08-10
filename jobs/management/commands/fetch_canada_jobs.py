from __future__ import annotations

import hashlib
import json
import logging
import re
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
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


class Command(BaseCommand):
    help = "Cherche et importe les nouvelles offres d'emploi d'employeurs canadiens qui recrutent à l'étranger (EIMT/LMIA)"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation du client GenAI...")
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
            "Recherche sur le web (sur guichet-emplois.gc.ca, indeed.ca, workopolis.com, randstad.ca, jobillico.com, ou directement sur les sites carrières d'employeurs canadiens) des offres d'emploi réelles et récentes au Canada ouvertes aux candidats internationaux hors du Canada (recrutement international, EIMT / LMIA approuvé ou en cours, ou exemption Mobilité Francophone). Trouve des postes diversifiés dans l'agriculture, la santé, l'informatique, le transport, la construction ou la restauration. Liste au moins 8 offres d'emploi avec : le titre du poste, l'entreprise, la ville, la province, le statut de l'EIMT ou Mobilité Francophone, le salaire et l'URL source directe pour postuler.\n"
            "EXCLUDE expired, closed, or deactivated offers. Verify that the recruitment/job is active.\n"
            "Crucial: The URL ('url_apply') MUST be the exact, specific direct web page link of the job posting (e.g. Indeed job link or Job Bank link). Do NOT use generic parent URLs or guess/hallucinate URLs. If you cannot find the direct, exact, working URL for the job, DO NOT include that job."
        )

        try:
            response_search = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                )
            )
            search_results = response_search.text
            self.stdout.write(f"Résultats de recherche récupérés (taille={len(search_results)}). Conversion en JSON...")

            # Pass 2: Controlled JSON extraction
            json_prompt = (
                "Analyse les offres d'emploi récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "N'inclus QUE des offres accessibles à des candidats situés à l'étranger (EIMT approuvé, EIMT en cours, "
                "Mobilité Francophone ou exemption explicite). Exclus toute offre destinée uniquement aux candidats déjà "
                "au Canada. Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- title: le titre de l'emploi en français (ex: Ouvrier Agricole)\n"
                "- company: le nom de l'entreprise\n"
                "- city: la ville canadienne\n"
                "- province: la province (ex: Québec, Alberta, Ontario)\n"
                "- lmia_status: le statut réglementaire exact (obligatoirement l'une de ces valeurs exactes : 'EIMT approuvé', 'EIMT en cours', 'Mobilité Francophone', 'Exempté' ou 'Non précisé')\n"
                "- salary: le salaire (ex: 20 $/heure) ou 'Non précisé'\n"
                "- deadline: la date limite de candidature (ex: 31 mars 2026) ou 'Non précisé'\n"
                "- description: une explication concise (2-3 sentences) en français du rôle et pourquoi c'est idéal pour un candidat étranger\n"
                "- url_apply: le vrai lien web direct pour postuler\n\n"
                f"Offres brutes :\n{search_results}"
            )

            response_json = client.models.generate_content(
                model="gemini-2.5-flash",
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

                # Check if the url_apply is active (returns 200/300 status code, not 404 or 410)
                if not _is_url_active(url_apply):
                    self.stdout.write(f"Offre ignorée car le lien url_apply est inactif ou renvoie un 404 : {url_apply}")
                    continue

                # Filet de sécurité supplémentaire : on n'affiche que les offres
                # explicitement ouvertes aux candidats étrangers.
                allowed_status = (
                    "eimt" in lmia_status.lower()
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
