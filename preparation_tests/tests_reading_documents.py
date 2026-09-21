from io import StringIO
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command, CommandError
from preparation_tests.models import CourseLesson, CourseExercise
from preparation_tests.services.reading_documents import validate_document


class ReadingDocumentTests(TestCase):
    def setUp(self):
        self.lesson = CourseLesson.objects.create(title='Bibliothèque', slug='reading-document-test',
            section='ce', level='A1', is_published=True)
        self.old = CourseExercise.objects.create(lesson=self.lesson, title='Question',
            instruction='Document absent', question_text='Quand ?', option_a='Lundi',
            option_b='Mardi', option_c='Mercredi', option_d='Jeudi', correct_option='A')
        self.data = dict(title='Horaires de la bibliothèque', document=(
            'La bibliothèque ouvre le lundi à neuf heures. Les lecteurs peuvent emprunter trois livres. '
            'Ils doivent présenter leur carte à l’accueil. Le retour des livres se fait dans la boîte '
            'près de la porte. Les enfants sont les bienvenus.'), question='Quel jour ouvre la bibliothèque ?',
            options={'A': 'Lundi', 'B': 'Mardi', 'C': 'Mercredi', 'D': 'Jeudi'}, answer='A',
            evidence='La bibliothèque ouvre le lundi à neuf heures.', explanation='Le jour est indiqué dans la première phrase.')

    @patch('preparation_tests.management.commands.repair_reading_documents.generate_document')
    def test_default_is_read_only(self, generate):
        call_command('repair_reading_documents', lesson=self.lesson.pk, stdout=StringIO())
        generate.assert_not_called()
        self.assertEqual(CourseExercise.objects.count(), 1)

    @patch('preparation_tests.management.commands.repair_reading_documents.generate_document')
    def test_replacement_preserves_original_and_is_idempotent(self, generate):
        generate.return_value = self.data
        call_command('repair_reading_documents', lesson=self.lesson.pk, apply=True, stdout=StringIO())
        self.old.refresh_from_db()
        self.assertFalse(self.old.is_active)
        self.assertEqual(self.old.question_text, 'Quand ?')
        new = CourseExercise.objects.get(is_active=True)
        self.assertEqual(new.document_text, self.data['document'])
        call_command('repair_reading_documents', lesson=self.lesson.pk, apply=True, stdout=StringIO())
        self.assertEqual(generate.call_count, 1)

    @patch('preparation_tests.management.commands.repair_reading_documents.generate_document')
    def test_generation_failure_does_not_change_exercises(self, generate):
        generate.side_effect = RuntimeError('provider unavailable')
        with self.assertRaises(CommandError):
            call_command('repair_reading_documents', lesson=self.lesson.pk, apply=True, stdout=StringIO())
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_active)
        self.assertEqual(CourseExercise.objects.count(), 1)

    def test_validation_rejects_missing_evidence_and_repeated_options(self):
        self.assertEqual(validate_document(self.data, 'A1'), self.data)
        with self.assertRaises(ValueError):
            validate_document({**self.data, 'evidence': 'Une citation qui ne figure pas dans le texte.'}, 'A1')
        with self.assertRaises(ValueError):
            validate_document({**self.data, 'options': dict.fromkeys('ABCD', 'Lundi')}, 'A1')

    def test_document_is_escaped_in_template(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        self.old.document_text = '<script>alert(1)</script>'
        self.old.document_title = 'Document de lecture'
        rendered = render_to_string('preparation_tests/partials/reading_document.html', {'exercise': self.old})
        self.assertIn('Document de lecture', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertNotIn('<script>alert(1)</script>', rendered)
