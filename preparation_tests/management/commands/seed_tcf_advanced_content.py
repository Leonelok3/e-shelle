from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from preparation_tests.models import CourseExercise, CourseLesson, Exam, ExamSection


LEVEL_THEMES = {
    "B2": [
        "teletravail et integration professionnelle",
        "logement et installation au Canada",
        "formation continue et reconversion",
        "mobilite urbaine durable",
        "sante communautaire",
        "participation citoyenne",
    ],
    "C1": [
        "reconnaissance des diplomes",
        "intelligence artificielle au travail",
        "politiques d'integration francophone",
        "transition ecologique",
        "universites et recherche appliquee",
        "sante publique et prevention",
    ],
    "C2": [
        "ethique algorithmique",
        "souverainete linguistique",
        "diplomatie migratoire",
        "justice sociale et institutions",
        "memoire collective",
        "innovation scientifique responsable",
    ],
}

SECTION_META = {
    "co": ("Compréhension orale", "CO"),
    "ce": ("Compréhension écrite", "CE"),
    "ee": ("Expression écrite", "EE"),
    "eo": ("Expression orale", "EO"),
}


class Command(BaseCommand):
    help = "Seed deterministic TCF B2/C1/C2 lessons and exercises for CO, CE, EE and EO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--levels",
            default="B2,C1,C2",
            help="Comma-separated CECR levels to seed. Default: B2,C1,C2.",
        )
        parser.add_argument(
            "--lessons-per-section",
            type=int,
            default=6,
            help="Lessons to create per section and level. Default: 6.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        levels = [level.strip().upper() for level in options["levels"].split(",") if level.strip()]
        lessons_per_section = max(1, int(options["lessons_per_section"]))
        exam = self._ensure_tcf_exam()
        self._attach_existing_french_lessons(exam)

        created_lessons = 0
        updated_lessons = 0
        created_exercises = 0
        updated_exercises = 0

        for level in levels:
            themes = LEVEL_THEMES.get(level)
            if not themes:
                self.stdout.write(self.style.WARNING(f"Niveau ignore: {level}"))
                continue

            for section in ["co", "ce", "ee", "eo"]:
                for index, theme in enumerate(themes[:lessons_per_section], start=1):
                    lesson, was_created = self._upsert_lesson(exam, level, section, index, theme)
                    created_lessons += int(was_created)
                    updated_lessons += int(not was_created)

                    count = 5 if section in ["co", "ce"] else 3
                    for order in range(1, count + 1):
                        _, ex_created = self._upsert_exercise(lesson, section, level, theme, order)
                        created_exercises += int(ex_created)
                        updated_exercises += int(not ex_created)

        self.stdout.write(
            self.style.SUCCESS(
                "TCF seed OK: "
                f"{created_lessons} lecons creees, {updated_lessons} mises a jour, "
                f"{created_exercises} exercices crees, {updated_exercises} mis a jour."
            )
        )

    def _ensure_tcf_exam(self) -> Exam:
        exam, _ = Exam.objects.update_or_create(
            code="tcf",
            defaults={
                "name": "TCF Canada",
                "language": "fr",
                "description": "Preparation TCF Canada: CO, CE, EE, EO et examens blancs.",
            },
        )
        durations = {"co": 1500, "ce": 2700, "ee": 3600, "eo": 720}
        for order, code in enumerate(["co", "ce", "ee", "eo"], start=1):
            ExamSection.objects.update_or_create(
                exam=exam,
                code=code,
                defaults={"order": order, "duration_sec": durations[code]},
            )
        return exam

    def _attach_existing_french_lessons(self, exam: Exam) -> None:
        lessons = CourseLesson.objects.filter(
            locale="fr",
            section__in=["co", "ce", "ee", "eo"],
            is_published=True,
        )
        for lesson in lessons.iterator():
            lesson.exams.add(exam)

    def _upsert_lesson(self, exam: Exam, level: str, section: str, index: int, theme: str):
        title_long, code = SECTION_META[section]
        slug = f"tcf-advanced-{section}-{level.lower()}-{index}"
        title = f"TCF {level} - {code} - {theme.title()}"
        content = self._lesson_content(level, section, theme)
        lesson, created = CourseLesson.objects.update_or_create(
            slug=slug,
            defaults={
                "exam": exam,
                "section": section,
                "level": level,
                "title": title,
                "locale": "fr",
                "content_html": content,
                "order": 800 + index,
                "is_published": True,
            },
        )
        lesson.exams.add(exam)
        return lesson, created

    def _lesson_content(self, level: str, section: str, theme: str) -> str:
        title_long, code = SECTION_META[section]
        if section == "co":
            body = (
                "Ecoute active: repere d'abord la situation, puis l'opinion implicite, "
                "les connecteurs logiques et les nuances de certitude. En examen TCF, "
                "ne cherche pas a tout memoriser: note mentalement qui parle, pourquoi, "
                "et quelle consequence est annoncee."
            )
        elif section == "ce":
            body = (
                "Lecture efficace: commence par le titre et la conclusion, puis scanne "
                "les chiffres, concessions et reformulations. Les distracteurs du TCF "
                "reprennent souvent des mots du texte mais changent l'intention."
            )
        elif section == "ee":
            body = (
                "Production ecrite: construis une reponse avec une these claire, deux "
                "arguments developpes et une conclusion utile. Varie les connecteurs, "
                "precise les exemples et relis les accords."
            )
        else:
            body = (
                "Expression orale: annonce ton plan en une phrase, developpe avec des "
                "exemples concrets, puis termine par une prise de position nette. La "
                "fluidite compte autant que la richesse lexicale."
            )
        return (
            f"<h2>{title_long} - niveau {level}</h2>"
            f"<p><strong>Theme:</strong> {theme}.</p>"
            f"<p>{body}</p>"
            "<ul>"
            "<li>Objectif: comprendre la consigne et repondre sous contrainte de temps.</li>"
            "<li>Methode: identifier les mots-cles, l'intention et le piege principal.</li>"
            "<li>Evaluation: precision, coherence, correction linguistique et niveau CECR.</li>"
            "</ul>"
        )

    def _upsert_exercise(self, lesson: CourseLesson, section: str, level: str, theme: str, order: int):
        if section == "co":
            data = self._co_data(level, theme, order)
        elif section == "ce":
            data = self._ce_data(level, theme, order)
        elif section == "ee":
            data = self._ee_data(level, theme, order)
        else:
            data = self._eo_data(level, theme, order)

        return CourseExercise.objects.update_or_create(
            lesson=lesson,
            order=order,
            defaults={
                "title": data["title"],
                "instruction": data["instruction"],
                "question_text": data["question_text"],
                "option_a": data["option_a"],
                "option_b": data["option_b"],
                "option_c": data.get("option_c", ""),
                "option_d": data.get("option_d", ""),
                "correct_option": data["correct_option"],
                "summary": data["summary"],
                "is_active": True,
            },
        )

    def _co_data(self, level: str, theme: str, order: int) -> dict:
        scripts = [
            (
                "Lors d'une reunion municipale, une responsable explique que le projet avance, "
                "mais que son acceptation dependra surtout de la capacite a rassurer les habitants."
            ),
            (
                "Un conseiller d'orientation affirme que la formation courte n'est pas une solution "
                "miracle, meme si elle facilite l'entree dans certains secteurs en tension."
            ),
            (
                "Dans une chronique radio, l'intervenante reconnait les couts du programme, "
                "tout en soulignant que l'inaction serait plus couteuse a long terme."
            ),
            (
                "Un employeur indique qu'il valorise l'experience internationale, a condition que "
                "le candidat sache l'adapter aux normes professionnelles locales."
            ),
            (
                "Une etudiante explique que la difficulte principale n'est pas le volume de travail, "
                "mais la necessite de justifier chaque opinion avec precision."
            ),
        ]
        correct = ["B", "C", "A", "D", "B"][order - 1]
        return {
            "title": f"CO {level} - inference {order}",
            "instruction": f"Script d'ecoute ({theme}): {scripts[order - 1]}",
            "question_text": "Quelle idee principale faut-il retenir de cet extrait ?",
            "option_a": "La situation est simple et ne presente aucune tension.",
            "option_b": "La decision depend d'une condition ou d'une nuance importante.",
            "option_c": "Le locuteur rejette totalement la proposition evoquee.",
            "option_d": "Le locuteur se limite a donner une information administrative.",
            "correct_option": correct,
            "summary": "La bonne reponse tient compte de la concession et de la condition exprimees dans le script.",
        }

    def _ce_data(self, level: str, theme: str, order: int) -> dict:
        text = (
            f"Document {order} - {theme}. Une enquete recente montre que les usagers acceptent "
            "plus facilement une reforme lorsqu'elle est accompagnee d'explications concretes, "
            "d'un calendrier realiste et d'un mecanisme de recours. Les critiques ne portent pas "
            "sur l'objectif general, mais sur la transparence de la mise en oeuvre."
        )
        return {
            "title": f"CE {level} - document {order}",
            "instruction": text,
            "question_text": "Selon le document, quel element provoque surtout les reserves ?",
            "option_a": "Le refus de tout changement collectif.",
            "option_b": "L'absence de transparence dans l'application.",
            "option_c": "La disparition complete du calendrier.",
            "option_d": "Le manque d'interet pour le sujet.",
            "correct_option": "B",
            "summary": "Le texte precise que les critiques portent surtout sur la transparence de la mise en oeuvre.",
        }

    def _ee_data(self, level: str, theme: str, order: int) -> dict:
        tasks = [
            "Rédigez un message argumenté à une association locale pour proposer une amélioration concrète.",
            "Écrivez un texte d'opinion en présentant deux arguments et un exemple personnel ou social.",
            "Rédigez une réponse formelle à une institution en défendant une position nuancée.",
        ]
        return {
            "title": f"EE {level} - production {order}",
            "instruction": (
                f"Theme: {theme}. Longueur conseillee: "
                f"{180 if level == 'B2' else 230 if level == 'C1' else 280} a "
                f"{230 if level == 'B2' else 300 if level == 'C1' else 360} mots. "
                "Structure attendue: introduction, arguments, exemple, conclusion."
            ),
            "question_text": tasks[(order - 1) % len(tasks)],
            "option_a": "Production libre",
            "option_b": "Correction IA",
            "correct_option": "A",
            "summary": "La correction IA doit evaluer la clarte, la coherence, la richesse lexicale et la correction grammaticale.",
        }

    def _eo_data(self, level: str, theme: str, order: int) -> dict:
        tasks = [
            "Présentez votre point de vue sur cette situation et justifiez-le.",
            "Convainquez un interlocuteur sceptique en donnant des exemples précis.",
            "Comparez deux solutions possibles et choisissez la plus efficace.",
        ]
        expected = [
            "annoncer une position claire",
            "developper au moins deux arguments",
            "illustrer avec un exemple concret",
            "conclure avec une recommandation",
        ]
        return {
            "title": f"EO {level} - simulation {order}",
            "instruction": (
                f"Theme: {theme}. Preparation: 2 minutes. Reponse: "
                f"{2 if level == 'B2' else 3} a {3 if level == 'B2' else 4} minutes. "
                "Parlez de facon structuree et naturelle."
            ),
            "question_text": tasks[(order - 1) % len(tasks)],
            "option_a": "Production orale",
            "option_b": "Evaluation IA",
            "correct_option": "A",
            "summary": json.dumps(expected, ensure_ascii=False),
        }
