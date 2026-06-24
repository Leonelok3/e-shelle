import uuid
import urllib.parse
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.text import slugify


class BusinessProfile(models.Model):
    """Profil economique global lie a une fiche prestataire d'un module."""

    class Module(models.TextChoices):
        RESTO = "resto", "Resto"
        GAZ = "gaz", "Gaz"
        PRESSING = "pressing", "Pressing"
        SANTE = "sante", "Sante"
        PHARMA = "pharma", "Pharma"
        JOBS = "jobs", "Jobs"
        SERVICES = "services", "Services"
        FORMATION = "formation", "Formation"
        BOUTIQUE = "boutique", "Boutique"
        MARKET = "market", "Market"
        AGRO = "agro", "Agro"
        IMMOBILIER = "immobilier", "Immobilier"
        AUTO = "auto", "Auto"
        TRANSPORT = "transport", "Transport"
        NJANGI = "njangi", "Njangi"
        ADGEN = "adgen", "AdGen"
        EDU = "edu", "EduCam Pro"
        QUINCAILLERIE = "quincaillerie", "Quincaillerie"
        GENERAL = "general", "General"

    class Plan(models.TextChoices):
        FREE = "free", "Gratuit"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"
        PREMIUM = "premium", "Premium"

    class ActivationStatus(models.TextChoices):
        DEMO = "demo", "Demo"
        PENDING = "pending", "Paiement en attente"
        ACTIVE = "active", "Activee"

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
    public_slug = models.SlugField(
        max_length=240,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Slug public stable pour la vitrine E-Shelle, ex: /business/@ma-boutique/.",
    )
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    promo_headline = models.CharField(
        max_length=140,
        blank=True,
        help_text="Titre court affiche sur la page d'accueil.",
    )
    promo_offer = models.CharField(
        max_length=160,
        blank=True,
        help_text="Offre, phrase d'accroche ou avantage commercial.",
    )
    promo_image = models.ImageField(
        upload_to="business/promos/",
        blank=True,
        null=True,
        help_text="Visuel publicitaire affiche dans le hero et les sections premium.",
    )
    promo_url = models.URLField(
        blank=True,
        help_text="Lien de destination de la publicite. Laisser vide pour utiliser WhatsApp ou le module.",
    )
    logo = models.ImageField(
        upload_to="business/logos/",
        blank=True,
        null=True,
        help_text="Logo officiel du business.",
    )

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE, db_index=True)
    activation_status = models.CharField(
        max_length=20,
        choices=ActivationStatus.choices,
        default=ActivationStatus.DEMO,
        db_index=True,
    )
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

    def save(self, *args, **kwargs):
        if not self.public_slug:
            self.public_slug = self._build_unique_public_slug()
        super().save(*args, **kwargs)

    def _build_unique_public_slug(self):
        base = slugify(self.slug or f"{self.name}-{self.city}" or self.name)[:210] or "business"
        slug = base
        n = 1
        while BusinessProfile.objects.filter(public_slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"[:240]
            n += 1
        return slug

    def get_absolute_url(self):
        if self.public_slug:
            try:
                return reverse("business_public_short", kwargs={"public_slug": self.public_slug})
            except NoReverseMatch:
                return reverse("business:public_profile", kwargs={"public_slug": self.public_slug})
        return reverse("business:dashboard")

    @property
    def public_url(self):
        return self.get_absolute_url()

    @property
    def clean_whatsapp_number(self):
        number = (self.whatsapp or self.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if number and not number.startswith("237"):
            number = f"237{number}"
        return number

    def whatsapp_url(self, text=None):
        number = self.clean_whatsapp_number
        if not number:
            return ""
        message = text or f"Bonjour {self.name}, je viens de E-Shelle."
        import urllib.parse
        return f"https://wa.me/{number}?text={urllib.parse.quote(message)}"

    def share_text(self):
        return f"Decouvrez {self.name} sur E-Shelle: {self.get_absolute_url()}"

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
        self.activation_status = self.ActivationStatus.ACTIVE
        base = self.subscription_expires_at if self.subscription_active else timezone.now()
        self.subscription_expires_at = base + timedelta(days=days)
        if plan == self.Plan.PRO:
            self.ai_credits += 5
        elif plan == self.Plan.BUSINESS:
            self.ai_credits += 20
        elif plan == self.Plan.PREMIUM:
            self.ai_credits += 50
        self.save(update_fields=["plan", "activation_status", "subscription_expires_at", "ai_credits", "updated_at"])

    def activate_boost(self, days: int = 7):
        base = self.boost_expires_at if self.boost_active else timezone.now()
        self.boost_expires_at = base + timedelta(days=days)
        self.save(update_fields=["boost_expires_at", "updated_at"])


class BusinessCatalogItem(models.Model):
    """Produit ou service ajoute directement sur une fiche business autonome."""

    class ItemType(models.TextChoices):
        PRODUCT = "product", "Produit"
        SERVICE = "service", "Service"
        MENU = "menu", "Menu"
        DELIVERY = "delivery", "Livraison"
        OFFER = "offer", "Offre"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="catalog_items",
    )
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.PRODUCT)
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    price_label = models.CharField(max_length=80, blank=True, help_text="Ex: 2 500 FCFA, Prix a discuter.")
    image = models.ImageField(upload_to="business/catalogue/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [
            models.Index(fields=["business", "is_active", "order"]),
        ]
        verbose_name = "Produit/service business"
        verbose_name_plural = "Produits/services business"

    def __str__(self):
        return f"{self.title} - {self.business.name}"

    @property
    def image_url(self):
        if not self.image:
            return ""
        try:
            return self.image.url
        except Exception:
            return ""

    def to_public_item(self):
        return {
            "id": self.id,
            "type": self.get_item_type_display(),
            "title": self.title,
            "description": self.description,
            "price": self.price_label or "Prix a discuter",
            "image": self.image_url,
            "images": ([self.image.url] if self.image else []) + [img.image.url for img in self.images.all() if img.image],
            "url": "",
            "contact_url": self.business.whatsapp_url(
                f"Bonjour {self.business.name}, je suis interesse par {self.title} vu sur E-Shelle."
            ),
            "meta": self.business.district or self.business.city,
        }


