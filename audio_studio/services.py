import math
import re
import wave
from pathlib import Path

from django.conf import settings
from django.core.files import File


SAMPLE_RATE = 44100


def generate_voiceover_audio(job):
    """Genere une voix-off. En local, produit un guide audio WAV testable."""
    if job.mode == "clone":
        return _generate_clone_placeholder(job)
    return _generate_local_voice_guide(job)


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


def _generate_local_voice_guide(job):
    """Guide audio local: rythme syllabique pour caler une voix-off en montage."""
    words = re.findall(r"\w+", job.script, flags=re.UNICODE)
    duration = max(3, min(len(words) // 2 + 2, 90))
    media_path = _media_output_path("voiceovers", f"voiceover_{job.pk}.wav")

    samples = []
    intro = _tone(660, .12, volume=.25) + _silence(.08) + _tone(880, .12, volume=.25)
    samples.extend(intro)
    samples.extend(_silence(.25))
    for index, word in enumerate(words[:180]):
        freq = 420 + (len(word) % 8) * 35
        samples.extend(_tone(freq, .055, volume=.2))
        samples.extend(_silence(.055 if index % 7 else .13))
    remaining = duration - (len(samples) / SAMPLE_RATE)
    if remaining > 0:
        samples.extend(_silence(remaining))
    _write_wav(media_path, samples)

    with media_path.open("rb") as fh:
        job.audio_file.save(media_path.name, File(fh), save=False)
    job.duration_seconds = int(len(samples) / SAMPLE_RATE)
    job.status = job.Status.DONE
    job.error_message = "Mode test local: audio guide genere. Branchez un fournisseur de clonage vocal pour obtenir votre vraie voix."
    job.save(update_fields=["audio_file", "duration_seconds", "status", "error_message"])
    return job


def _generate_clone_placeholder(job):
    """Point d'integration futur pour ElevenLabs/PlayHT/Resemble/etc."""
    if not job.voice_profile:
        raise ValueError("Selectionnez une voix enregistree pour le mode voix clonee.")
    if not job.voice_profile.consent_confirmed:
        raise ValueError("Consentement vocal obligatoire.")
    # Tant que le fournisseur n'est pas configure, on genere un guide local.
    return _generate_local_voice_guide(job)


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
