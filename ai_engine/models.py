"""
ai_engine/models.py — Moteur de génération IA E-Shelle
Historique des générations, templates de prompts.
"""
from django.db import models
from django.conf import settings


class GenerationIA(models.Model):
    """Enregistre chaque génération de contenu par l'IA."""
    TYPES = [
        ("cours",          "Plan de cours complet"),
        ("lecon",          "Contenu de leçon"),
        ("quiz",           "Questions de quiz"),
        ("description",    "Description produit/formation"),
        ("article",        "Article de blog"),
        ("email",          "Email marketing"),
        ("devis",          "Devis automatique"),
        ("faq",            "FAQ"),
        ("autre",          "Autre"),
    ]
    STATUTS = [
        ("en_cours",  "En cours"),
        ("succes",    "Succès"),
        ("erreur",    "Erreur"),
    ]

    utilisateur  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name="generations_ia", null=True, blank=True)
    type_gen     = models.CharField(max_length=20, choices=TYPES, default="autre")
    modele       = models.CharField(max_length=100, default="",
                                     help_text="Modèle IA utilisé")
    prompt       = models.TextField(help_text="Prompt envoyé au modèle")
    resultat     = models.TextField(blank=True, help_text="Résultat généré")
    parametres   = models.JSONField(default=dict, blank=True,
                                     help_text="Paramètres (langue, niveau, ton, etc.)")
    tokens_input  = models.PositiveIntegerField(default=0)
    tokens_output = models.PositiveIntegerField(default=0)
    statut       = models.CharField(max_length=20, choices=STATUTS, default="en_cours")
    erreur       = models.TextField(blank=True)
    # Contenu sauvegardé en BDD (lien vers formation/produit)
    sauvegarde   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    duree_ms     = models.PositiveIntegerField(default=0, help_text="Durée de génération en ms")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Génération IA"
        verbose_name_plural = "Générations IA"

    def __str__(self):
        user = self.utilisateur.username if self.utilisateur else "Anonyme"
        return f"{user} — {self.type_gen} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"

    @property
    def tokens_total(self):
        return self.tokens_input + self.tokens_output


class TemplatePrompt(models.Model):
    """Templates de prompts réutilisables pour la génération IA."""
    nom          = models.CharField(max_length=200)
    type_gen     = models.CharField(max_length=20, choices=GenerationIA.TYPES, default="autre")
    description  = models.TextField(blank=True)
    template     = models.TextField(
        help_text="Template de prompt avec variables {{titre}}, {{niveau}}, {{langue}}, etc."
    )
    variables    = models.JSONField(default=list, blank=True,
                                     help_text='["titre", "niveau", "langue"]')
    actif        = models.BooleanField(default=True)
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["type_gen", "nom"]
        verbose_name = "Template de prompt"

    def __str__(self):
        return f"{self.nom} ({self.type_gen})"
