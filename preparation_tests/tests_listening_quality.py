import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase, override_settings
from preparation_tests.models import Exam, CourseLesson, CourseExercise
from preparation_tests.services.listening_material import spoken_text, listening_script, repair_encoding, repair_seed_text
from ai_engine.services.tts_service import generate_audio


class ListeningTests(TestCase):
    def setUp(self):
        self.exam = Exam.objects.create(code="tcf", name="TCF", language="fr")
        self.lesson = CourseLesson.objects.create(title="Écoute", slug="quality-listening", section="co",
            level="A1", content_html="<p>Méthode : écoutez attentivement.</p>", exam=self.exam)
        self.exercise = CourseExercise.objects.create(lesson=self.lesson, title="Question",
            instruction="Écoutez et répondez.", question_text="Quand ?", option_a="Lundi",
            option_b="Mardi", option_c="Jeudi", option_d="Vendredi", correct_option="C", summary="Il vient jeudi.")

    def test_instruction_and_course_are_never_audio_sources(self):
        self.assertEqual(listening_script(self.exercise), "")
        with patch("preparation_tests.management.commands.generate_exercise_audio.generate_audio") as tts:
            call_command("generate_exercise_audio", stdout=StringIO())
            tts.assert_not_called()
        self.exercise.refresh_from_db()
        self.assertIsNone(self.exercise.audio_id)

    def test_explicit_transcript_and_legacy_marker(self):
        self.exercise.document_text = "<p>Il pr&eacute;fère jeudi.</p>"
        self.assertEqual(self.exercise.listening_transcript, "Il préfère jeudi.")
        self.exercise.document_text = ""
        self.exercise.instruction = "Audio indisponible. Travaillez sur cette transcription : À bientôt !"
        self.assertEqual(listening_script(self.exercise), "À bientôt !")

    def test_dry_run_preserves_existing_data(self):
        self.exercise.document_text = "Bonjour, je préfère venir jeudi."
        self.exercise.save()
        before = list(CourseExercise.objects.values())
        with patch("preparation_tests.management.commands.generate_exercise_audio.generate_audio") as tts:
            call_command("generate_exercise_audio", dry_run=True, stdout=StringIO())
            call_command("fix_co_audio", dry_run=True, stdout=StringIO())
            tts.assert_not_called()
        self.assertEqual(list(CourseExercise.objects.values()), before)

    def test_generation_uses_document_only(self):
        self.exercise.document_text = "À jeudi !"
        self.exercise.save()
        with patch("preparation_tests.management.commands.generate_exercise_audio.generate_audio", return_value="audio/test.mp3") as tts:
            call_command("generate_exercise_audio", stdout=StringIO())
            self.assertEqual(tts.call_args.args[0], "À jeudi !")
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.audio.file.name, "audio/test.mp3")

    def test_repairs_have_backup_and_do_not_touch_normal_lessons(self):
        self.exercise.instruction = "RÃ©pondez à la question."
        self.exercise.save()
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            call_command("repair_french_encoding", stdout=StringIO())
            self.exercise.refresh_from_db()
            self.assertEqual(self.exercise.instruction, "RÃ©pondez à la question.")
            call_command("repair_french_encoding", apply=True, stdout=StringIO())
            self.exercise.refresh_from_db()
            self.assertEqual(self.exercise.instruction, "Répondez à la question.")
            files = list((Path(directory) / "output/tcf_tef_quality").glob("*.json"))
            self.assertEqual(len(files), 1)
            backup = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(backup[0]["fields"]["instruction"]["before"], "RÃ©pondez à la question.")

    def test_seed_key_and_script_are_repaired_without_regenerating_audio(self):
        from preparation_tests.management.commands.seed_tcf_advanced_content import Command
        self.lesson.slug = "tcf-advanced-co-b2-1"
        self.lesson.save()
        data = Command()._co_data("B2", "logement", 2)
        for field in ("instruction", "question_text", "option_a", "option_b", "option_c", "option_d"):
            setattr(self.exercise, field, data[field])
        self.exercise.correct_option = "C"
        self.exercise.save()
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            call_command("repair_french_encoding", apply=True, stdout=StringIO())
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.correct_option, "B")
        self.assertIn("conseiller", self.exercise.document_text)
        self.assertIsNone(self.exercise.audio_id)

    def test_all_level_audit_is_read_only(self):
        output = StringIO()
        call_command("audit_learning_materials", all_levels=True, stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(len(report["groups"]), 24)
        self.assertIn("no_dedicated_audio_script", report["lessons_to_review"][0]["flags"])


class AudioCacheTests(SimpleTestCase):
    def test_encoding_repair_preserves_valid_french(self):
        self.assertEqual(repair_encoding("École, cœur, à bientôt."), "École, cœur, à bientôt.")
        self.assertEqual(repair_encoding("cafÃ© et lâ€™Ã©cole"), "café et l’école")
        self.assertEqual(repair_seed_text("Quelle idee principale ?"), "Quelle idée principale ?")

    def test_html_entities_and_combining_accents(self):
        self.assertEqual(spoken_text("<p>caf&eacute;</p><p>e\u0301cole &amp; gare</p>"), "café\nécole & gare")

    def test_cache_separates_languages_and_preserves_accents(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            with patch("gtts.gTTS") as tts:
                tts.return_value.save.side_effect = lambda name: Path(name).write_bytes(b"mock-mp3")
                french = generate_audio("École", "fr", "audio")
                german = generate_audio("École", "de", "audio")
                self.assertNotEqual(french, german)
                self.assertEqual(generate_audio("École", "fr", "audio"), french)
                self.assertEqual(tts.call_count, 2)
                self.assertEqual(tts.call_args_list[0].kwargs["text"], "École")

    def test_cached_audio_repairs_public_file_permissions_without_regeneration(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            with patch("gtts.gTTS") as tts:
                tts.return_value.save.side_effect = lambda name: Path(name).write_bytes(b"mock-mp3")
                relative = generate_audio("Bonjour", "fr", "audio/fr/tcf_daily")
                tts.reset_mock()
                with patch.object(Path, "chmod", autospec=True) as chmod:
                    self.assertEqual(generate_audio("Bonjour", "fr", "audio/fr/tcf_daily"), relative)
                    chmod.assert_any_call(Path(directory) / relative, 0o644)
                tts.assert_not_called()

    def test_failed_generation_never_publishes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            def fail(name):
                Path(name).write_bytes(b"partial")
                raise RuntimeError("provider unavailable")
            with patch("gtts.gTTS") as tts:
                tts.return_value.save.side_effect = fail
                with self.assertRaises(RuntimeError):
                    generate_audio("Bonjour", "fr", "audio")
            self.assertEqual(list((Path(directory) / "audio").iterdir()), [])

    def test_empty_script_and_external_path_rejected(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            with self.assertRaises(ValueError):
                generate_audio("   ", "fr", "audio")
            with self.assertRaises(ValueError):
                generate_audio("Bonjour", "fr", "../outside")


class GeneratedLessonValidationTests(SimpleTestCase):
    def test_duplicate_choices_are_rejected_before_publication(self):
        from preparation_tests.management.commands.generate_tcf_content import _validate_lesson
        data = {"title": "Écoute", "intro": "Objectif", "content": "Cours", "exercises": [{
            "audio_text": "Bonjour, je viendrai jeudi.", "question_text": "Quand ?",
            "option_a": "Jeudi", "option_b": "Jeudi", "option_c": "Lundi", "option_d": "Mardi",
            "correct_option": "A", "explanation": "Il dit jeudi."}]}
        with self.assertRaises(ValueError):
            _validate_lesson(data, 1, "co")
        data["exercises"][0]["option_b"] = "Vendredi"
        _validate_lesson(data, 1, "co")
        data["exercises"][0]["audio_text"] = ""
        with self.assertRaises(ValueError):
            _validate_lesson(data, 1, "co")
