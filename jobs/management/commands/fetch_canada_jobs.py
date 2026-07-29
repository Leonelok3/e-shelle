from __future__ import annotations

import hashlib
import json
import logging
import re
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
        self.stdout.write("Initialisation du client Vertex AI...")
        client, err = get_vertex_client()
        if err or not client:
            self.stderr.write(f"Erreur d'initialisation du client Vertex AI : {err}")
            return

        self.stdout.write("Recherche globale des offres d'emploi Canada avec EIMT...")

        # Pass 1: Google Search Grounding to find actual job links and details
        search_prompt = (
            "Recherche sur le web des offres d'emploi réelles, vérifiables et récentes (publiées il y a moins de 30 jours) "
            "d'employeurs canadiens qui recrutent activement des travailleurs à l'étranger (candidats qui ne sont PAS "
            "déjà au Canada), en particulier des candidats francophones d'Afrique (Cameroun, Côte d'Ivoire, Sénégal, etc.). "
            "IMPORTANT — n'utilise que des sources vérifiées : le Guichet-Emplois officiel du gouvernement du Canada "
            "(guichet-emplois.gc.ca / jobbank.gc.ca), les pages carrières officielles des employeurs, ou des cabinets de "
            "recrutement canadiens agréés. Ignore les blogs et agrégateurs non officiels qui ne font que relayer une offre. "
            "EXCLUS impérativement toute offre réservée aux résidents/citoyens canadiens déjà sur le territoire ou sans "
            "aucune mention de parrainage/EIMT/mobilité — ne garde QUE les postes recrutant explicitement hors du Canada : "
            "EIMT (Étude d'Impact sur le Marché du Travail) déjà approuvée, EIMT en cours de traitement, postes exemptés "
            "d'EIMT, ou dans le cadre de la Mobilité Francophone (dispense d'EIMT pour les candidats francophones "
            "recrutés hors Québec). "
            "Trouve au moins 5 à 10 offres d'emploi différentes dans divers secteurs (Santé, IT, Agriculture, Restauration, Transport, Construction, etc.). "
            "Pour chaque offre, tu dois obligatoirement trouver : le titre exact du poste, le nom de l'entreprise, la ville, la province, "
            "le statut exact de l'EIMT ou Mobilité Francophone, le salaire, la date limite de candidature si elle est publiée "
            "(sinon 'Non précisé'), une description brève et le lien URL source direct du poste."
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

            for job in jobs_list:
                title = job.get("title", "").strip()
                company = job.get("company", "").strip()
                city = job.get("city", "").strip()
                url_apply = job.get("url_apply", "").strip()
                lmia_status = job.get("lmia_status", "Non précisé").strip()

                if not title or not company or not url_apply:
                    continue

                # Filet de sécurité supplémentaire : on n'affiche que les offres
                # explicitement ouvertes aux candidats étrangers.
                allowed_status = (
                    "eimt" in lmia_status.lower()
                    or "francophone" in lmia_status.lower()
                    or "exempt" in lmia_status.lower()
                )
                if not allowed_status:
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
