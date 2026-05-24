from django.conf import settings
from django.db import models


class ConversationSession(models.Model):
    """Une session de conversation par utilisateur ou visiteur anonyme."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_sessions",
    )
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Session de conversation"
        verbose_name_plural = "Sessions de conversation"

    def __str__(self):
        owner = self.user or self.session_key or "Visiteur"
        return f"Conversation {owner}"


class Message(models.Model):
    """Un message dans une conversation."""

    ROLE_CHOICES = [
        ("user", "Utilisateur"),
        ("assistant", "E-Shelle AI"),
    ]
    MODULE_CHOICES = [
        ("general", "General"),
        ("resto", "Restaurant"),
        ("gaz", "Gaz"),
        ("pressing", "Pressing"),
        ("formation", "Formation"),
        ("boutique", "Boutique"),
        ("adgen", "AdGen"),
        ("transport", "Transport"),
        ("services", "Services"),
        ("sante", "Sante"),
        ("immobilier", "Immobilier"),
        ("jobs", "Jobs"),
        ("njangi", "Njangi"),
        ("fintech", "Fintech"),
        ("agro", "Agro"),
        ("rencontres", "Rencontres"),
        ("quincaillerie", "Quincaillerie"),
        ("business_onboarding", "Inscription prestataire"),
    ]

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    module_detected = models.CharField(
        max_length=30,
        choices=MODULE_CHOICES,
        default="general",
    )
    redirect_url = models.CharField(max_length=300, blank=True)
    results = models.JSONField(default=list, blank=True)
    has_image = models.BooleanField(default=False)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.role} - {self.content[:60]}"

# Create your models here.
