from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .base import TimeStampedUUIDModel
from .catalog import Product, ProductVariant


CANADIAN_PROVINCES = [
    ("AB", "Alberta"),
    ("BC", "British Columbia"),
    ("MB", "Manitoba"),
    ("NB", "New Brunswick"),
    ("NL", "Newfoundland and Labrador"),
    ("NS", "Nova Scotia"),
    ("NT", "Northwest Territories"),
    ("NU", "Nunavut"),
    ("ON", "Ontario"),
    ("PE", "Prince Edward Island"),
    ("QC", "Quebec"),
    ("SK", "Saskatchewan"),
    ("YT", "Yukon"),
]


class Address(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tibo_addresses")
    full_name = models.CharField(max_length=160)
    company = models.CharField(max_length=160, blank=True)
    line1 = models.CharField(max_length=180)
    line2 = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=120)
    province = models.CharField(max_length=2, choices=CANADIAN_PROVINCES)
    postal_code = models.CharField(max_length=12)
    country = models.CharField(max_length=2, default="CA")
    phone = models.CharField(max_length=30, blank=True)
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default_shipping", "-created_at"]
        indexes = [models.Index(fields=["user", "province"])]
        verbose_name = "Adresse TIBO"
        verbose_name_plural = "Adresses TIBO"

    def __str__(self):
        return f"{self.full_name}, {self.city} {self.province}"


class Coupon(TimeStampedUUIDModel):
    PERCENT = "percent"
    FIXED = "fixed"
    TYPE_CHOICES = [(PERCENT, "%"), (FIXED, "Montant fixe")]

    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency = models.CharField(max_length=3, default="CAD")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active or self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def apply_to(self, amount):
        if not self.is_valid():
            return Decimal("0.00")
        if self.discount_type == self.PERCENT:
            return min(amount * (self.value / Decimal("100")), amount)
        return min(self.value, amount)

    def __str__(self):
        return self.code


class Cart(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="tibo_carts")
    session_key = models.CharField(max_length=80, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.CharField(max_length=3, default="CAD")

    class Meta:
        indexes = [models.Index(fields=["user", "session_key"])]
        verbose_name = "Panier TIBO"
        verbose_name_plural = "Paniers TIBO"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.select_related("product", "variant")), Decimal("0.00"))

    @property
    def discount_total(self):
        return self.coupon.apply_to(self.subtotal) if self.coupon else Decimal("0.00")

    @property
    def tax_total(self):
        return (self.subtotal - self.discount_total) * Decimal("0.13")

    @property
    def shipping_total(self):
        return Decimal("0.00") if self.subtotal >= Decimal("99.00") else Decimal("9.95")

    @property
    def total(self):
        return self.subtotal - self.discount_total + self.tax_total + self.shipping_total

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart {self.user or self.session_key or self.id}"


class CartItem(TimeStampedUUIDModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("cart", "product", "variant")]
        verbose_name = "Ligne panier"
        verbose_name_plural = "Lignes panier"

    @property
    def unit_price(self):
        return self.variant.effective_price if self.variant else self.product.price

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"


class Order(TimeStampedUUIDModel):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (DRAFT, "Brouillon"),
        (PENDING, "En attente"),
        (PAID, "Payée"),
        (FULFILLING, "Préparation"),
        (SHIPPED, "Expédiée"),
        (COMPLETED, "Terminée"),
        (CANCELLED, "Annulée"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tibo_orders")
    email = models.EmailField()
    number = models.CharField(max_length=24, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    currency = models.CharField(max_length=3, default="CAD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_address = models.JSONField(default=dict, blank=True)
    billing_address = models.JSONField(default=dict, blank=True)
    external_order_id = models.CharField(max_length=180, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["email"])]
        verbose_name = "Commande TIBO"
        verbose_name_plural = "Commandes TIBO"

    def save(self, *args, **kwargs):
        if not self.number:
            compact = str(self.id).split("-")[0].upper()
            self.number = f"TIBO-{compact}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number


class OrderItem(TimeStampedUUIDModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=240)
    supplier_source = models.CharField(max_length=20, blank=True)
    external_product_id = models.CharField(max_length=180, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    fulfillment_status = models.CharField(max_length=40, default="pending")
    tracking_url = models.URLField(blank=True, max_length=700)

    class Meta:
        verbose_name = "Article commande"
        verbose_name_plural = "Articles commande"

    def __str__(self):
        return self.title


class Payment(TimeStampedUUIDModel):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    PROVIDERS = [(STRIPE, "Stripe"), (PAYPAL, "PayPal")]
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    STATUSES = [(PENDING, "Pending"), (SUCCEEDED, "Succeeded"), (FAILED, "Failed"), (REFUNDED, "Refunded")]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    status = models.CharField(max_length=20, choices=STATUSES, default=PENDING, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="CAD")
    provider_reference = models.CharField(max_length=180, blank=True, db_index=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paiement TIBO"
        verbose_name_plural = "Paiements TIBO"


class Wishlist(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tibo_wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        unique_together = [("user", "product")]
        verbose_name = "Favori TIBO"
        verbose_name_plural = "Favoris TIBO"

    def __str__(self):
        return f"{self.user} - {self.product}"


class AffiliateProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tibo_affiliate")
    code = models.CharField(max_length=40, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profil affilié TIBO"
        verbose_name_plural = "Profils affiliés TIBO"

    def __str__(self):
        return self.code


class Commission(TimeStampedUUIDModel):
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name="commissions")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="commissions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="CAD")
    status = models.CharField(max_length=20, default="pending", db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Commission TIBO"
        verbose_name_plural = "Commissions TIBO"