class BusinessCatalogItemImage(models.Model):
    """Photos supplementaires pour un produit/service du catalogue."""

    item = models.ForeignKey(
        BusinessCatalogItem,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="business/catalogue/extra/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Photo produit supplementaire"
        verbose_name_plural = "Photos produit supplementaires"

    def __str__(self):
        return f"Photo pour {self.item.title}"


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


class HomeAdSlide(models.Model):
    """Slide publicitaire visible sur la page d'accueil."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image / flyer"
        VIDEO = "video", "Video"

    business = models.ForeignKey(
        BusinessProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="home_ad_slides",
        help_text="Business premium/business associe au slide.",
    )
    title = models.CharField(max_length=140)
    subtitle = models.CharField(max_length=190, blank=True)
    image = models.ImageField(upload_to="business/home-slides/")
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    video = models.FileField(upload_to="business/home-slides/videos/", blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="Lien direct MP4 optionnel si la video n'est pas uploadee.")
    badge = models.CharField(max_length=60, blank=True, default="Premium")
    cta_label = models.CharField(max_length=40, blank=True, default="Commander")
    cta_url = models.URLField(
        blank=True,
        help_text="Lien de commande. Si vide, E-Shelle utilise WhatsApp ou la recherche IA du business.",
    )
    city = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    impressions_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Slide publicitaire accueil"
        verbose_name_plural = "Slides publicitaires accueil"

    def __str__(self):
        return self.title

    @property
    def is_live(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        if self.business and self.business.plan not in [BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]:
            return False
        return True

    def destination_url(self):
        if self.cta_url:
            return self.cta_url
        if self.business:
            number = (self.business.whatsapp or self.business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
            if number:
                if not number.startswith("237"):
                    number = f"237{number}"
                text = urllib.parse.quote(f"Bonjour {self.business.name}, je viens de E-Shelle.")
                return f"https://wa.me/{number}?text={text}"
            query = urllib.parse.quote(f"Je veux commander chez {self.business.name}")
            return f"/chat/?q={query}"
        return "/chat/"


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


class PremiumSectorCampaign(models.Model):
    """Campagne commerciale pour pousser un secteur premium sur E-Shelle."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "En pause"
        DONE = "done", "Terminee"

    name = models.CharField(max_length=160)
    module = models.CharField(max_length=30, choices=BusinessProfile.Module.choices, db_index=True)
    city = models.CharField(max_length=100, blank=True)
    goal = models.CharField(max_length=180, blank=True, help_text="Ex: recruter 20 restos Premium a Douala")
    pitch = models.TextField(blank=True, help_text="Script commercial ou message WhatsApp de campagne.")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    target_businesses = models.PositiveIntegerField(default=0)
    budget_xaf = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at", "name"]
        verbose_name = "Campagne secteur premium"
        verbose_name_plural = "Campagnes secteurs premium"

    def __str__(self):
        return self.name

    @property
    def is_live(self):
        now = timezone.now()
        if self.status != self.Status.ACTIVE:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True


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
        if self.business.activation_status != BusinessProfile.ActivationStatus.ACTIVE:
            self.business.activation_status = BusinessProfile.ActivationStatus.ACTIVE
            self.business.save(update_fields=["activation_status", "updated_at"])
        return tx


class BusinessKeyAccount(models.Model):
    """Statut commercial d'un partenaire E-Shelle Business Key."""

    class Tier(models.TextChoices):
        FREE = "free", "Gratuit"
        KEY = "key", "Business Key"
        PRO = "pro", "Ambassadeur Pro"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_key_account")
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compte Business Key"
        verbose_name_plural = "Comptes Business Key"

    def __str__(self):
        return f"{self.user} - {self.get_tier_display()}"

    @property
    def is_paid(self):
        return self.tier in {self.Tier.KEY, self.Tier.PRO}

    @property
    def is_active_paid(self):
        return self.is_paid and (not self.expires_at or self.expires_at > timezone.now())

    def activate(self, tier, days=30):
        self.tier = tier
        self.activated_at = timezone.now()
        base = self.expires_at if self.expires_at and self.expires_at > timezone.now() else timezone.now()
        self.expires_at = base + timedelta(days=days)
        self.save(update_fields=["tier", "activated_at", "expires_at", "updated_at"])


class BusinessKeyPaymentRequest(models.Model):
    """Demande de paiement manuel pour activer une Business Key."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirme"
        CANCELED = "canceled", "Annule"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_key_payment_requests")
    tier = models.CharField(max_length=20, choices=BusinessKeyAccount.Tier.choices, db_index=True)
    amount_xaf = models.PositiveIntegerField(default=0)
    momo_number = models.CharField(max_length=40, blank=True)
    proof = models.FileField(upload_to="business_key/proofs/", blank=True, null=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paiement Business Key"
        verbose_name_plural = "Paiements Business Key"

    def __str__(self):
        return f"{self.user} - {self.get_tier_display()} - {self.amount_xaf} FCFA"

    def confirm(self):
        from billing.affiliates import create_commission_for_transaction
        from billing.models import Transaction

        if self.status == self.Status.CONFIRMED:
            return None
        account, _ = BusinessKeyAccount.objects.get_or_create(user=self.user)
        account.activate(self.tier, days=30)
        tx = Transaction.objects.create(
            user=self.user,
            amount=self.amount_xaf,
            currency="XAF",
            type="CREDIT",
            status="COMPLETED",
            payment_method="OTHER",
            description="Activation E-Shelle Business Key",
            metadata={
                "business_key_tier": self.tier,
                "commission_base": str(self.amount_xaf),
                "product_type": "business_key_subscription",
                "payment_request_id": self.id,
            },
        )
        create_commission_for_transaction(tx)
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at"])
        return account


class AppCommission(models.Model):
    """Catalogue des apps E-Shelle vendables par les partenaires."""

    class AppName(models.TextChoices):
        MARKETPLACE = "marketplace", "Marketplace"
        LOVE = "love", "E-Shelle Love"
        FORMATIONS = "formations", "Formations"
        NJANGI = "njangi", "Njangi Tontine"
        AGRO = "agro", "Agro B2B/B2C"
        PHARMA = "pharma", "Pharma"
        TRANSPORT = "transport", "Transport"
        TCHASLUCPAY = "tchaslucpay", "Tchaslucpay"
        PRESSING = "pressing", "Pressing"
        RESTO = "resto", "Resto"
        IMMOBILIER = "immobilier", "Immobilier"
        AUTO = "auto", "Auto"
        GAZ = "gaz", "Gaz & Livraison"
        JOBS = "jobs", "Jobs"
        ADGEN = "adgen", "AdGen"
        EDU = "edu", "EduCam Pro"
        SANTE = "sante", "Sante"
        SIMPLO = "simplo", "Simplo"
        MARKET = "market", "Market general"
        SERVICES_WEB = "services_web", "Services Web"

    app_name = models.CharField(max_length=50, choices=AppName.choices, unique=True)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="% commission sur vente",
    )
    commission_fixe = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text="Commission fixe en FCFA",
    )
    is_recurring = models.BooleanField(default=False, help_text="Commission mensuelle recurrente")
    is_active = models.BooleanField(default=True)
    script_vente = models.TextField(blank=True, help_text="Script WhatsApp pour vendre cette app")
    priority = models.IntegerField(default=0, help_text="Ordre d'affichage (0=premier)")
    icon = models.CharField(max_length=50, blank=True, help_text="Icone ou emoji simple")

    class Meta:
        ordering = ["priority", "app_name"]
        verbose_name = "Commission par App"
        verbose_name_plural = "Commissions par App"

    def __str__(self):
        return f"{self.label} - {self.commission_rate}%"


class PartnerLevel(models.Model):
    """Niveau commercial Business Key et apps debloquees."""

    class Level(models.TextChoices):
        GRATUIT = "gratuit", "Gratuit"
        BUSINESS_KEY = "business_key", "Business Key"
        AMBASSADEUR = "ambassadeur", "Ambassadeur Pro"
        MULTI_APP = "multi_app", "Multi-App Master"

    level = models.CharField(max_length=30, choices=Level.choices, unique=True)
    label = models.CharField(max_length=100)
    prix_fcfa = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    apps_accessibles = models.ManyToManyField(
        AppCommission,
        blank=True,
        help_text="Apps dont le partenaire peut vendre et toucher commission",
    )
    bonus_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Niveau Partenaire"
        verbose_name_plural = "Niveaux Partenaires"

    def __str__(self):
        return f"{self.label} - {self.prix_fcfa} FCFA"


class PartnerCRMLead(models.Model):
    """Prospect suivi par un partenaire Business Key."""

    class Status(models.TextChoices):
        NEW = "new", "Nouveau"
        CONTACTED = "contacted", "Contacte"
        INTERESTED = "interested", "Interesse"
        FOLLOW_UP = "follow_up", "A relancer"
        CONVERTED = "converted", "Converti"
        REFUSED = "refused", "Refuse"

    class Sector(models.TextChoices):
        RESTAURANT = "restaurant", "Restaurant"
        PRESSING = "pressing", "Pressing"
        GAZ = "gaz", "Gaz"
        IMMOBILIER = "immobilier", "Immobilier"
        AUTO = "auto", "Auto"
        AGRO = "agro", "Agro"
        MARKET = "market", "Market"
        SANTE = "sante", "Sante"
        SERVICES = "services", "Services"
        OTHER = "other", "Autre"

    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_key_crm_leads")
    business_name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=120, blank=True)
    sector = models.CharField(max_length=30, choices=Sector.choices, default=Sector.OTHER, db_index=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW, db_index=True)
    potential_xaf = models.PositiveIntegerField(default=15000)
    next_follow_up_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "next_follow_up_at", "-updated_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["partner", "sector"]),
        ]
        verbose_name = "Prospect CRM partenaire"
        verbose_name_plural = "Prospects CRM partenaires"

    def __str__(self):
        return f"{self.business_name} - {self.get_status_display()}"

    @property
    def preferred_phone(self):
        return self.whatsapp or self.phone

    def whatsapp_url(self, text=""):
        number = (self.preferred_phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if not number:
            return ""
        if not number.startswith("237"):
            number = f"237{number}"
        return f"https://wa.me/{number}?text={urllib.parse.quote(text)}"


class ClientAIKit(models.Model):
    """Kit de livraison IA reutilisable pour personnaliser E-Shelle a un client."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        READY = "ready", "Pret a vendre"
        DELIVERED = "delivered", "Livre"
        ARCHIVED = "archived", "Archive"

    business = models.OneToOneField(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="ai_delivery_kit",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    client_brief = models.JSONField(default=dict, blank=True)
    recommended_agents = models.JSONField(default=list, blank=True)
    chatbot_prompt = models.TextField(blank=True)
    website_plan = models.JSONField(default=dict, blank=True)
    content_pack = models.JSONField(default=dict, blank=True)
    whatsapp_scripts = models.JSONField(default=list, blank=True)
    seo_plan = models.JSONField(default=dict, blank=True)
    video_plan = models.JSONField(default=dict, blank=True)
    automation_plan = models.JSONField(default=list, blank=True)
    qa_checklist = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_client_ai_kits",
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Kit client IA"
        verbose_name_plural = "Kits clients IA"

    def __str__(self):
        return f"Kit IA - {self.business.name}"


class UnmetSearchRequest(models.Model):
    """Demande client creee quand E-Shelle ne trouve pas de resultat satisfaisant."""

    class Status(models.TextChoices):
        NEW = "new", "Nouvelle"
        VIEWED = "viewed", "Vue"
        NOTIFIED = "notified", "Prestataires notifies"
        IN_PROGRESS = "in_progress", "En traitement"
        CONTACTED = "contacted", "Client contacte"
        PROVIDER_FOUND = "provider_found", "Prestataire trouve"
        SOLD = "sold", "Vendu"
        LOST = "lost", "Perdu"
        SATISFIED = "satisfied", "Satisfaite"
        EXPIRED = "expired", "Expiree"
        CANCELED = "canceled", "Annulee"

    query = models.CharField(max_length=260)
    module = models.CharField(max_length=30, choices=BusinessProfile.Module.choices, default=BusinessProfile.Module.GENERAL, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True)
    customer_name = models.CharField(max_length=120, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    consent_share_contact = models.BooleanField(default=False)
    consent_promotions = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    source = models.CharField(max_length=40, default="search")
    notified_count = models.PositiveIntegerField(default=0)
    assigned_partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_unmet_search_requests",
    )
    ai_category = models.CharField(max_length=80, blank=True)
    ai_priority = models.CharField(max_length=20, default="normal", db_index=True)
    lead_score = models.PositiveIntegerField(default=50, db_index=True)
    estimated_value_xaf = models.PositiveIntegerField(default=0)
    conversion_note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unmet_search_requests",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["module", "city", "status"]),
            models.Index(fields=["created_at", "status"]),
        ]
        verbose_name = "Demande non satisfaite"
        verbose_name_plural = "Demandes non satisfaites"

    def __str__(self):
        return f"{self.query} - {self.get_module_display()} - {self.city or 'zone non precisee'}"

    @property
    def preferred_contact(self):
        return self.whatsapp or self.email

    @property
    def clean_whatsapp_number(self):
        number = (self.whatsapp or "").replace("+", "").replace(" ", "").replace("-", "")
        if number and not number.startswith("237"):
            number = f"237{number}"
        return number


class UnmetSearchResponse(models.Model):
    """Action d'un prestataire sur une demande client non satisfaite."""

    class Status(models.TextChoices):
        CONTACTED = "contacted", "Client contacte"
        NOT_AVAILABLE = "not_available", "Non disponible"
        SATISFIED = "satisfied", "Client satisfait"

    request = models.ForeignKey(UnmetSearchRequest, on_delete=models.CASCADE, related_name="responses")
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="unmet_search_responses")
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unmet_search_responses",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONTACTED)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["request", "business"], name="uniq_unmet_response_per_business"),
        ]
        verbose_name = "Reponse a une demande non satisfaite"
        verbose_name_plural = "Reponses aux demandes non satisfaites"

    def __str__(self):
        return f"{self.business.name} -> {self.request.query}"


