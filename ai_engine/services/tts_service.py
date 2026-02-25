import asyncio
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from django.conf import settings

# Coqui models (optionnel)
TTS_MODELS = {
    "fr": "tts_models/fr/css10/vits",
    "en": "tts_models/en/ljspeech/vits",
    "de": "tts_models/de/thorsten/vits",
}

EDGE_VOICES = {
    "fr": "fr-FR-DeniseNeural",
    "en": "en-US-JennyNeural",
    "de": "de-DE-KatjaNeural",
}

_tts_cache: dict[str, Any] = {}
_tts_lock = Lock()


def _normalize_language(language: str) -> str:
    lang = (language or "").strip().lower().replace("_", "-")
    if "-" in lang:
        lang = lang.split("-")[0]
    return lang


def _clean_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean:
        raise ValueError("Text is empty.")
    max_len = int(getattr(settings, "AI_TTS_MAX_TEXT_LEN", 2500))
    if len(clean) > max_len:
        clean = clean[:max_len]
    return clean


def _media_root() -> Path:
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_root:
        return Path(media_root)
    base_dir = getattr(settings, "BASE_DIR", Path.cwd())
    return Path(base_dir) / "media"


def _ensure_output_dir(output_dir: Optional[str]) -> Path:
    if output_dir:
        p = Path(output_dir)
        if not p.is_absolute():
            p = _media_root() / p
    else:
        p = _media_root() / "audio"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rel_media_path(abs_path: Path) -> str:
    root = _media_root()
    try:
        return abs_path.relative_to(root).as_posix()
    except ValueError:
        return abs_path.as_posix()


def _coqui_tts(language: str):
    lang = _normalize_language(language)
    if lang not in TTS_MODELS:
        raise ValueError(f"Unsupported language for Coqui: '{language}'")

    if lang in _tts_cache:
        return _tts_cache[lang]

    with _tts_lock:
        if lang in _tts_cache:
            return _tts_cache[lang]

        from TTS.api import TTS  # lazy import
        use_gpu = bool(getattr(settings, "AI_TTS_USE_GPU", False))
        _tts_cache[lang] = TTS(model_name=TTS_MODELS[lang], progress_bar=False, gpu=use_gpu)
        return _tts_cache[lang]


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _edge_save(text: str, voice: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(output_path)


def _generate_edge(text: str, language: str, output_path: Path):
    lang = _normalize_language(language)
    voice = EDGE_VOICES.get(lang, EDGE_VOICES["fr"])
    _run_async(_edge_save(text, voice, str(output_path)))


def _generate_coqui(text: str, language: str, output_path: Path):
    tts = _coqui_tts(language)
    tts.tts_to_file(text=text, file_path=str(output_path))


def _generate_gtts(text: str, language: str, output_path: Path):
    from gtts import gTTS
    lang = _normalize_language(language)
    gTTS(text=text, lang=lang).save(str(output_path))


def generate_audio(text: str, language: str, output_dir: Optional[str] = None) -> str:
    """
    Retourne un chemin relatif MEDIA, ex: 'audio/co_xxx.mp3'
    Backends (ordre): settings.AI_TTS_BACKENDS ou 'edge,coqui,gtts'
    """
    clean = _clean_text(text)
    lang = _normalize_language(language)
    out_dir = _ensure_output_dir(output_dir)

    backends = getattr(settings, "AI_TTS_BACKENDS", "edge,coqui,gtts")
    backend_list = [b.strip().lower() for b in backends.split(",") if b.strip()]

    last_error = None
    for backend in backend_list:
        try:
            if backend == "edge":
                path = out_dir / f"co_{uuid.uuid4().hex}.mp3"
                _generate_edge(clean, lang, path)
                return _rel_media_path(path)

            if backend == "coqui":
                path = out_dir / f"co_{uuid.uuid4().hex}.wav"
                _generate_coqui(clean, lang, path)
                return _rel_media_path(path)

            if backend == "gtts":
                path = out_dir / f"co_{uuid.uuid4().hex}.mp3"
                _generate_gtts(clean, lang, path)
                return _rel_media_path(path)

        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All TTS backends failed for lang='{lang}'. Last error: {last_error}")