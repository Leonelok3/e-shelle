"""Read-only inventory of advanced training material. No AI calls or repairs."""
import json
import re
from collections import Counter
from django.core.management.base import BaseCommand
from django.db.models import Q, Prefetch
from django.utils.html import strip_tags
from preparation_tests.models import CourseLesson, CourseExercise


def normalized(text):
    return re.sub(r'\s+', ' ', strip_tags(text or '')).strip().casefold()


class Command(BaseCommand):
    help = 'Audit published C1/C2 lessons and active exercises without modifying content.'

    def add_arguments(self, parser):
        parser.add_argument('--exam', choices=['tcf', 'tef'], default='tcf')
        parser.add_argument('--check-audio-files', action='store_true')

    def handle(self, *args, **options):
        exam = options['exam']
        lessons = CourseLesson.objects.filter(is_published=True, level__in=['C1', 'C2']).filter(
            Q(exam__code__iexact=exam) | Q(exams__code__iexact=exam)).distinct().prefetch_related(
                Prefetch('exercises', queryset=CourseExercise.objects.filter(is_active=True).select_related('audio')))
        groups = {(level, skill): {'level': level, 'skill': skill, 'lessons': 0, 'exercises': 0,
            'separate_documents': 0, 'audio_references': 0} for level in ['C1', 'C2'] for skill in ['ce', 'co', 'ee', 'eo']}
        issues = []
        for lesson in lessons:
            group = groups.get((lesson.level, lesson.section))
            if group is None:
                continue
            group['lessons'] += 1
            exercises = list(lesson.exercises.all())
            group['exercises'] += len(exercises)
            flags = Counter()
            if not normalized(lesson.content_html):
                flags['empty_lesson_content'] += 1
            if not exercises:
                flags['no_active_exercises'] += 1
            questions, documents = [], []
            for exercise in exercises:
                question = normalized(exercise.question_text)
                if not question:
                    flags['empty_question_or_task'] += 1
                else:
                    questions.append(question)
                if lesson.section in ['ce', 'co']:
                    choices = [getattr(exercise, 'option_' + letter) for letter in 'abcd']
                    if any(not normalized(value) for value in choices):
                        flags['incomplete_answer_choices'] += 1
                    if len({normalized(value) for value in choices}) != 4:
                        flags['duplicate_answer_choices'] += 1
                    if exercise.correct_option not in 'ABCD' or len(exercise.correct_option) != 1:
                        flags['invalid_answer_key'] += 1
                    if not normalized(exercise.summary):
                        flags['missing_explanation'] += 1
                if lesson.section == 'ce':
                    if normalized(exercise.document_text):
                        group['separate_documents'] += 1
                        documents.append(normalized(exercise.document_text))
                        if not normalized(exercise.document_title):
                            flags['missing_document_title'] += 1
                    else:
                        flags['no_separate_document_review_legacy_instruction'] += 1
                        if not normalized(exercise.instruction):
                            flags['no_exercise_reading_support'] += 1
                    if 'une enquete recente montre que les usagers acceptent' in normalized(exercise.instruction):
                        flags['generic_seed_document'] += 1
                if lesson.section == 'co':
                    asset = exercise.audio
                    if not asset or asset.kind != 'audio' or not asset.file:
                        flags['missing_audio_reference'] += 1
                    else:
                        group['audio_references'] += 1
                        if options['check_audio_files']:
                            try:
                                if not asset.file.storage.exists(asset.file.name):
                                    flags['audio_file_not_found'] += 1
                            except Exception:
                                flags['audio_storage_check_failed'] += 1
            for key, values in [('repeated_questions', questions), ('repeated_documents', documents)]:
                excess = sum(count - 1 for count in Counter(values).values() if count > 1)
                if excess:
                    flags[key] = excess
            if flags:
                issues.append({'lesson': lesson.pk, 'level': lesson.level, 'skill': lesson.section,
                               'title': lesson.title, 'flags': dict(flags)})
        report = {'exam': exam, 'read_only': True, 'groups': list(groups.values()),
                  'missing_groups': [f'{level}/{skill}' for (level, skill), g in groups.items() if not g['lessons']],
                  'lessons_to_review': issues,
                  'limits': 'Presence and structure only; not pedagogical certification. Legacy instructions may contain valid documents. Audio existence does not validate playback or transcription. EE/EO need a real learner submission test.'}
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
