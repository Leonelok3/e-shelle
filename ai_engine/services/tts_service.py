import uuid
from pathlib import Path
from typing import Any

from django.conf import settings

TTS_MODELS = {
    "fr": "tts_models/fr/css10/vits",
    "en": "tts_models/en/ljspeech/vits",
    "de": "tts_models/de/thorsten/vits",
}

_tts_cache: dict[str, Any] = {}


def get_tts(language: str):
    lang = (language or "").strip().lower()
    if lang not in TTS_MODELS:
        raise ValueError(f"Unsupported language: '{language}'. Allowed: {list(TTS_MODELS.keys())}")

    if lang not in _tts_cache:
        try:
            from TTS.api import TTS  # lazy import
        except ImportError as e:
            raise RuntimeError(
                "Coqui TTS is not installed. Install it with: pip install TTS"
            ) from e

        _tts_cache[lang] = TTS(
            model_name=TTS_MODELS[lang],
            progress_bar=False,
            gpu=False,
        )
    return _tts_cache[lang]


def generate_audio(text: str, language: str) -> str:
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Text is empty.")

    tts = get_tts(language)

    filename = f"co_{uuid.uuid4()}.mp3"
    output_dir = Path(settings.MEDIA_ROOT) / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename
    tts.tts_to_file(text=clean_text, file_path=str(output_path))

    return f"audio/{filename}"