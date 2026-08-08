from django.db import models
from django.urls import reverse


class DrivingSchool(models.Model):
    """Promoteur Auto-école"""

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    # Optional geolocation for map display
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Auto-école"
        verbose_name_plural = "Auto-écoles"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("auto_ecole:school_detail", args=[self.slug])


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
