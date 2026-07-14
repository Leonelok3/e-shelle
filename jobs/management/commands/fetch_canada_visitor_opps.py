from __future__ import annotations

import json
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from jobs.models import CanadaVisitorOpportunity

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Cherche et importe par IA les opportunités de visa visiteur/tourisme au Canada (conférences, séminaires, certifications)"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation du client Vertex AI...")
        client, err = get_vertex_client()
        if err or not client:
            self.stderr.write(f"Erreur d'initialisation du client Vertex AI : {err}")
            return

        self.stdout.write("Recherche globale des opportunités de visa visiteur...")

        # Pass 1: Google Search Grounding to find actual upcoming conferences, summits & events in Canada
        search_prompt = (
            "Recherche sur le web des conférences internationales, sommets mondiaux, séminaires professionnels et "
            "certifications en présentiel se déroulant au Canada pour l'année 2026/2027, qui acceptent et invitent des participants internationaux "
            "et qui fournissent une lettre d'invitation officielle pour l'obtention d'un visa de résident temporaire (visa visiteur / tourisme). "
            "Trouve au moins 5 à 8 événements réels avec des dates de déroulement précises (exemples: conférences en technologies de l'information, "
            "sommets en santé, forums d'affaires, formations certifiantes d'organismes reconnus à Montréal, Toronto, Vancouver, Calgary, etc.). "
            "Pour chaque événement, tu dois obligatoirement trouver : le nom exact de l'événement, l'organisation ou l'association hôte, "
            "la date de déroulement de l'événement, la ville et la province d'accueil, la date limite d'inscription, "
            "une description brève et le lien URL source direct pour s'inscrire."
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
            self.stdout.write("Résultats de recherche récupérés. Extraction JSON...")

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

            response_json = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=json_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )

            try:
                opps_list = json.loads(response_json.text)
            except json.JSONDecodeError as je:
                self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                return

            if not isinstance(opps_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste d'opportunités.")
                return

            created_count = 0
            updated_count = 0

            for opp in opps_list:
                ref_nr = opp.get("ref_nr", "").strip()
                title = opp.get("title", "").strip()
                organizer = opp.get("organizer", "").strip()
                url_apply = opp.get("url_apply", "").strip()

                if not ref_nr or not title or not organizer or not url_apply:
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
