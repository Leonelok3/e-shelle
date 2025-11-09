from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import hashlib
import json

User = get_user_model()

class Source(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    url = models.URLField()
    country = models.CharField(max_length=80, blank=True, default="")
    active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Opportunity(models.Model):
    CATEGORY_CHOICES = [
        ("study", "Études"),
        ("work", "Travail"),
        ("pr", "Résidence permanente"),
        ("scholarship", "Bourse"),
    ]
    title = models.CharField(max_length=300)
    country = models.CharField(max_length=80)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    is_scholarship = models.BooleanField(default=False)
    url = models.URLField()
    deadline = models.DateField(null=True, blank=True)
    cost_min = models.IntegerField(null=True, blank=True)
    cost_max = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    eligibility_tags = models.JSONField(default=list)  # p.ex. ["IELTS>=6", "Licence"]
    score = models.IntegerField(default=0)            # 0..100 (heuristique)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="opps")
    hash = models.CharField(max_length=64, db_index=True)  # dédup
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["country", "category"]),
            models.Index(fields=["deadline"]),
            models.Index(fields=["score"]),
        ]
        ordering = ["-score", "deadline", "title"]

    def compute_hash(self):
        payload = f"{self.title}|{self.url}|{self.country}|{self.category}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = self.compute_hash()
        super().save(*args, **kwargs)

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    country_filter = models.CharField(max_length=80, blank=True, default="")
    category_filter = models.CharField(max_length=32, blank=True, default="")
    min_score = models.IntegerField(default=50)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
