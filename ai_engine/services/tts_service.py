"""Cached audio generation with atomic publication of complete files."""
import hashlib
import logging
import os
import tempfile
import unicodedata
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_audio(text: str, language: str = "de", output_dir: str = "audio/german") -> str:
    text = unicodedata.normalize("NFC", text.strip())
    if not text:
        raise ValueError("Le script sonore est vide.")
    language = language.strip().lower()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    directory = (media_root / output_dir).resolve()
    if directory != media_root and media_root not in directory.parents:
        raise ValueError("Le répertoire audio doit rester dans MEDIA_ROOT.")
    directory.mkdir(parents=True, exist_ok=True)
    # Public audio must be traversable by the web server, including under umask 027.
    current = directory
    while current != media_root:
        current.chmod(current.stat().st_mode | 0o001)
        current = current.parent
    # Include language and generator version; old assets remain untouched.
    digest = hashlib.sha256(("gtts-v2\0" + language + "\0" + text).encode("utf-8")).hexdigest()
    destination = directory / f"tts_{digest}.mp3"
    relative = destination.relative_to(media_root).as_posix()
    if destination.is_file() and destination.stat().st_size > 0:
        destination.chmod(0o644)
        return relative
    temporary = None
    try:
        from gtts import gTTS
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".mp3", delete=False) as stream:
            temporary = Path(stream.name)
        gTTS(text=text, lang=language).save(str(temporary))
        if temporary.stat().st_size == 0:
            raise ValueError("La génération a produit un audio vide.")
        temporary.chmod(0o644)
        os.replace(temporary, destination)
        return relative
    except Exception:
        logger.exception("Échec de génération audio (%s)", language)
        raise
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
