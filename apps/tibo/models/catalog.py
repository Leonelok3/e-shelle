from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .base import ActiveManager, TimeStampedUUIDModel


class Supplier(TimeStampedUUIDModel):
    SOURCE_SHOPIFY = "shopify"
    SOURCE_AMAZON = "amazon"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_SHOPIFY, "Shopify"),
        (SOURCE_AMAZON, "Amazon"),
        (SOURCE_MANUAL, "Manuel"),
    ]

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True)
    website = models.URLField(blank=True)
    api_shop_domain = models.CharField(max_length=255, blank=True)
    affiliate_tag = models.CharField(max_length=120, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.00"))
    is_active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["source", "is_active"])]
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedUUIDModel):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    logo = models.ImageField(upload_to="tibo/brands/", blank=True, null=True)
    website = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]
        verbose_name = "Marque"
        verbose_name_plural = "Marques"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(TimeStampedUUIDModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="tibo/categories/", blank=True, null=True)
    accent_color = models.CharField(max_length=20, default="#2f7cff")
    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["parent", "is_active"])]
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tibo:category", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class ProductTag(TimeStampedUUIDModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tag produit"
        verbose_name_plural = "Tags produits"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedUUIDModel):
    SOURCE_SHOPIFY = "shopify"
    SOURCE_AMAZON = "amazon"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_SHOPIFY, "Shopify"),
        (SOURCE_AMAZON, "Amazon"),
        (SOURCE_MANUAL, "Manuel"),
    ]
    CURRENCY_CHOICES = [("CAD", "CAD"), ("USD", "USD")]

    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True)
    external_id = models.CharField(max_length=180, blank=True, db_index=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    tags = models.ManyToManyField(ProductTag, blank=True, related_name="products")
    short_description = models.CharField(max_length=320, blank=True)
    description = models.TextField()
    specifications = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CAD")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    affiliate_url = models.URLField(blank=True, max_length=600)
    canonical_url = models.URLField(blank=True, max_length=600)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    rating_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_trending = models.BooleanField(default=False, db_index=True)
    is_digital = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)
    og_image = models.ImageField(upload_to="tibo/og/", blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["source", "external_id"]),
            models.Index(fields=["is_active", "is_featured", "is_trending"]),
            models.Index(fields=["category", "price"]),
        ]
        verbose_name = "Produit TIBO"
        verbose_name_plural = "Produits TIBO"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:250]
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def margin_amount(self):
        if self.cost_price is None:
            return Decimal("0.00")
        return max(self.price - self.cost_price, Decimal("0.00"))

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int((Decimal("1.0") - (self.price / self.compare_at_price)) * 100)
        return 0

    def get_absolute_url(self):
        return reverse("tibo:product_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class ProductVariant(TimeStampedUUIDModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    title = models.CharField(max_length=180)
    sku = models.CharField(max_length=120, blank=True, db_index=True)
    external_id = models.CharField(max_length=180, blank=True, db_index=True)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["product", "title"]
        unique_together = [("product", "sku")]
        verbose_name = "Variante"
        verbose_name_plural = "Variantes"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price

    def __str__(self):
        return f"{self.product.title} - {self.title}"


class ProductImage(TimeStampedUUIDModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name="images")
    image = models.ImageField(upload_to="tibo/products/", blank=True, null=True)
    remote_url = models.URLField(blank=True, max_length=700)
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-is_primary"]
        verbose_name = "Image produit"
        verbose_name_plural = "Images produits"

    @property
    def url(self):
        if self.image:
            return self.image.url
        return self.remote_url or "/static/tibo/images/product-placeholder.svg"

    def __str__(self):
        return self.alt_text or self.product.title


class Inventory(TimeStampedUUIDModel):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name="inventory")
    quantity = models.IntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    sync_enabled = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"

    @property
    def available(self):
        return max(self.quantity - self.reserved, 0)

    @property
    def is_low_stock(self):
        return self.available <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product.title}: {self.available}"


class ProductReview(TimeStampedUUIDModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=180, blank=True)
    comment = models.TextField()
    is_verified = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "is_published"])]
        verbose_name = "Avis produit"
        verbose_name_plural = "Avis produits"

    def __str__(self):
        return f"{self.product.title} - {self.rating}/5"
