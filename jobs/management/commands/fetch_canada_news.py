from __future__ import annotations

import hashlib
import json
import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from ai_engine.services.openai_adapter import call_openai, call_openai_json, search_duckduckgo
from jobs.models import CanadaNews

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


def _stable_ref_nr(category: str, title: str) -> str:
    """
    Identifiant stable basé sur (category, title) pour éviter les doublons.
    """
    raw = f"{category.strip().lower()}|{title.strip().lower()}"
    return "ca-news-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


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
    help = "Cherche sur le web et importe par IA les actualités et tirages officiels sur l'immigration Canada"

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

        self.stdout.write("Recherche globale des actualités d'immigration Canada...")

        # Pass 1: Google Search Grounding to find actual active news & official IRCC draws/announcements
        search_prompt = (
            "Recherche sur le web les dernières actualités officielles, tirages récents Entrée Express ou Arrima, "
            "communiqués officiels d'immigration et nouvelles lois sur l'immigration concernant le Canada pour l'année 2026/2027. "
            "Cible en priorité les sites officiels gouvernementaux comme canada.ca, quebec.ca ou de grands journaux vérifiés. "
            "Trouve au moins 6 actualités réelles de 2026. Liste pour chacune : le titre de l'actualité, la catégorie "
            "(ex: Tirage, Loi d'immigration, Communiqué ou Opportunité), la date de publication, un résumé explicatif détaillé "
            "en français de 3-4 phrases et l'URL source directe vers la page officielle.\n"
            "EXCLUDE expired, closed, or deactivated offers. Verify that the news/draw is active.\n"
            "Crucial: The URL ('url_source') MUST be the exact, specific direct web page link of the official article/announcement. "
            "Do NOT use generic parent URLs or guess/hallucinate URLs. If you cannot find the direct, exact, working URL, DO NOT include that news."
        )

        try:
            if use_openai:
                self.stdout.write("OpenAI actif. Recherche web via DuckDuckGo puis extraction IA...")
                ddg_results = search_duckduckgo("site:canada.ca IRCC Express Entry draw immigration Canada 2026", max_results=12)
                if not ddg_results:
                    ddg_results = search_duckduckgo("site:quebec.ca Arrima tirage immigration Quebec 2026", max_results=12)
                if not ddg_results:
                    self.stderr.write("Aucun résultat DuckDuckGo exploitable.")
                    return
                search_results = call_openai(
                    "Tu es un analyste d'actualités immigration Canada. Analyse les résultats web fournis et conserve les informations officielles ou fiables.",
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
                "Analyse les actualités récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- title: le titre de l'actualité ou communiqué en français\n"
                "- category: la catégorie en français (obligatoirement l'une de ces valeurs exactes : 'Tirage', 'Loi d\'immigration', 'Communiqué' ou 'Opportunité')\n"
                "- published_date: la date de publication (ex: 15 Février 2026) ou 'Récemment'\n"
                "- summary: un résumé détaillé (3-4 phrases) en français expliquant l'impact de l'information pour les candidats étrangers\n"
                "- url_source: le vrai lien web officiel de la source (ex: canada.ca/fr/immigration-refugies-citoyennete/...)\n\n"
                f"Actualités brutes :\n{search_results}"
            )

            if use_openai:
                news_list = call_openai_json(
                    "Tu es un extracteur JSON strict. Retourne uniquement une liste JSON valide, sans markdown.",
                    json_prompt,
                    temperature=0.1,
                )
                self.stdout.write(f"JSON reçu de l'IA (éléments={len(news_list) if isinstance(news_list, list) else 'non-liste'})")
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
                    news_list = json.loads(response_json.text)
                except json.JSONDecodeError as je:
                    self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                    return

            if not isinstance(news_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste d'actualités.")
                return

            self.stdout.write(f"Nombre d'actualités extraites par l'IA : {len(news_list)}")

            created_count = 0
            updated_count = 0

            for ns in news_list:
                title = ns.get("title", "").strip()
                category = ns.get("category", "").strip()
                url_source = ns.get("url_source", "").strip()

                if not title or not category or not url_source:
                    continue

                # Check if the url_source is active (returns 200/300 status code, not 404 or 410)
                if not _is_url_active(url_source):
                    # Fallback to official government landing hub if the specific link is dead
                    category_lower = category.lower()
                    fallback_url = "https://www.canada.ca/fr/immigration-refugies-citoyennete.html"
                    if "tirage" in category_lower:
                        fallback_url = "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/rondes-invitations.html"
                    elif "loi" in category_lower:
                        fallback_url = "https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles.html"
                    elif "communiqué" in category_lower or "communique" in category_lower:
                        fallback_url = "https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles.html"
                    
                    self.stdout.write(f"Lien spécifique mort ({url_source}). Utilisation du lien officiel de secours : {fallback_url}")
                    url_source = fallback_url

                ref_nr = _stable_ref_nr(category, title)

                offer, created = CanadaNews.objects.update_or_create(
                    ref_nr=ref_nr,
                    defaults={
                        "title": title,
                        "category": category,
                        "published_date": ns.get("published_date", "Récemment").strip(),
                        "summary": ns.get("summary", "").strip(),
                        "url_source": url_source,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Désactiver les anciennes actualités après 30 jours
            cutoff = timezone.now() - timezone.timedelta(days=30)
            deactivated_count = CanadaNews.objects.filter(
                last_seen__lt=cutoff, is_active=True
            ).update(is_active=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation des actualités terminée ! +{created_count} nouvelles actualités, "
                    f"{updated_count} mises à jour, {deactivated_count} désactivées."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")
