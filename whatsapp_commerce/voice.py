"""Transcribe inbound business audio with the sending business's Meta token."""

import io
from django.conf import settings

from whatsapp_agent.media import MB, retrieve_media
from .onboarding import _graph_url

EXTENSIONS = {
    "audio/ogg": "ogg", "audio/opus": "ogg", "audio/mpeg": "mp3",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/webm": "webm", "audio/mp4": "m4a",
}


def voice_available():
    return bool(getattr(settings, "WHATSAPP_INBOUND_VOICE_ENABLED", False) and getattr(settings, "OPENAI_API_KEY", ""))


def transcribe_voice(connection, message):
    from openai import OpenAI

    with io.BytesIO() as audio:
        mime = retrieve_media(
            message.media_id, connection.get_access_token(), audio, max_bytes=8 * MB,
            phone_number_id=connection.phone_number_id, media_kind="audio",
            graph_base=_graph_url("").rstrip("/"),
        )
        if mime not in EXTENSIONS:
            return ""
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30.0, max_retries=0)
        result = client.audio.transcriptions.create(
            model=getattr(settings, "OPENAI_TRANSCRIBE_MODEL", "whisper-1"),
            file=(f"note.{EXTENSIONS[mime]}", audio, mime),
            prompt="Transcris fidèlement sans traduire, y compris si le message est en français, anglais ou pidgin.",
        )
        return (result.text or "").strip()[:2000]
