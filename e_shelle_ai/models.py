"""
e_shelle_ai/models.py
Modèles de l'agent IA central E-Shelle.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date
import json


# ─── Conversation ─────────────────────────────────────────────────────────────

class AIConversation(models.Model):
    """Session de chat entre un utilisateur et l'agent E-Shelle AI."""

    MODULE_CHOICES = [
        ("global",      "Global — Tous modules"),
        ("resto",       "E-Shelle Resto"),
        ("boutique",    "E-Shelle Boutique"),
        ("formations",  "Formations"),
        ("agro",        "E-Shelle Agro"),
        ("gaz",         "E-Shelle Gaz"),
        ("pharma",      "E-Shelle Pharma"),
        ("pressing",    "E-Shelle Pressing"),
        ("rencontres",  "E-Shelle Love"),
        ("njangi",      "Njangi Digital"),
        ("immobilier",  "E-Shelle Immo"),
        ("marketing",   "Marketing & Croissance"),
    ]

    user           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        verbose_name="Utilisateur",
    )
    title          = models.CharField(
        max_length=200, blank=True,
        verbose_name="Titre (auto-généré)",
        help_text="Généré automatiquement depuis le premier message",
    )
    module_context = models.CharField(
        max_length=20, choices=MODULE_CHOICES, default="global",
        verbose_name="Contexte module",
    )
    is_active      = models.BooleanField(default=True, verbose_name="Active")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Conversation IA"
        verbose_name_plural = "Conversations IA"

    def __str__(self):
        return f"{self.user.username} — {self.title or 'Sans titre'} ({self.created_at:%d/%m/%Y})"

    @property
    def message_count(self):
        return self.messages.filter(role__in=["user", "assistant"]).count()

    def get_context_messages(self, limit: int = 20) -> list:
        """Retourne les derniers messages au format OpenAI [{role, content}]."""
        msgs = self.messages.filter(
            role__in=["user", "assistant"]
        ).order_by("-created_at")[:limit]
        return [{"role": m.role, "content": m.content} for m in reversed(list(msgs))]


# ─── Message ──────────────────────────────────────────────────────────────────

class AIMessage(models.Model):
    """Message individuel dans une conversation."""

    ROLE_CHOICES = [
        ("user",      "Utilisateur"),
        ("assistant", "Assistant IA"),
        ("system",    "Système"),
    ]
    TYPE_CHOICES = [
        ("text",  "Texte"),
        ("image", "Image générée"),
        ("video", "Vidéo générée"),
        ("mixed", "Texte + Image"),
    ]

    conversation   = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE,
        related_name="messages", verbose_name="Conversation",
    )
    role           = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content        = models.TextField(verbose_name="Contenu")
    message_type   = models.CharField(max_length=10, choices=TYPE_CHOICES, default="text")
    image_url      = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="URL image (DALL-E)",
        help_text="Chemin local media/ après téléchargement",
    )
    tokens_used    = models.PositiveIntegerField(default=0, verbose_name="Tokens utilisés")
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message IA"
        verbose_name_plural = "Messages IA"

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}…"


# ─── Mémoire long terme ───────────────────────────────────────────────────────

