from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Client"
        OWNER = "owner", "Prestataire (salon / institut)"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField("Téléphone", max_length=20, blank=True)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    def __str__(self):
        return self.get_full_name() or self.username
