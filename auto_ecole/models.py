from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils.text import slugify


class DrivingSchool(models.Model):
    """Promoteur Auto-école"""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driving_schools",
        verbose_name="Propriétaire",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    logo = models.ImageField(upload_to="auto_ecole/logos/", null=True, blank=True)
    # Optional geolocation for map display
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    price_note = models.CharField(max_length=160, blank=True)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Auto-école"
        verbose_name_plural = "Auto-écoles"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "auto-ecole"
            candidate = base_slug
            counter = 1
            while DrivingSchool.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                counter += 1
                candidate = f"{base_slug}-{counter}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("auto_ecole:school_detail", args=[self.slug])

    @property
    def contact_number(self):
        return self.whatsapp or self.phone

    @property
    def whatsapp_url(self):
        number = self.contact_number.replace("+", "").replace(" ", "")
        if not number:
            return ""
        return f"https://wa.me/{number}?text=Bonjour%2C%20je%20viens%20de%20E-Shelle%20Auto-%C3%A9cole%20et%20je%20souhaite%20des%20informations."


class Course(models.Model):
    """Cours théoriques d'auto-école"""

    school = models.ForeignKey(DrivingSchool, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        unique_together = ("school", "slug")

    def __str__(self):
        return f"{self.school.name} - {self.title}"

    def get_absolute_url(self):
        return reverse("auto_ecole:course_detail", args=[self.school.slug, self.slug])
