import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone


class BusinessProfile(models.Model):
    """Profil economique global lie a une fiche prestataire d'un module."""

    class Module(models.TextChoices):
        RESTO = "resto", "Resto"
        GAZ = "gaz", "Gaz"
        PRESSING = "pressing", "Pressing"
        SANTE = "sante", "Sante"
        JOBS = "jobs", "Jobs"
        FORMATION = "formation", "Formation"
        BOUTIQUE = "boutique", "Boutique"
        AGRO = "agro", "Agro"
        IMMOBILIER = "immobilier", "Immobilier"
        QUINCAILLERIE = "quincaillerie", "Quincaillerie"
        GENERAL = "general", "General"

    class Plan(models.TextChoices):
        FREE = "free", "Gratuit"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"
        PREMIUM = "premium", "Premium"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_profiles",
    )
    module = models.CharField(max_length=30, choices=Module.choices, db_index=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE, db_index=True)
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    boost_expires_at = models.DateTimeField(null=True, blank=True)
    ai_credits = models.PositiveIntegerField(default=0)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    views_count = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    phone_clicks = models.PositiveIntegerField(default=0)
    detail_clicks = models.PositiveIntegerField(default=0)
    leads_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-boost_expires_at", "-subscription_expires_at", "-leads_count", "name"]
        indexes = [
            models.Index(fields=["module", "plan", "is_active"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        verbose_name = "Profil business"
        verbose_name_plural = "Profils business"

    def __str__(self):
        return f"{self.name} ({self.get_module_display()})"

    @property
    def subscription_active(self):
        return bool(self.subscription_expires_at and self.subscription_expires_at > timezone.now())

    @property
    def boost_active(self):
        return bool(self.boost_expires_at and self.boost_expires_at > timezone.now())

    @property
    def economic_score(self):
        score = self.leads_count * 5 + self.whatsapp_clicks * 3 + self.phone_clicks * 2 + self.views_count
        if self.subscription_active:
            score += 100
        if self.boost_active:
            score += 250
        if self.plan == self.Plan.PREMIUM:
            score += 300
        elif self.plan == self.Plan.BUSINESS:
            score += 180
        elif self.plan == self.Plan.PRO:
            score += 80
        return score

    def activate_plan(self, plan: str, days: int = 30):
        self.plan = plan
        base = self.subscription_expires_at if self.subscription_active else timezone.now()
        self.subscription_expires_at = base + timedelta(days=days)
        if plan == self.Plan.PRO:
            self.ai_credits += 5
        elif plan == self.Plan.BUSINESS:
            self.ai_credits += 20
        elif plan == self.Plan.PREMIUM:
            self.ai_credits += 50
        self.save(update_fields=["plan", "subscription_expires_at", "ai_credits", "updated_at"])

    def activate_boost(self, days: int = 7):
        base = self.boost_expires_at if self.boost_active else timezone.now()
        self.boost_expires_at = base + timedelta(days=days)
        self.save(update_fields=["boost_expires_at", "updated_at"])


class ProviderPlan(models.Model):
    """Offres commerciales vendues aux prestataires."""

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    plan_level = models.CharField(max_length=20, choices=BusinessProfile.Plan.choices)
    monthly_price_xaf = models.PositiveIntegerField(default=0)
    duration_days = models.PositiveIntegerField(default=30)
    included_boost_days = models.PositiveIntegerField(default=0)
    included_ai_credits = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "monthly_price_xaf"]
        verbose_name = "Plan prestataire"
        verbose_name_plural = "Plans prestataires"

    def __str__(self):
        return f"{self.name} - {self.monthly_price_xaf:,} FCFA".replace(",", " ")


class BoostCampaign(models.Model):
    """Historique des boosts achetes par un prestataire."""

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="boosts")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    amount_xaf = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=40, default="manual")
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ends_at"]
        verbose_name = "Boost prestataire"
        verbose_name_plural = "Boosts prestataires"

    def __str__(self):
        return f"Boost {self.business} jusqu'au {self.ends_at:%d/%m/%Y}"


class AICreditLedger(models.Model):
    """Mouvements de credits IA pour les services payants."""

    class Movement(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="ai_credit_movements")
    movement = models.CharField(max_length=10, choices=Movement.choices)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mouvement credit IA"
        verbose_name_plural = "Mouvements credits IA"

    def __str__(self):
        return f"{self.business} {self.movement} {self.quantity}"


class BusinessLeadEvent(models.Model):
    """Evenement commercial: vue, clic WhatsApp, appel, detail, commande."""

    class EventType(models.TextChoices):
        VIEW = "view", "Vue"
        WHATSAPP = "whatsapp", "WhatsApp"
        PHONE = "phone", "Appel"
        DETAIL = "detail", "Details"
        ORDER = "order", "Commande"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="lead_events")
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    source = models.CharField(max_length=40, default="chat")
    target_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande/clic business"
        verbose_name_plural = "Demandes/clics business"

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.business.name}"

    def tracking_url(self):
        return reverse("business:track", kwargs={"public_id": self.public_id})


class PaymentRequest(models.Model):
    """Demande de paiement adaptée terrain: cash, reception, Mobile Money manuel."""

    class Method(models.TextChoices):
        CASH_ON_DELIVERY = "cash_on_delivery", "Paiement a la reception"
        MOMO_MANUAL = "momo_manual", "Mobile Money manuel"
        ACCESS_CODE = "access_code", "Code d'acces"
        ONLINE = "online", "Paiement en ligne"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirme"
        CANCELED = "canceled", "Annule"

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="payment_requests")
    plan = models.ForeignKey(ProviderPlan, on_delete=models.PROTECT, related_name="payment_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_payment_requests")
    method = models.CharField(max_length=30, choices=Method.choices, default=Method.CASH_ON_DELIVERY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount_xaf = models.PositiveIntegerField(default=0)
    phone = models.CharField(max_length=40, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de paiement prestataire"
        verbose_name_plural = "Demandes de paiement prestataire"

    def __str__(self):
        return f"{self.business.name} - {self.plan.name} - {self.get_status_display()}"

    def confirm(self):
        from .services import record_provider_plan_payment

        if self.status == self.Status.CONFIRMED:
            return None
        tx = record_provider_plan_payment(
            business=self.business,
            plan=self.plan,
            paid_by=self.requested_by,
            amount_xaf=self.amount_xaf,
            payment_method="OTHER",
        )
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at"])
        return tx

# Create your models here.
