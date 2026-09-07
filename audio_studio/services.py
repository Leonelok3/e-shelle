import math
import os
import wave
from pathlib import Path

import requests
from django.conf import settings
from django.core.files import File


SAMPLE_RATE = 44100
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"


def generate_voiceover_audio(job):
    """Genere une voix-off. Mode local = vraie synthese vocale OpenAI. Mode clone = voix personnelle (a venir)."""
    if job.mode == "clone":
        return _generate_clone_placeholder(job)
    return _generate_openai_voiceover(job)


def _generate_openai_voiceover(job):
    """Appelle l'API OpenAI Text-to-Speech (tts-1-hd) pour produire un vrai fichier audio parle."""
    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY n'est pas configuree sur le serveur.")

    script = (job.script or "").strip()
    if not script:
        raise ValueError("Le texte de la voix-off est vide.")

    response = requests.post(
        OPENAI_TTS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "tts-1-hd",
            "voice": job.openai_voice or "nova",
            "input": script[:4000],
            "response_format": "mp3",
        },
        timeout=120,
    )
    if response.status_code >= 400:
        message = "Erreur de l'API OpenAI Text-to-Speech."
        try:
            message = response.json().get("error", {}).get("message", message)
        except ValueError:
            pass
        raise RuntimeError(message)

    media_path = _media_output_path("voiceovers", f"voiceover_{job.pk}.mp3")
    media_path.write_bytes(response.content)

    with media_path.open("rb") as fh:
        job.audio_file.save(media_path.name, File(fh), save=False)
    # Estimation simple : ~2,5 mots par seconde en lecture naturelle.
    job.duration_seconds = max(1, round(len(script.split()) / 2.5))
    job.status = job.Status.DONE
    job.error_message = ""
    job.save(update_fields=["audio_file", "duration_seconds", "status", "error_message"])
    return job


def generate_music_track(job):
    """Genere une musique de fond locale simple en WAV."""
    media_path = _media_output_path("music", f"music_{job.pk}.wav")
    duration = max(5, min(int(job.duration_seconds or 20), 120))
    mood = job.mood or "afrobeat"

    patterns = {
        "afrobeat": [(220, .16), (330, .12), (392, .12), (440, .18), (330, .1), (494, .14)],
        "corporate": [(262, .22), (330, .22), (392, .22), (523, .26)],
        "emotional": [(196, .35), (262, .35), (330, .35), (294, .35)],
        "ambient": [(174, .5), (220, .5), (261, .5), (329, .5)],
        "energetic": [(330, .12), (440, .12), (554, .12), (660, .16), (554, .1), (440, .1)],
    }
    pattern = patterns.get(mood, patterns["afrobeat"])
    samples = []
    elapsed = 0.0
    i = 0
    while elapsed < duration:
        freq, beat = pattern[i % len(pattern)]
        samples.extend(_tone(freq, min(beat, duration - elapsed), volume=.32))
        elapsed += beat
        i += 1
    _write_wav(media_path, samples)

    with media_path.open("rb") as fh:
        job.audio_file.save(media_path.name, File(fh), save=False)
    job.status = job.Status.DONE
    job.error_message = ""
    job.save(update_fields=["audio_file", "status", "error_message"])
    return job


def _generate_clone_placeholder(job):
    """Point d'integration futur pour ElevenLabs/PlayHT/Resemble/etc.
    Le clonage de la voix personnelle de l'utilisateur n'est pas fourni par
    l'API OpenAI publique : il faut un fournisseur specialise (ElevenLabs...)
    non encore connecte a E-Shelle."""
    if not job.voice_profile:
        raise ValueError("Selectionnez une voix enregistree pour le mode voix clonee.")
    if not job.voice_profile.consent_confirmed:
        raise ValueError("Consentement vocal obligatoire.")
    raise ValueError(
        "Le clonage de votre voix personnelle n'est pas encore disponible : cela demande "
        "un fournisseur specialise non connecte pour le moment. Utilisez le mode "
        "« Voix IA (OpenAI) » en attendant."
    )


def _media_output_path(kind, filename):
    path = Path(settings.MEDIA_ROOT) / "audio_studio" / kind
    path.mkdir(parents=True, exist_ok=True)
    return path / filename


def _tone(freq, seconds, volume=.3):
    count = max(1, int(SAMPLE_RATE * seconds))
    return [
        int(32767 * volume * math.sin(2 * math.pi * freq * (i / SAMPLE_RATE)))
        for i in range(count)
    ]


def _silence(seconds):
    return [0] * max(1, int(SAMPLE_RATE * seconds))


def _write_wav(path, samples):
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for sample in samples:
            sample = max(-32767, min(32767, int(sample)))
            frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
        wav.writeframes(bytes(frames))
