from pathlib import Path
from django.conf import settings


class VoiceGenerator:
    """Wrapper to select Piper or Coqui for generating TTS."""

    def __init__(self):
        self.backend = settings.VOICE_BACKEND.lower()

    def generate(self, text: str, output_path: Path, language: str = 'fr') -> Path:
        from voices.services import LocalVoiceService

        service = LocalVoiceService()
        # LocalVoiceService already handles backend selection
        return service._generate_for_text(text=text, output_path=output_path) if hasattr(service, '_generate_for_text') else service.generate_for_scene_dummy(text, output_path)
