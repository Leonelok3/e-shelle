from django.db import models

# Create your models here.
from django.db import models

class Letter(models.Model):
    SOURCE_CHOICES = [
        ("form", "Formulaire"),
        ("cv", "Depuis CV"),
    ]
    TONE_CHOICES = [("pro", "Pro"), ("convaincant", "Convaincant"), ("sobre", "Sobre")]
    LANG_CHOICES = [("fr", "Français"), ("en", "English")]

    full_name   = models.CharField(max_length=120)
    email       = models.EmailField(blank=True)
    phone       = models.CharField(max_length=50, blank=True)
    target_role = models.CharField(max_length=160, blank=True)
    company     = models.CharField(max_length=160, blank=True)
    keywords    = models.TextField(blank=True)
    language    = models.CharField(max_length=2, choices=LANG_CHOICES, default="fr")
    tone        = models.CharField(max_length=12, choices=TONE_CHOICES, default="pro")
    source      = models.CharField(max_length=8, choices=SOURCE_CHOICES, default="form")
    content     = models.TextField()              # la lettre complète
    ats_score   = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        base = self.full_name or "Lettre"
        return f"{base} — {self.target_role or 'Poste'} @ {self.company or 'Entreprise'}"
