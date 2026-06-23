import subprocess
import wave
from pathlib import Path

from django.conf import settings
from moviepy.editor import AudioFileClip


class LocalVoiceService:
    """Génère la voix off localement avec Coqui TTS ou Piper TTS."""

    def __init__(self) -> None:
        self.backend = settings.VOICE_BACKEND.lower()

    def generate_for_scene(self, scene, text: str) -> Path:
        output_dir = settings.MEDIA_ROOT / 'generated' / 'audio'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'project_{scene.project_id}_scene_{scene.order}.wav'

        try:
            if self.backend == 'piper':
                self._generate_with_piper(text, output_path)
            else:
                self._generate_with_coqui(text, output_path)
        except Exception:
            self._create_silent_wav(output_path, max(scene.duration_seconds, 2.0))

        try:
            clip = AudioFileClip(str(output_path))
            scene.duration_seconds = max(float(clip.duration), scene.duration_seconds)
            scene.save(update_fields=['duration_seconds'])
            clip.close()
        except Exception:
            pass
        return output_path

    def _generate_with_coqui(self, text: str, output_path: Path) -> None:
        from TTS.api import TTS

        tts = TTS(model_name=settings.COQUI_TTS_MODEL, progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(output_path))

    def _generate_with_piper(self, text: str, output_path: Path) -> None:
        command = [settings.PIPER_EXE, '--model', settings.PIPER_MODEL, '--output_file', str(output_path)]
        subprocess.run(command, input=text, text=True, check=True, capture_output=True)

    def _create_silent_wav(self, output_path: Path, duration_seconds: float) -> None:
        sample_rate = 22050
        frames = int(sample_rate * duration_seconds)
        with wave.open(str(output_path), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b'\x00\x00' * frames)
