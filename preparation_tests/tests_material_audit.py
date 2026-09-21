import json
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from preparation_tests.models import Exam, CourseLesson, CourseExercise


class MaterialAuditTests(TestCase):
    def report(self):
        output = StringIO()
        call_command('audit_learning_materials', stdout=output)
        return json.loads(output.getvalue())

    def test_empty_curriculum_reports_all_missing_groups(self):
        report = self.report()
        self.assertEqual(len(report['missing_groups']), 8)
        self.assertTrue(report['read_only'])

    def test_shared_exam_counted_once_and_inactive_history_ignored(self):
        exam = Exam.objects.create(code='tcf', name='TCF', language='fr')
        lesson = CourseLesson.objects.create(exam=exam, title='Lecture', slug='audit-reading',
            section='ce', level='C1', is_published=True, content_html='<p>Cours</p>')
        lesson.exams.add(exam)
        CourseExercise.objects.create(lesson=lesson, title='Ancien', is_active=False)
        exercise = CourseExercise.objects.create(lesson=lesson, title='Question',
            question_text='Quand ?', option_a='Lundi', option_b='Mardi',
            option_c='Mercredi', option_d='Jeudi', correct_option='A', summary='Explication')
        before = list(CourseExercise.objects.values())
        report = self.report()
        group = next(g for g in report['groups'] if g['level'] == 'C1' and g['skill'] == 'ce')
        self.assertEqual(group['lessons'], 1)
        self.assertEqual(group['exercises'], 1)
        flags = report['lessons_to_review'][0]['flags']
        self.assertEqual(flags['no_exercise_reading_support'], 1)
        self.assertEqual(list(CourseExercise.objects.values()), before)
        exercise.document_text = 'Un document lisible.'
        exercise.document_title = 'Horaires'
        exercise.save()
        self.assertEqual(self.report()['lessons_to_review'], [])
