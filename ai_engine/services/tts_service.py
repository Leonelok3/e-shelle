import uuid
from pathlib import Path
from django.conf import settings
from TTS.api import TTS

TTS_MODELS = {
    "fr": "tts_models/fr/css10/vits",
    "en": "tts_models/en/ljspeech/vits",
    "de": "tts_models/de/thorsten/vits",
}

_tts_cache = {}

def get_tts(language: str) -> TTS:
    if language not in _tts_cache:
        _tts_cache[language] = TTS(
            model_name=TTS_MODELS[language],
            progress_bar=False,
            gpu=False  # 🔒 FORCÉ CPU
        )
    return _tts_cache[language]

def generate_audio(text: str, language: str) -> str:
    tts = get_tts(language)

    filename = f"co_{uuid.uuid4()}.mp3"
    output_dir = Path(settings.MEDIA_ROOT) / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename
    tts.tts_to_file(text=text, file_path=str(output_path))

    return f"audio/{filename}"
