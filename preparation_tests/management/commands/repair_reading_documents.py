"""Explicit, bounded production repair preserving learner history."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from preparation_tests.models import CourseLesson, CourseExercise
from preparation_tests.services.reading_documents import generate_document


class Command(BaseCommand):
    help = 'Audit missing CE documents, or generate reviewed replacements with --apply.'

    def add_arguments(self, parser):
        parser.add_argument('--lesson', type=int, required=True)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--limit', type=int, default=5)

    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 10:
            raise CommandError('Limit must be between 1 and 10.')
        lesson = CourseLesson.objects.filter(pk=options['lesson'], section='ce').first()
        if not lesson:
            raise CommandError('Reading lesson not found.')
        rows = list(lesson.exercises.filter(is_active=True, document_text='').order_by('order', 'id')[:options['limit']])
        self.stdout.write(f'Lesson {lesson.pk}: {len(rows)} exercise(s) without a separate document.')
        if not options['apply'] or not rows:
            self.stdout.write('Audit only; use --apply to generate. No API calls or writes.')
            return
        snapshot = [(row.pk, row.instruction, row.question_text, row.correct_option,
                     row.option_a, row.option_b, row.option_c, row.option_d) for row in rows]
        existing = list(lesson.exercises.filter(is_active=True).exclude(document_text='').values(
            'document_title', 'document_text', 'question_text'))
        generated, titles = [], [r['document_title'] for r in existing]
        for index, row in enumerate(rows, 1):
            self.stdout.write(f'Generating and reviewing document {index}/{len(rows)}...', ending='\n')
            try:
                data = generate_document(lesson, row.order, titles)
                if any(data['document'] == r['document_text'] or data['question'] == r['question_text'] for r in existing):
                    raise ValueError('Document or question already exists in this lesson')
                if any(data['document'] == other['document'] or data['question'] == other['question']
                       for other in generated):
                    raise ValueError('Repeated document or question')
                generated.append(data)
                titles.append(data['title'])
            except Exception as exc:
                # Provider exceptions can contain credentials; never print their messages.
                raise CommandError(f'Generation/validation failed ({type(exc).__name__}). No exercise changed.') from None
        with transaction.atomic():
            CourseLesson.objects.select_for_update().get(pk=lesson.pk)
            current = list(CourseExercise.objects.select_for_update().filter(
                pk__in=[r.pk for r in rows], is_active=True, document_text='').order_by('order', 'id'))
            actual = [(r.pk, r.instruction, r.question_text, r.correct_option,
                       r.option_a, r.option_b, r.option_c, r.option_d) for r in current]
            if actual != snapshot:
                raise CommandError('Lesson changed during generation. Nothing saved; audit again.')
            for old, data in zip(current, generated):
                new = CourseExercise.objects.create(lesson=lesson, title=data['title'],
                    document_title=data['title'], document_text=data['document'],
                    instruction='Lisez le document puis répondez à la question.',
                    question_text=data['question'], correct_option=data['answer'],
                    summary=data['explanation'] + '\nIndice dans le document : ' + data['evidence'],
                    order=old.order, is_active=True,
                    **{'option_' + key.lower(): value for key, value in data['options'].items()})
                new.competency_tags.set(old.competency_tags.all())
                old.is_active = False
                old.save(update_fields=['is_active'])
        self.stdout.write(self.style.SUCCESS(f'{len(generated)} documents published. Previous exercises and history preserved.'))
