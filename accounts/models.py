from django.db import models
from django.contrib.auth.models import User

class UserRole(models.TextChoices):
    CANDIDATE = "candidate", "Candidat"
    RECRUITER = "recruiter", "Recruteur"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CANDIDATE)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
