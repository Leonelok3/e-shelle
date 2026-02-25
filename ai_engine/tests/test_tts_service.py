import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from ai_engine.services import tts_service


class TTSServiceTests(SimpleTestCase):
    def setUp(self):
        tts_service._tts_cache.clear()

    def test_get_tts_unsupported_language_raises(self):
        with self.assertRaises(ValueError) as ctx:
            tts_service.get_tts("es")
        self.assertIn("Unsupported language", str(ctx.exception))

    def test_generate_audio_empty_text_raises(self):
        with self.assertRaises(ValueError) as ctx:
            tts_service.generate_audio("   ", "fr")
        self.assertEqual(str(ctx.exception), "Text is empty.")

    @patch("ai_engine.services.tts_service.uuid.uuid4", return_value="fixed-id")
    def test_generate_audio_calls_tts_and_returns_relative_path(self, _uuid_mock):
        fake_tts = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                with patch("ai_engine.services.tts_service.get_tts", return_value=fake_tts) as get_tts_mock:
                    result = tts_service.generate_audio("  Bonjour test  ", "FR")

        expected_rel = "audio/co_fixed-id.mp3"
        self.assertEqual(result, expected_rel)
        get_tts_mock.assert_called_once_with("FR")

        expected_abs = str(Path(tmpdir) / "audio" / "co_fixed-id.mp3")
        fake_tts.tts_to_file.assert_called_once_with(
            text="Bonjour test",
            file_path=expected_abs,
        )