class PresentationSlide(models.Model):
    """Slide pour le Slider Revolution de la page de présentation."""
    
    class MockupType(models.TextChoices):
        DESKTOP = "desktop", "Navigateur Desktop"
        LAPTOP = "laptop", "MacBook Laptop"
        MOBILE = "mobile", "Smartphone Mobile"
        GLASS = "glass", "Carte Glassmorphism"

    title = models.CharField(max_length=150, verbose_name="Nom du site / Titre")
    subtitle = models.CharField(max_length=250, blank=True, verbose_name="Sous-titre / Tagline")
    badge = models.CharField(max_length=50, blank=True, verbose_name="Badge / Catégorie")
    image = models.ImageField(upload_to="business/presentation-slides/", verbose_name="Capture / Maquette", blank=True, null=True)
    mockup_type = models.CharField(
        max_length=20, 
        choices=MockupType.choices, 
        default=MockupType.DESKTOP, 
        verbose_name="Type de Maquette"
    )
    cta_label = models.CharField(max_length=50, default="Visiter le site", verbose_name="Texte du bouton")
    cta_url = models.CharField(max_length=250, blank=True, verbose_name="URL du bouton")
    tech_stack = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Technologies (séparées par des virgules)", 
        help_text="Ex: Django, Postgres, TailwindCSS"
    )
    features = models.TextField(
        blank=True, 
        verbose_name="Fonctionnalités clés (une par ligne)", 
        help_text="Ex: Paiement Mobile Money\nAlertes temps réel"
    )
    bg_gradient = models.CharField(
        max_length=250, 
        blank=True, 
        default="linear-gradient(135deg, #0f172a, #1e293b)", 
        verbose_name="Gradient de fond CSS", 
        help_text="Style linear-gradient CSS complet."
    )
    text_color = models.CharField(max_length=30, default="#ffffff", verbose_name="Couleur du texte (Hex)")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Slide de Présentation (Maquette)"
        verbose_name_plural = "Slides de Présentation (Maquettes)"

    def __str__(self):
        return self.title

    @property
    def tech_tags(self):
        """Retourne la liste des technologies."""
        if not self.tech_stack:
            return []
        return [tag.strip() for tag in self.tech_stack.split(",") if tag.strip()]

    @property
    def features_list(self):
        """Retourne la liste des fonctionnalités (séparées par des sauts de ligne)."""
        if not self.features:
            return []
        return [f.strip() for f in self.features.split("\n") if f.strip()]

