from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Administrateur"
    COLLECTEUR = "COLLECTEUR", "Collecteur"
    CLIENT = "CLIENT", "Client"


class CustomUser(AbstractUser):
    """Standalone user model used when Tchaslucpay runs as its own service."""

    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CLIENT, db_index=True)
    phone_number = models.CharField(max_length=25, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="tchaslucpay_user_set",
        related_query_name="tchaslucpay_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="tchaslucpay_user_set",
        related_query_name="tchaslucpay_user",
    )

    class Meta:
        verbose_name = "Utilisateur Tchaslucpay"
        verbose_name_plural = "Utilisateurs Tchaslucpay"

    @property
    def is_collecteur(self):
        return self.role == UserRole.COLLECTEUR

    @property
    def is_client(self):
        return self.role == UserRole.CLIENT


class CollecteurProfile(models.Model):
    user = models.OneToOneField("tchaslucpay_accounts.CustomUser", on_delete=models.CASCADE, related_name="collecteur_profile")
    employee_code = models.CharField(max_length=30, unique=True)
    zone = models.CharField(max_length=120, db_index=True)
    city = models.CharField(max_length=80, default="Douala")
    phone_number = models.CharField(max_length=25)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil collecteur"
        verbose_name_plural = "Profils collecteurs"

    def __str__(self):
        return f"{self.employee_code} - {self.user.get_full_name() or self.user.username}"


class ClientProfile(models.Model):
    user = models.OneToOneField("tchaslucpay_accounts.CustomUser", on_delete=models.CASCADE, related_name="client_profile")
    account_number = models.CharField(max_length=24, unique=True, db_index=True)
    national_id = models.CharField(max_length=80, blank=True)
    national_id_expiry = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=80, default="Douala")
    quarter = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=25, db_index=True)
    solde = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trusted_collecteur = models.ForeignKey(
        CollecteurProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil client"
        verbose_name_plural = "Profils clients"

    def __str__(self):
        return f"{self.account_number} - {self.user.get_full_name() or self.user.username}"
