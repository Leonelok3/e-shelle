"""
Commande d'ingestion de sujets d'examen PDF -> exercices Django
Usage : python manage.py import_exam_pdf <pdf_path> <exam_code> [--section co|ce|ee|eo] [--level A1|B1...]

Prerequis : pip install pymupdf openai
"""
import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un expert en preparation aux examens de langue (TCF, TEF, DELF, DALF, Goethe-Zertifikat).
On te donne le contenu brut d'un sujet d'examen extrait d'un PDF.

Ta tache : structurer ce contenu en JSON avec, pour chaque question :
- "question_text" : le texte de la question ou de l'enonce
- "option_a", "option_b", "option_c", "option_d" : les choix (laisser vide si pas de QCM)
- "correct_option" : "A", "B", "C" ou "D" (laisser vide si pas de QCM)
- "summary" : la correction/justification si presente dans le document
- "competency_tags" : liste de 1 a 3 tags de competence PRECIS
  - Pour le francais : ex: "accord du participe passe", "inference du sens d'un mot en contexte",
    "comprendre une intention implicite", "connecteurs logiques", "conjugaison au subjonctif"
  - JAMAIS de tags generiques comme "grammaire" ou "comprehension" seuls

Reponds UNIQUEMENT en JSON valide, structure exacte :
{"questions": [{"question_text": "...", "option_a": "...", "option_b": "...", "option_c": "...",
"option_d": "...", "correct_option": "A", "summary": "...", "competency_tags": ["...", "..."]}]}
"""


class Command(BaseCommand):
    help = "Importe un sujet d'examen PDF et cree les exercices + tags de competence en base"

    def add_arguments(self, parser):
        parser.add_argument("pdf_path", type=str, help="Chemin vers le fichier PDF")
        parser.add_argument("exam_code", type=str, help="Code de l'examen : tcf, tef, delf, dalf")
        parser.add_argument("--section", type=str, default="co",
                            choices=["co", "ce", "ee", "eo"],
                            help="Section d'examen (co/ce/ee/eo). Defaut: co")
        parser.add_argument("--level", type=str, default="B1",
                            choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                            help="Niveau CECR cible. Defaut: B1")
        parser.add_argument("--dry-run", action="store_true",
                            help="Affiche les questions sans les sauvegarder")

    def handle(self, *args, **options):
        pdf_path = Path(options["pdf_path"])
        exam_code = options["exam_code"].lower()
        section_code = options["section"]
        level = options["level"]
        dry_run = options["dry_run"]

        if not pdf_path.exists():
            raise CommandError(f"Fichier introuvable : {pdf_path}")

        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise CommandError("OPENAI_API_KEY absent des settings")

        self.stdout.write(self.style.NOTICE(
            f"\n[PDF] Ingestion : {pdf_path.name} -- {exam_code.upper()} / {section_code.upper()} / {level}"
        ))

        text = self._extract_text(pdf_path)
        if len(text) < 100:
            raise CommandError("PDF trop court ou illisible (< 100 chars extraits).")
        self.stdout.write(f"   OK {len(text)} caracteres extraits du PDF")

        self.stdout.write("   [LLM] Appel GPT-4o pour structurer les questions...")
        questions_data = self._call_llm(api_key, text)
        self.stdout.write(f"   OK {len(questions_data)} questions structurees par le LLM")

        if dry_run:
            self.stdout.write("\n" + self.style.WARNING("--- DRY RUN -- rien n'est sauvegarde ---"))
            for i, q in enumerate(questions_data, 1):
                self.stdout.write(f"\n[Q{i}] {q.get('question_text', '')[:80]}")
                self.stdout.write(f"      A={q.get('option_a','')} B={q.get('option_b','')} -> {q.get('correct_option','?')}")
                self.stdout.write(f"      Tags: {', '.join(q.get('competency_tags', []))}")
            return

        from preparation_tests.models import (
            Exam, CourseLesson, CourseExercise, CompetencyTag
        )

        try:
            exam = Exam.objects.get(code__iexact=exam_code)
        except Exam.DoesNotExist:
            raise CommandError(
                f"Examen '{exam_code}' introuvable en base. "
                f"Creez-le via l'admin ou setup_french_exams."
            )

        lesson, created = CourseLesson.objects.get_or_create(
            slug=f"{exam_code}-{section_code}-{level.lower()}-pdf-import",
            defaults={
                "title": f"[Import PDF] {exam_code.upper()} {section_code.upper()} {level}",
                "section": section_code,
                "level": level,
                "locale": "fr",
                "content_html": f"<p>Questions importees depuis PDF -- {pdf_path.name}</p>",
                "is_published": False,
                "order": 999,
            }
        )
        if created:
            lesson.exams.add(exam)
            self.stdout.write(f"   [NEW] Lecon creee : {lesson.title} (is_published=False)")
        else:
            self.stdout.write(f"   [OK] Lecon existante : {lesson.title}")

        created_count = 0
        tags_reused = 0
        tags_created = 0

        for i, q_data in enumerate(questions_data, 1):
            exercise = CourseExercise.objects.create(
                lesson=lesson,
                title=f"Q{i} -- {section_code.upper()} {level}",
                question_text=q_data.get("question_text", ""),
                option_a=q_data.get("option_a", ""),
                option_b=q_data.get("option_b", ""),
                option_c=q_data.get("option_c", ""),
                option_d=q_data.get("option_d", ""),
                correct_option=q_data.get("correct_option", "A") or "A",
                summary=q_data.get("summary", ""),
                order=i,
            )

            for tag_label in q_data.get("competency_tags", []):
                tag_label = tag_label.strip()
                if not tag_label:
                    continue
                tag, was_created = CompetencyTag.objects.get_or_create(
                    label__iexact=tag_label,
                    defaults={"label": tag_label, "skill": section_code},
                )
                exercise.competency_tags.add(tag)
                if was_created:
                    tags_created += 1
                else:
                    tags_reused += 1

            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] {created_count} exercices crees | "
            f"{tags_created} nouveaux tags | {tags_reused} tags reutilises\n"
            f"Lecon : '{lesson.title}' (is_published=False)\n"
            f"Relire dans l'admin avant publication :\n"
            f"/admin/preparation_tests/courselesson/{lesson.pk}/change/"
        ))

    def _extract_text(self, pdf_path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            texts = [page.get_text("text") for page in doc]
            doc.close()
            return "\n".join(texts)
        except ImportError:
            raise CommandError("PyMuPDF non installe. Installez : pip install pymupdf")

    def _call_llm(self, api_key: str, text: str) -> list:
        try:
            from openai import OpenAI
        except ImportError:
            raise CommandError("openai non installe : pip install openai")

        client = OpenAI(api_key=api_key)
        if len(text) > 12000:
            text = text[:12000] + "\n[TEXTE TRONQUE]"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Contenu du sujet d'examen :\n\n{text}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        try:
            return json.loads(raw).get("questions", [])
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON invalide du LLM : {e}\n{raw[:300]}")
