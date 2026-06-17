from django.conf import settings
from django.db import models


class VoiceProfile(models.Model):
    """Voix autorisee par l'utilisateur pour generer des voix-off."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_profiles")
    name = models.CharField(max_length=120)
    sample = models.FileField(upload_to="audio_studio/voice_samples/")
    consent_confirmed = models.BooleanField(default=False)
    consent_note = models.CharField(max_length=240, blank=True)
    provider_voice_id = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profil voix"
        verbose_name_plural = "Profils voix"

    def __str__(self):
        return f"{self.name} - {self.owner}"


class VoiceOverJob(models.Model):
    """Generation de voix-off depuis un texte."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        DONE = "done", "Termine"
        FAILED = "failed", "Echec"

    class Mode(models.TextChoices):
        LOCAL = "local", "Test local"
        CLONE = "clone", "Voix clonee"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voiceover_jobs")
    voice_profile = models.ForeignKey(VoiceProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    title = models.CharField(max_length=160)
    script = models.TextField()
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.LOCAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    audio_file = models.FileField(upload_to="audio_studio/voiceovers/", blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Voix-off"
        verbose_name_plural = "Voix-off"

    def __str__(self):
        return self.title


class MusicTrackJob(models.Model):
    """Generation de musique de fond pour video."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        DONE = "done", "Termine"
        FAILED = "failed", "Echec"

    MOOD_CHOICES = [
        ("afrobeat", "Afrobeat dynamique"),
        ("corporate", "Corporate positif"),
        ("emotional", "Emotionnel / storytelling"),
        ("ambient", "Ambiance douce"),
        ("energetic", "Promo energique"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="music_track_jobs")
    title = models.CharField(max_length=160)
    prompt = models.TextField()
    mood = models.CharField(max_length=30, choices=MOOD_CHOICES, default="afrobeat")
    duration_seconds = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    audio_file = models.FileField(upload_to="audio_studio/music/", blank=True, null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Musique video"
        verbose_name_plural = "Musiques video"

    def __str__(self):
        return self.title
