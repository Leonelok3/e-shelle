"""Validate the editable story before a render is reserved."""

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from .ffmpeg_filters import SAFE_ZONES


def transcription_available():
    return bool(getattr(settings, "OPENAI_API_KEY", "").strip())


def parse_storyboard(data, campaign):
    fields = {}
    for key, limit in (("hook", 85), ("detail", 95), ("cta", 45)):
        value = data.get(key) or ""
        if not isinstance(value, str) or len(value) > limit:
            raise ValidationError(f"Le champ {key} doit contenir au plus {limit} caractères.")
        if value.strip():
            fields[key] = " ".join(value.split())
    if "hook" not in fields and data.get("channel"):
        fields["hook"] = campaign.nom_produit[:85]
    if "cta" not in fields and campaign.offer_kind == "bien":
        fields["cta"] = "Demander une visite"
    channel = data.get("channel") or "reels"
    if not isinstance(channel, str) or channel not in SAFE_ZONES:
        raise ValidationError("Choisis une destination vidéo valide.")
    fields["channel"] = channel
    raw = data.get("captions") or ""
    if not isinstance(raw, str) or len(raw) > 1500:
        raise ValidationError("Les sous-titres sont trop longs.")
    fields["captions"] = []
    for line in filter(str.strip, raw.splitlines()):
        match = re.fullmatch(r"\s*(\d{1,2}(?:[.,]\d{1,3})?)\s*-\s*(\d{1,2}(?:[.,]\d{1,3})?)\s*\|\s*(.{1,85})", line)
        if not match:
            raise ValidationError("Sous-titres : écris une ligne par phrase au format 0.5 - 3.2 | Mon texte.")
        start, end = (float(value.replace(",", ".")) for value in match.groups()[:2])
        if not 0 <= start < end <= 15 or (fields["captions"] and start < fields["captions"][-1][1]):
            raise ValidationError("Les sous-titres doivent se suivre entre 0 et 15 secondes.")
        fields["captions"].append([start, end, match[3].strip()])
    fields["auto_captions"] = data.get("auto_captions") in (True, "true", "1", "on") and not fields["captions"]
    if fields["auto_captions"] and not transcription_available():
        raise ValidationError("La transcription est indisponible. Renseigne les sous-titres à la main.")
    return fields


def transcribe_captions(voice, duration):
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=20, max_retries=0)
    limit = 20 * 1024 * 1024
    with voice.audio_file.open("rb") as audio:
        content = audio.read(limit + 1)
    if len(content) > limit:
        raise ValueError("La narration dépasse la taille maximale de transcription.")
    result = client.audio.transcriptions.create(
        model="whisper-1", file=(Path(voice.audio_file.name).name, content),
        response_format="verbose_json", timestamp_granularities=["word"],
    )
    captions = []
    words = []
    start = end = 0
    for item in result.words or []:
        word = item.word.strip()
        if not word or item.start >= duration:
            continue
        if words and (len(" ".join(words)) + len(word) > 38 or item.end - start > 2.8 or item.start - end > .55):
            captions.append([start, end, " ".join(words)])
            words = []
        if not words:
            start = max(round(item.start, 3), captions[-1][1] if captions else 0)
        end = min(duration, round(item.end, 3))
        if end > start:
            words.append(word)
    if words:
        captions.append([start, end, " ".join(words)])
    return captions
