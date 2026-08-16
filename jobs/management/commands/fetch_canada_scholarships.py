from __future__ import annotations

import hashlib
import json
import logging
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from jobs.models import CanadaScholarship

logger = logging.getLogger(__name__)


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


def _stable_ref_nr(provider: str, title: str) -> str:
    """
    Identifiant stable basé sur (provider, title) plutôt que sur l'ID
    fourni par l'IA (qui change d'un run à l'autre, ex: 'ca-scholarship-1'
    à chaque exécution) — indispensable pour que update_or_create()
    reconnaisse une bourse déjà vue la veille au lieu de l'écraser
    avec une autre bourse portant le même numéro générique.
    """
    raw = f"{provider.strip().lower()}|{title.strip().lower()}"
    return "ca-scholarship-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

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
    help = "Cherche et importe par IA les bourses d'études au Canada actives pour les étudiants internationaux"

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

        self.stdout.write("Recherche globale des bourses d'études au Canada...")
        
        # Pass 1: Google Search Grounding to find actual active scholarships
        search_prompt = (
            "Recherche sur le web des bourses d'études réelles et officielles actives ou annoncées pour les étudiants internationaux au Canada pour 2026/2027. Cible en priorité les sites officiels d'universités canadiennes (umontreal.ca, uottawa.ca, ulaval.ca, mcgill.ca, etc.) ou gouvernementaux (canada.ca, educanada.ca). Liste au moins 6 bourses valides avec : le titre de la bourse, l'université ou organisme émetteur, la valeur, les critères d'éligibilité, la date limite de candidature et le lien URL officiel direct pour postuler.\n"
            "EXCLUDE expired, closed, or deactivated offers. Verify that the scholarship is active.\n"
            "Crucial: The URL ('url_apply') MUST be the exact, specific direct web page link of the scholarship offer. Do NOT use generic parent URLs (like 'https://www.ulaval.ca') or guess/hallucinate URLs. If you cannot find the direct, exact, working URL for the scholarship, DO NOT include that scholarship."
        )

        try:
            response_search = _generate_content_with_retry(
                client=client,
                model="gemini-2.5-flash",
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                )
            )
            search_results = response_search.text
            self.stdout.write(f"Résultats de recherche récupérés (taille={len(search_results)}). Extraction JSON...")

            # Pass 2: Controlled JSON extraction
            json_prompt = (
                "Analyse les bourses d'études canadiennes récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- title: le nom officiel de la bourse en français (ex: Bourse d'exemption de l'Université d'Ottawa)\n"
                "- provider: le nom de l'université ou de l'organisme (ex: Université d'Ottawa)\n"
                "- amount: la valeur de la bourse (ex: Exemption partielle, 10 000 $/an, Entière)\n"
                "- eligibility: les critères clés d'éligibilité simplifiés en français\n"
                "- deadline: la date limite (ex: 31 Mars 2026) ou 'Non précisé'\n"
                "- description: une brève description (2-3 phrases) expliquant comment postuler et le public cible\n"
                "- url_apply: le vrai lien web officiel pour soumettre son dossier de bourse\n\n"
                f"Bourses brutes :\n{search_results}"
            )

            response_json = _generate_content_with_retry(
                client=client,
                model="gemini-2.5-flash",
                contents=json_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )

            self.stdout.write(f"JSON brut reçu de l'IA (taille={len(response_json.text)})")

            try:
                scholarships_list = json.loads(response_json.text)
            except json.JSONDecodeError as je:
                self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                return

            if not isinstance(scholarships_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste de bourses.")
                return

            self.stdout.write(f"Nombre de bourses extraites par l'IA : {len(scholarships_list)}")

            created_count = 0
            updated_count = 0

            for sc in scholarships_list:
                title = sc.get("title", "").strip()
                provider = sc.get("provider", "").strip()
                url_apply = sc.get("url_apply", "").strip()

                if not title or not provider or not url_apply:
                    continue

                # Check if the url_apply is active (returns 200/300 status code, not 404 or 410)
                if not _is_url_active(url_apply):
                    self.stdout.write(f"Bourse ignorée car le lien url_apply est inactif ou renvoie un 404 : {url_apply}")
                    continue

                ref_nr = _stable_ref_nr(provider, title)

                offer, created = CanadaScholarship.objects.update_or_create(
                    ref_nr=ref_nr,
                    defaults={
                        "title": title,
                        "provider": provider,
                        "amount": sc.get("amount", "Non précisé").strip(),
                        "eligibility": sc.get("eligibility", "").strip(),
                        "deadline": sc.get("deadline", "Non précisé").strip(),
                        "description": sc.get("description", "").strip(),
                        "url_apply": url_apply,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Désactiver les anciennes bourses après 30 jours
            cutoff = timezone.now() - timezone.timedelta(days=30)
            deactivated_count = CanadaScholarship.objects.filter(
                last_seen__lt=cutoff, is_active=True
            ).update(is_active=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation des bourses terminée ! +{created_count} nouvelles bourses, "
                    f"{updated_count} mises à jour, {deactivated_count} désactivées."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")
