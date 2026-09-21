"""
Usage: python manage.py generate_cours --chapitre <slug> --lecons 4
"""
import json
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from math_cm.models import Chapitre, Lecon

PROMPT_COURS = """
Tu es un professeur de mathématiques expert du programme MINESEC Cameroun.
Génère un cours complet pour le chapitre "{titre}" destiné aux élèves de {classe}.

Génère exactement {nb_lecons} leçons progressives en JSON valide.
Chaque leçon doit avoir cette structure EXACTE :
{{
  "ordre": 1,
  "titre": "Titre de la leçon",
  "type_lecon": "definition",
  "duree_lecture": 15,
  "is_free": false,
  "contenu": {{
    "introduction": "Texte d'introduction engageant...",
    "sections": [
      {{
        "titre": "I. Titre section",
        "type": "texte",
        "contenu": "Explication claire...",
        "formules": ["formule mathématique"],
        "exemples": [{{"enonce": "...", "solution": "...", "etapes": ["Étape 1", "Étape 2"]}}],
        "remarques": ["Remarque importante..."]
      }}
    ],
    "retenir": ["Point essentiel 1", "Point essentiel 2"],
    "mots_cles": ["mot1", "mot2"]
  }}
}}

La première leçon doit avoir "is_free": true.
Réponds UNIQUEMENT avec un tableau JSON valide. Pas de texte avant ou après.
Adapte le vocabulaire au niveau {classe}. Utilise des exemples concrets de la vie africaine/camerounaise.
"""


class Command(BaseCommand):
    help = "Génère les leçons d'un chapitre via les fournisseurs IA configurés"

    def add_arguments(self, parser):
        parser.add_argument('--chapitre', type=str, required=True, help='Slug du chapitre')
        parser.add_argument('--lecons', type=int, default=4, help='Nombre de leçons à générer')

    def handle(self, *args, **options):
        from ai_engine.services.llm_service import call_llm

        try:
            chapitre = Chapitre.objects.get(slug=options['chapitre'])
        except Chapitre.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Chapitre '{options['chapitre']}' introuvable"))
            return

        prompt = PROMPT_COURS.format(
            titre=chapitre.titre,
            classe=chapitre.classe.label,
            nb_lecons=options['lecons'],
        )

        self.stdout.write(f"⏳ Génération de {options['lecons']} leçons pour '{chapitre.titre}'...")

        raw = call_llm("Tu es un professeur de mathématiques. Réponds uniquement en JSON.",
                       prompt, max_tokens=8192)
        # Nettoyer si entouré de ```json
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]

        try:
            lecons_data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Erreur JSON : {e}"))
            self.stdout.write(raw[:500])
            return

        created = 0
        for ld in lecons_data:
            base_slug = slugify(f"{chapitre.slug}-l{ld['ordre']}-{ld['titre']}")[:210]
            slug = base_slug
            counter = 1
            while Lecon.objects.filter(slug=slug).exclude(chapitre=chapitre, ordre=ld['ordre']).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            _, was_created = Lecon.objects.update_or_create(
                chapitre=chapitre, ordre=ld['ordre'],
                defaults={
                    'titre': ld['titre'],
                    'slug': slug,
                    'type_lecon': ld.get('type_lecon', 'definition'),
                    'contenu': ld['contenu'],
                    'duree_lecture': ld.get('duree_lecture', 15),
                    'is_free': ld.get('is_free', False),
                    'is_published': True,
                }
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {created} leçons créées pour '{chapitre.titre}'"
        ))
