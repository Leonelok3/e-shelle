"""
Usage: python manage.py generate_exercices --chapitre <slug> --niveau entrainement --nb 5
"""
import json
from django.core.management.base import BaseCommand
from math_cm.models import Chapitre, Exercice

PROMPT_EXERCICES = """
Tu es un professeur de mathématiques expert du programme MINESEC Cameroun.
Génère {nb} exercices de niveau "{niveau}" pour le chapitre "{titre}" en {classe}.

Chaque exercice doit avoir cette structure JSON EXACTE :
{{
  "titre": "Titre court de l'exercice",
  "type_exercice": "qcm",
  "niveau": "{niveau}",
  "bareme": 5,
  "duree_recommandee": 15,
  "enonce": {{
    "texte": "Énoncé complet...",
    "donnees": ["donnée 1"],
    "questions": [{{"numero": "1", "texte": "Question 1", "points": 5}}]
  }},
  "correction": {{
    "methode": "Description de la méthode",
    "etapes": [{{"numero": 1, "texte": "Résultat", "justification": "Pourquoi"}}],
    "reponses": {{"1": "réponse"}},
    "piege": "Erreur fréquente à éviter",
    "points_total": 5
  }},
  "options_qcm": [
    {{"label": "A", "texte": "Option A", "correct": false}},
    {{"label": "B", "texte": "Option B", "correct": true}},
    {{"label": "C", "texte": "Option C", "correct": false}},
    {{"label": "D", "texte": "Option D", "correct": false}}
  ]
}}

Réponds UNIQUEMENT avec un tableau JSON valide.
Utilise des contextes africains (marchés, agriculture, transport) quand c'est naturel.
"""


class Command(BaseCommand):
    help = 'Génère des exercices pour un chapitre via les fournisseurs IA configurés'

    def add_arguments(self, parser):
        parser.add_argument('--chapitre', type=str, required=True)
        parser.add_argument('--niveau', type=str, default='entrainement',
                            choices=['decouverte', 'entrainement', 'approfondissement', 'examen'])
        parser.add_argument('--nb', type=int, default=5)

    def handle(self, *args, **options):
        from ai_engine.services.llm_service import call_llm

        try:
            chapitre = Chapitre.objects.get(slug=options['chapitre'])
        except Chapitre.DoesNotExist:
            self.stdout.write(self.style.ERROR("Chapitre introuvable"))
            return

        prompt = PROMPT_EXERCICES.format(
            nb=options['nb'],
            niveau=options['niveau'],
            titre=chapitre.titre,
            classe=chapitre.classe.label,
        )

        self.stdout.write(f"⏳ Génération de {options['nb']} exercices ({options['niveau']})...")

        raw = call_llm("Tu es un professeur de mathématiques. Réponds uniquement en JSON.",
                       prompt, max_tokens=8192)
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]

        try:
            exercices_data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Erreur JSON : {e}"))
            return

        offset = chapitre.exercices.count()
        for i, ex in enumerate(exercices_data):
            Exercice.objects.update_or_create(
                chapitre=chapitre, numero=offset + i + 1,
                defaults={
                    'titre': ex['titre'],
                    'type_exercice': ex.get('type_exercice', 'qcm'),
                    'niveau': ex.get('niveau', options['niveau']),
                    'enonce': ex['enonce'],
                    'correction': ex['correction'],
                    'options_qcm': ex.get('options_qcm', []),
                    'bareme': ex.get('bareme', 5),
                    'duree_recommandee': ex.get('duree_recommandee', 20),
                    'is_published': True,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f"✅ {len(exercices_data)} exercices créés pour '{chapitre.titre}'"
        ))
