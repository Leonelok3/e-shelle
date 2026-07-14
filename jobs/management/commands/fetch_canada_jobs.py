from __future__ import annotations

import json
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from jobs.models import CanadaJobOffer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Cherche et importe les nouvelles offres d'emploi d'employeurs canadiens qui recrutent à l'étranger (EIMT/LMIA)"

    def handle(self, *args, **options):
        self.stdout.write("Initialisation du client Vertex AI...")
        client, err = get_vertex_client()
        if err or not client:
            self.stderr.write(f"Erreur d'initialisation du client Vertex AI : {err}")
            return

        self.stdout.write("Recherche globale des offres d'emploi Canada avec EIMT...")
        
        # Pass 1: Google Search Grounding to find actual job links and details
        search_prompt = (
            "Recherche sur le web des offres d'emploi réelles et récentes (publiées il y a moins de 30 jours) d'employeurs canadiens "
            "qui recrutent activement des travailleurs étrangers hors du Canada, spécifiquement avec une EIMT (Étude d'Impact sur le Marché du Travail) approuvée ou en cours. "
            "Trouve au moins 5 à 10 offres d'emploi différentes dans divers secteurs (Santé, IT, Agriculture, Restauration, Construction, etc.). "
            "Pour chaque offre, tu dois obligatoirement trouver : le titre exact du poste, le nom de l'entreprise, la ville, la province, le statut EIMT, le salaire, "
            "une description brève et le lien URL source direct du poste (sur le Guichet-Emplois ou site d'origine)."
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
            self.stdout.write("Résultats de recherche récupérés. Conversion en JSON...")

            # Pass 2: Controlled JSON extraction
            json_prompt = (
                "Analyse les offres d'emploi récupérées ci-dessous et convertis-les en une liste JSON valide.\n"
                "Ne génère rien d'autre que du JSON. Chaque objet de la liste doit avoir ces clés exactes :\n"
                "- ref_nr: un identifiant unique basé sur le poste et l'entreprise (ex: ca-job-1)\n"
                "- title: le titre de l'emploi en français (ex: Ouvrier Agricole)\n"
                "- company: le nom de l'entreprise\n"
                "- city: la ville canadienne\n"
                "- province: la province (ex: Québec, Alberta)\n"
                "- lmia_status: le statut de l'EIMT (ex: 'EIMT approuvé', 'EIMT en cours', 'Exempté')\n"
                "- salary: le salaire (ex: 20 $/heure) ou 'Non précisé'\n"
                "- description: une explication concise (2-3 phrases) en français du rôle et pourquoi c'est idéal pour un candidat étranger\n"
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

            try:
                jobs_list = json.loads(response_json.text)
            except json.JSONDecodeError as je:
                self.stderr.write(f"Erreur de décodage JSON : {je}\nContenu brut : {response_json.text}")
                return

            if not isinstance(jobs_list, list):
                self.stderr.write("L'IA n'a pas retourné une liste d'offres.")
                return

            created_count = 0
            updated_count = 0
            seen_refs = []

            for job in jobs_list:
                ref_nr = job.get("ref_nr", "").strip()
                title = job.get("title", "").strip()
                company = job.get("company", "").strip()
                url_apply = job.get("url_apply", "").strip()

                if not ref_nr or not title or not company or not url_apply:
                    continue

                seen_refs.append(ref_nr)

                offer, created = CanadaJobOffer.objects.update_or_create(
                    ref_nr=ref_nr,
                    defaults={
                        "title": title,
                        "company": company,
                        "city": job.get("city", "").strip(),
                        "province": job.get("province", "").strip(),
                        "lmia_status": job.get("lmia_status", "Non précisé").strip(),
                        "salary": job.get("salary", "Non précisé").strip(),
                        "description": job.get("description", "").strip(),
                        "url_apply": url_apply,
                        "is_active": True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Désactiver les anciennes offres qui ne sont plus d'actualité après 15 jours
            cutoff = timezone.now() - timezone.timedelta(days=15)
            deactivated_count = CanadaJobOffer.objects.filter(
                last_seen__lt=cutoff, is_active=True
            ).update(is_active=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Importation terminée ! +{created_count} nouvelles offres, "
                    f"{updated_count} mises à jour, {deactivated_count} désactivées."
                )
            )

        except Exception as e:
            self.stderr.write(f"Une erreur s'est produite lors de la génération : {e}")
