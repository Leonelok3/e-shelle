import sys
from TTS.api import TTS
from pathlib import Path
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "media" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "fr": "tts_models/fr/css10/vits",
    "en": "tts_models/en/ljspeech/vits",
}

tts_cache = {}

def generate(text, lang):
    if lang not in tts_cache:
        tts_cache[lang] = TTS(MODELS[lang], gpu=False)

    filename = f"{uuid.uuid4()}.wav"
    path = AUDIO_DIR / filename
    tts_cache[lang].tts_to_file(text=text, file_path=str(path))
    print(path)

if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2])
