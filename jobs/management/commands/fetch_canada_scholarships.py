from __future__ import annotations

import json
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from jobs.models import CanadaScholarship

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Cherche et importe par IA les bourses d'études au Canada actives pour les étudiants internationaux"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation du client Vertex AI...")
        client, err = get_vertex_client()
        if err or not client:
            self.stderr.write(f"Erreur d'initialisation du client Vertex AI : {err}")
            return

        self.stdout.write("Recherche globale des bourses d'études au Canada...")
        
        # Pass 1: Google Search Grounding to find actual active scholarships
        search_prompt = (
            "Recherche sur le web des bourses d'études réelles, officielles et actuellement ouvertes ou annoncées "
            "pour l'année universitaire 2026/2027 au Canada, destinées aux étudiants internationaux (Afrique, Europe, Asie, etc.). "
            "Trouve au moins 5 à 8 bourses d'études valides (exemples: bourses Vanier, bourses d'excellence de l'Université de Montréal, "
            "bourses d'exemptions de droits de scolarité de l'Université d'Ottawa, bourses de l'Université Laval, bourses de l'UQAM, bourses de McGill, etc.). "
            "Pour chaque bourse, tu dois impérativement trouver : le titre exact de la bourse, l'université ou l'organisme émetteur, "
            "la valeur financière de la bourse, les critères d'éligibilité simplifiés, la date limite de candidature estimée ou réelle, "
            "une description brève et le lien URL source direct pour postuler."
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
                "Analyse les bourses d'études canadiennes récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- ref_nr: un identifiant unique (ex: ca-scholarship-1)\n"
                "- title: le nom officiel de la bourse en français (ex: Bourse d'exemption de l'Université d'Ottawa)\n"
                "- provider: le nom de l'université ou de l'organisme (ex: Université d'Ottawa)\n"
                "- amount: la valeur de la bourse (ex: Exemption partielle, 10 000 $/an, Entière)\n"
                "- eligibility: les critères clés d'éligibilité simplifiés en français\n"
                "- deadline: la date limite (ex: 31 Mars 2026) ou 'Non précisé'\n"
                "- description: une brève description (2-3 phrases) expliquant comment postuler et le public cible\n"
                "- url_apply: le vrai lien web officiel pour soumettre son dossier de bourse\n\n"
                f"Bourses brutes :\n{search_results}"
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
                scholarships_list = json.loads(response_json.text)
            except json.JSONDecodeError as je:
                self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                return

            if not isinstance(scholarships_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste de bourses.")
                return

            created_count = 0
            updated_count = 0

            for sc in scholarships_list:
                ref_nr = sc.get("ref_nr", "").strip()
                title = sc.get("title", "").strip()
                provider = sc.get("provider", "").strip()
                url_apply = sc.get("url_apply", "").strip()

                if not ref_nr or not title or not provider or not url_apply:
                    continue

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
