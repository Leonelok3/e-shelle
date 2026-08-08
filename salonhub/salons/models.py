import re
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField("Nom", max_length=80)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField("Emoji / icône", max_length=10, default="✨")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Salon(models.Model):
    class Kind(models.TextChoices):
        COIFFURE = "coiffure", "Coiffure & Esthétique"
        BEAUTE = "beaute", "Institut de Beauté & Spa"
        ELECTRICITE = "elec", "Électricité & Énergie"
        PLOMBERIE = "plomb", "Plomberie & Sanitaire"
        MECANIQUE = "meca", "Mécanique & Auto"
        BATIMENT = "batiment", "Maçonnerie & Bâtiment"
        COUTURE = "couture", "Couture & Mode"
        MENUISERIE = "menuis", "Menuiserie & Ameublement"
        PEINTURE = "peinture", "Peinture & Décoration"
        AUTRE = "autre", "Autre Service"

        # Compatibilité
        SALON = "salon", "Coiffure & Esthétique"
        INSTITUT = "institut", "Institut de Beauté & Spa"
        SPA = "spa", "Spa & bien-être"
        BARBIER = "barbier", "Barbershop"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="salons")
    name = models.CharField("Nom de l'établissement", max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    kind = models.CharField("Secteur d'activité", max_length=10,
                             choices=Kind.choices, default=Kind.COIFFURE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="salons")
    description = models.TextField("Description", blank=True)

    city = models.CharField("Ville", max_length=100)
    district = models.CharField("Quartier", max_length=100, blank=True)
    address = models.CharField("Adresse complète", max_length=255, blank=True)

    whatsapp_number = models.CharField(
        "Numéro WhatsApp (format international, ex: 237690000000)",
        max_length=20,
    )
    phone_display = models.CharField("Téléphone affiché", max_length=20, blank=True)
    email = models.EmailField(blank=True)

    logo = models.ImageField("Logo", upload_to="salons/logos/", blank=True, null=True)
    cover_image = models.ImageField("Photo de couverture", upload_to="salons/covers/",
                                     blank=True, null=True)

    is_active = models.BooleanField("Visible sur la plateforme", default=True)
    is_verified = models.BooleanField("Établissement vérifié", default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_verified", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Salon.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        # normalise le numéro whatsapp : on ne garde que les chiffres
        self.whatsapp_number = re.sub(r"\D", "", self.whatsapp_number or "")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("salons:detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Service(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="services")
    name = models.CharField("Prestation", max_length=150)
    description = models.CharField("Description courte", max_length=255, blank=True)
    price = models.DecimalField("Prix (FCFA)", max_digits=10, decimal_places=0)
    duration_minutes = models.PositiveIntegerField("Durée (minutes)", default=30)
    is_active = models.BooleanField("Actif", default=True)
    order = models.PositiveIntegerField("Ordre d'affichage", default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} — {self.salon.name}"


class OpeningHour(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Lundi"
        TUESDAY = 1, "Mardi"
        WEDNESDAY = 2, "Mercredi"
        THURSDAY = 3, "Jeudi"
        FRIDAY = 4, "Vendredi"
        SATURDAY = 5, "Samedi"
        SUNDAY = 6, "Dimanche"

    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="opening_hours")
    weekday = models.IntegerField(choices=Weekday.choices)
    is_closed = models.BooleanField("Fermé ce jour", default=False)
    start_time = models.TimeField("Ouverture", default="08:00")
    end_time = models.TimeField("Fermeture", default="18:00")

    class Meta:
        ordering = ["weekday"]
        unique_together = ("salon", "weekday")

    def __str__(self):
        return f"{self.get_weekday_display()} : {self.start_time}-{self.end_time}" if not self.is_closed else f"{self.get_weekday_display()} : fermé"
