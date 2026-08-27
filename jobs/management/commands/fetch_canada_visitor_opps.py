from __future__ import annotations

import json
import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, search_duckduckgo
from ai_engine.services.openai_adapter import call_openai, call_openai_json
from jobs.models import CanadaVisitorOpportunity

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
    help = "Cherche et importe par IA les opportunités de visa visiteur/tourisme au Canada (conférences, séminaires, certifications)"

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

        self.stdout.write("Recherche globale des opportunités de visa visiteur...")

        # Pass 1: Google Search Grounding to find actual upcoming conferences, summits & events in Canada
        search_prompt = (
            "Recherche sur le web des conférences internationales, sommets, séminaires ou formations professionnelles se déroulant au Canada en 2026/2027 qui acceptent les participants internationaux et facilitent l'obtention d'une lettre d'invitation pour visa visiteur. Trouve au moins 6 événements réels et récents avec : le nom de l'événement, l'organisateur, la date de l'événement, la ville, la province, la date limite d'inscription et le lien URL officiel pour s'inscrire.\n"
            "EXCLUDE expired, closed, or deactivated offers. Verify that the conference/event is active and accepting registrations.\n"
            "Crucial: The URL ('url_apply') MUST be the exact, specific direct web page link of the event registration or official announcement. Do NOT use generic parent URLs or guess/hallucinate URLs. If you cannot find the direct, exact, working URL for the event, DO NOT include that event."
        )

        try:
            if use_openai:
                self.stdout.write("OpenAI actif. Recherche web via DuckDuckGo puis extraction IA...")
                ddg_results = search_duckduckgo("Canada conferences seminars 2026 invitation letter visa international participants registration", max_results=12)
                if not ddg_results:
                    self.stderr.write("Aucun résultat DuckDuckGo exploitable.")
                    return
                search_results = call_openai(
                    "Tu es un analyste d'événements professionnels au Canada. Analyse les résultats web et conserve les événements plausibles pour visiteurs internationaux.",
                    f"{search_prompt}\n\nRésultats web:\n{ddg_results}",
                    temperature=0.2,
                )
            else:
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
            self.stdout.write(f"Résultats de recherche récupérés (taille={len(search_results)}). Extraction JSON...")

            # Pass 2: Controlled JSON extraction
            json_prompt = (
                "Analyse les événements et opportunités récupérés ci-dessous et convertis-les en une liste JSON valide.\n"
                "Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- ref_nr: un identifiant unique (ex: ca-visitor-opp-1)\n"
                "- title: le titre officiel de l'événement en français (ex: Sommet Mondial sur l'Intelligence Artificielle)\n"
                "- organizer: le nom de l'organisme ou association hôte (ex: Institut d'IA du Canada)\n"
                "- event_date: la date de l'événement (ex: 12-14 Octobre 2026)\n"
                "- location: la ville et la province (ex: Montréal, Québec)\n"
                "- deadline: la date limite d'inscription (ex: 15 Septembre 2026) ou 'Non précisée'\n"
                "- description: une brève description (2-3 phrases) expliquant l'intérêt de l'événement et comment s'y inscrire pour demander une lettre d'invitation de visa\n"
                "- url_apply: le vrai lien web officiel de l'événement pour s'inscrire\n\n"
                f"Opportunités brutes :\n{search_results}"
            )

            if use_openai:
                opps_list = call_openai_json(
                    "Tu es un extracteur JSON strict. Retourne uniquement une liste JSON valide, sans markdown.",
                    json_prompt,
                    temperature=0.1,
                )
                self.stdout.write(f"JSON reçu de l'IA (éléments={len(opps_list) if isinstance(opps_list, list) else 'non-liste'})")
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
                    opps_list = json.loads(response_json.text)
                except json.JSONDecodeError as je:
                    self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                    return

            if not isinstance(opps_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste d'opportunités.")
                return

            self.stdout.write(f"Nombre d'opportunités extraites par l'IA : {len(opps_list)}")

            created_count = 0
            updated_count = 0

            for opp in opps_list:
                ref_nr = opp.get("ref_nr", "").strip()
                title = opp.get("title", "").strip()
                organizer = opp.get("organizer", "").strip()
                url_apply = opp.get("url_apply", "").strip()

                if not ref_nr or not title or not organizer or not url_apply:
                    continue

                # Check if the url_apply is active (returns 200/300 status code, not 404 or 410)
                if not _is_url_active(url_apply):
                    self.stdout.write(f"Opportunité ignorée car le lien url_apply est inactif ou renvoie un 404 : {url_apply}")
                    continue

                obj, created = CanadaVisitorOpportunity.objects.update_or_create(
                    ref_nr=ref_nr,
                    defaults={
                        "title": title,
                        "organizer": organizer,
                        "event_date": opp.get("event_date", "").strip(),
                        "location": opp.get("location", "").strip(),
                        "deadline": opp.get("deadline", "Non précisée").strip(),
                        "description": opp.get("description", "").strip(),
                        "url_apply": url_apply,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Désactiver les anciennes opportunités après 30 jours
            cutoff = timezone.now() - timezone.timedelta(days=30)
            deactivated_count = CanadaVisitorOpportunity.objects.filter(
                last_seen__lt=cutoff, is_active=True
            ).update(is_active=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation des opportunités de visa visiteur terminée ! +{created_count} nouvelles opportunités, "
                    f"{updated_count} mises à jour, {deactivated_count} désactivées."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")