class AIUserMemory(models.Model):
    """
    Mémoire persistante de l'utilisateur.
    Stocke ses préférences, son profil métier, ses projets détectés.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_memory",
        verbose_name="Utilisateur",
    )
    preferences = models.JSONField(
        default=dict,
        verbose_name="Préférences détectées",
        help_text='ex: {"ville":"Yaoundé","secteur":"restauration","objectif":"vente"}'
    )
    summary = models.TextField(
        blank=True,
        verbose_name="Résumé de l'historique utilisateur",
        help_text="Condensé auto-généré par GPT-4o après N messages",
    )
    # Données métier extraites des conversations
    business_context = models.JSONField(
        default=dict,
        verbose_name="Contexte business",
        help_text='ex: {"produits":["ndolé","eru"],"zone":"Bastos","cible":"25-40 ans"}'
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mémoire utilisateur IA"
        verbose_name_plural = "Mémoires utilisateurs IA"

    def __str__(self):
        return f"Mémoire de {self.user.username}"

    def get_summary_for_prompt(self) -> str:
        """Retourne un texte compact pour injection dans le system prompt."""
        parts = []
        if self.summary:
            parts.append(f"Historique : {self.summary}")
        if self.preferences:
            prefs = ", ".join(f"{k}={v}" for k, v in self.preferences.items())
            parts.append(f"Préférences : {prefs}")
        if self.business_context:
            ctx = ", ".join(f"{k}={v}" for k, v in self.business_context.items())
            parts.append(f"Business : {ctx}")
        return " | ".join(parts) if parts else ""


# ─── Quota utilisateur ────────────────────────────────────────────────────────

class AIQuota(models.Model):
    """
    Quota mensuel de l'utilisateur — lié à son plan.
    Reset automatique le 1er de chaque mois.
    """
    PLAN_CHOICES = [
        ("starter",    "Starter — Gratuit"),
        ("pro",        "Pro"),
        ("enterprise", "Enterprise"),
    ]

    user           = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_quota",
        verbose_name="Utilisateur",
    )
    plan           = models.CharField(max_length=15, choices=PLAN_CHOICES, default="starter")
    messages_used  = models.PositiveIntegerField(default=0)
    images_used    = models.PositiveIntegerField(default=0)
    messages_limit = models.PositiveIntegerField(default=30, verbose_name="Limite messages/mois")
    images_limit   = models.PositiveIntegerField(default=0,  verbose_name="Limite images/mois")
    reset_date     = models.DateField(default=date.today, verbose_name="Date de prochain reset")

    class Meta:
        verbose_name = "Quota IA"
        verbose_name_plural = "Quotas IA"

    def __str__(self):
        return f"{self.user.username} — {self.plan} ({self.messages_used}/{self.messages_limit} msg)"

    @property
    def messages_remaining(self) -> int:
        return max(0, self.messages_limit - self.messages_used)

    @property
    def images_remaining(self) -> int:
        return max(0, self.images_limit - self.images_used)

    @property
    def is_expired(self) -> bool:
        return date.today() >= self.reset_date

    def check_and_reset_if_needed(self):
        """Remet à zéro si le mois est écoulé."""
        from datetime import date as d, timedelta
        today = d.today()
        if today >= self.reset_date:
            self.messages_used = 0
            self.images_used = 0
            # Prochain reset = 1er du mois suivant
            if today.month == 12:
                self.reset_date = d(today.year + 1, 1, 1)
            else:
                self.reset_date = d(today.year, today.month + 1, 1)
            self.save(update_fields=["messages_used", "images_used", "reset_date"])


# ─── Analytics agent central ─────────────────────────────────────────────────

class CentralAgentQueryLog(models.Model):
    """Journal des recherches et intentions du chat public E-Shelle AI."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="central_agent_queries",
    )
    session_key = models.CharField(max_length=80, blank=True)
    query = models.TextField()
    module = models.CharField(max_length=40, db_index=True)
    response = models.TextField(blank=True)
    results_count = models.PositiveIntegerField(default=0)
    premium_results_count = models.PositiveIntegerField(default=0)
    had_results = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Recherche Agent Central"
        verbose_name_plural = "Recherches Agent Central"
        indexes = [
            models.Index(fields=["module", "created_at"]),
            models.Index(fields=["had_results", "created_at"]),
        ]

    def __str__(self):
        return f"{self.module} - {self.query[:70]}"


# ─── Log API ──────────────────────────────────────────────────────────────────

class AILog(models.Model):
    """
    Trace chaque appel à l'API OpenAI — pour facturation et monitoring.
    """
    TYPE_CHOICES = [
        ("chat",  "Chat GPT-4o"),
        ("image", "Image DALL-E 3"),
    ]

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="ai_logs",
    )
    type_appel    = models.CharField(max_length=10, choices=TYPE_CHOICES)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens  = models.PositiveIntegerField(default=0)
    # Coût estimé en USD (gpt-4o : $5/1M input + $15/1M output)
    cout_estime_usd = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    model_used    = models.CharField(max_length=30, default="gpt-4o")
    success       = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log API IA"
        verbose_name_plural = "Logs API IA"

    def __str__(self):
        user_str = self.user.username if self.user else "anonyme"
        return f"{self.type_appel} — {user_str} — {self.total_tokens} tokens ({self.created_at:%d/%m %H:%M})"

    @classmethod
    def compute_cost(cls, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calcule le coût estimé en USD."""
        costs = {
            "gpt-4o":       (5.00, 15.00),   # par million tokens
            "gpt-4o-mini":  (0.15, 0.60),
            "dall-e-3":     (0.04, 0.04),     # par image (fixe)
        }
        input_price, output_price = costs.get(model, (5.00, 15.00))
        return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
