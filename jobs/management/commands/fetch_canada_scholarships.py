from __future__ import annotations

import hashlib
import json
import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from ai_engine.services.openai_adapter import call_openai, call_openai_json, call_openai_web, search_duckduckgo
from jobs.models import CanadaScholarship
from jobs.content_fallback import import_scholarships

logger = logging.getLogger(__name__)


def _is_url_active(url: str) -> bool:
    from ai_engine.services.official_sources import fetch
    domains = ['gc.ca', 'canada.ca', 'quebec.ca', 'educanada.ca', 'mcgill.ca',
        'ubc.ca', 'umontreal.ca', 'ulaval.ca', 'uottawa.ca', 'alberta.ca',
        'utoronto.ca', 'destinationcanada.com']
    try:
        fetch(url, domains)
        return True
    except (requests.RequestException, ValueError):
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


def _truncate(value: str, max_length: int) -> str:
    value = (value or "").strip()
    return value[:max_length]

def _generate_content_with_retry(client, model, contents, config, retries=4, initial_delay=5):
    # A quota failure is not fixed by immediate retries; switch to official sources.
    return client.models.generate_content(model=model, contents=contents, config=config)


class Command(BaseCommand):
    help = "Cherche et importe par IA les bourses d'études au Canada actives pour les étudiants internationaux"

    def add_arguments(self, parser):
        parser.add_argument('--skip-ai', action='store_true', help='Sources officielles uniquement, sans appel IA.')

    def handle(self, *args, **options):
        from ai_engine.services.availability import offline_mode, failed
        if not options.get('skip_ai') and not offline_mode():
            try:
                return self._handle_ai(*args, **options)
            except Exception as error:
                if getattr(settings, 'OPENAI_API_KEY', ''):
                    failed('openai', error)
                logger.warning('Collecte IA indisponible (%s); utilisation des sources officielles.', type(error).__name__)
        try:
            result = import_scholarships()
        except Exception as error:
            raise CommandError('Source officielle indisponible. Les contenus existants sont conservés.') from error
        if not result['found']:
            raise CommandError('Aucun nouveau contenu vérifiable trouvé. Les contenus existants sont conservés.')
        self.stdout.write(self.style.SUCCESS(f"Collecte sans IA : {result}"))

    def _handle_ai(self, *args, **options):
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
                raise CommandError(f"Erreur d'initialisation du client GenAI : {err}")

        self.stdout.write("Recherche globale des bourses d'études au Canada...")
        
        # Pass 1: Google Search Grounding to find actual active scholarships
        search_prompt = (
            "Recherche sur le web des bourses d'études réelles et officielles actives ou annoncées pour les étudiants internationaux au Canada pour 2026/2027. Cible en priorité les sites officiels d'universités canadiennes (umontreal.ca, uottawa.ca, ulaval.ca, mcgill.ca, etc.) ou gouvernementaux (canada.ca, educanada.ca). Liste au moins 6 bourses valides avec : le titre de la bourse, l'université ou organisme émetteur, la valeur, les critères d'éligibilité, la date limite de candidature et le lien URL officiel direct pour postuler.\n"
            "EXCLUDE expired, closed, or deactivated offers. Verify that the scholarship is active.\n"
            "Crucial: The URL ('url_apply') MUST be the exact, specific direct web page link of the scholarship offer. Do NOT use generic parent URLs (like 'https://www.ulaval.ca') or guess/hallucinate URLs. If you cannot find the direct, exact, working URL for the scholarship, DO NOT include that scholarship."
        )

        try:
            if use_openai:
                self.stdout.write("OpenAI actif. Recherche web OpenAI puis extraction IA...")
                try:
                    search_results = call_openai_web(
                        "Tu es un analyste de bourses canadiennes. Utilise le web et privilégie EduCanada, Canada.ca et les universités officielles.",
                        search_prompt,
                    )
                except Exception as web_error:
                    logger.warning("OpenAI web search indisponible: %s", web_error)
                    ddg_results = search_duckduckgo("site:educanada.ca scholarships international students Canada 2026 2027", max_results=12)
                    if not ddg_results:
                        ddg_results = search_duckduckgo("site:canada.ca bourses étudiants internationaux Canada 2026", max_results=12)
                    search_results = ddg_results or (
                        "Sources officielles: https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=eng\n"
                        "https://www.educanada.ca/scholarships-bourses/app/apply-scholarships-postuler-bourses.aspx?lang=eng\n"
                        "Si aucune bourse précise active n'est identifiable, retourne une liste JSON vide."
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

            if use_openai:
                scholarships_list = call_openai_json(
                    "Tu es un extracteur JSON strict. Retourne uniquement une liste JSON valide, sans markdown.",
                    json_prompt,
                    temperature=0.1,
                )
                self.stdout.write(f"JSON reçu de l'IA (éléments={len(scholarships_list) if isinstance(scholarships_list, list) else 'non-liste'})")
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
                    scholarships_list = json.loads(response_json.text)
                except json.JSONDecodeError as je:
                    raise CommandError(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")

            if not isinstance(scholarships_list, list):
                raise CommandError("L'IA n'a pas retourné une liste de bourses.")

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
                        "title": _truncate(title, 300),
                        "provider": _truncate(provider, 200),
                        "amount": _truncate(sc.get("amount", "Non précisé"), 100),
                        "eligibility": sc.get("eligibility", "").strip(),
                        "deadline": _truncate(sc.get("deadline", "Non précisé"), 100),
                        "description": sc.get("description", "").strip(),
                        "url_apply": url_apply,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            if created_count + updated_count == 0:
                raise ValueError('Aucun contenu IA exploitable')

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

        except Exception:
            raise
