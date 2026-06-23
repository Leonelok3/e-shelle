import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenAITTSService:
    """Service to generate voice using OpenAI Text-to-Speech (TTS) API."""

    def __init__(self) -> None:
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")

    def generate(self, text: str, output_path: Path, voice: str = "onyx", model: str = "tts-1") -> Path:
        """
        Converts text to speech using OpenAI API.
        Saves output audio file to output_path.
        Falls back to local Piper or Coqui generator if api_key is missing or API fails.
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY is not configured. Falling back to local TTS engine.")
            return self._fallback_local(text, output_path)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Generating OpenAI TTS for text length: {len(text)} using voice: {voice}")
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            response.write_to_file(str(output_path))
            return output_path
        except Exception as e:
            logger.error(f"OpenAI TTS generation failed: {e}. Falling back to local TTS engine.")
            return self._fallback_local(text, output_path)

    def _fallback_local(self, text: str, output_path: Path) -> Path:
        """Fallback to the local voice generator service or free gTTS."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try free gTTS first as it doesn't require keys and works natively in French
        try:
            from gtts import gTTS
            logger.info("Attempting to generate French voice-over using free gTTS...")
            tts = gTTS(text=text, lang='fr')
            tts.save(str(output_path))
            logger.info("Voice-over generated successfully via gTTS.")
            return output_path
        except Exception as e:
            logger.warning(f"gTTS voice generation failed: {e}. Trying local system fallback...")

        from voices.services import LocalVoiceService
        service = LocalVoiceService()
        
        try:
            if service.backend == 'piper':
                service._generate_with_piper(text, output_path)
            else:
                service._generate_with_coqui(text, output_path)
        except Exception as e:
            logger.error(f"Fallback local TTS engine failed: {e}. Generating silent wave.")
            # Fallback to silent WAV
            service._create_silent_wav(output_path, duration_seconds=max(5.0, len(text) * 0.1))
        
        return output_path
