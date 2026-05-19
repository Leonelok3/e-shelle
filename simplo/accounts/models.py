from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class CustomUser(AbstractUser):
    """Utilisateur Simplo avec séparation simple entre client et prestataire."""

    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        PRESTATAIRE = "PRESTATAIRE", "Prestataire"
        ADMIN = "ADMIN", "Administrateur"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone_number = models.CharField(max_length=30, blank=True)

    # Noms uniques pour éviter les collisions si Simplo est monté dans un écosystème plus large.
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="simplo_users",
        related_query_name="simplo_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="simplo_users",
        related_query_name="simplo_user",
    )

    def __str__(self):
        return self.get_full_name() or self.username


class ClientProfile(models.Model):
    """Profil léger du client : l'information clé est le quartier de départ."""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="client_profile",
        limit_choices_to={"role": CustomUser.Role.CLIENT},
    )
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=30)
    ville = models.CharField(max_length=80)
    quartier = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil client"
        verbose_name_plural = "Profils clients"

    def __str__(self):
        return f"{self.nom} - {self.quartier}"


class PrestataireProfile(models.Model):
    """Prestataire terrain activable par module, sans suivi GPS lourd en V1."""

    class ServiceType(models.TextChoices):
        MOTO = "MOTO", "Moto"
        LIVRAISON = "LIVRAISON", "Livraison"
        COURSES = "COURSES", "Courses"
        ENFANTS = "ENFANTS", "Récupération enfants"

    class Status(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        OCCUPE = "OCCUPE", "Occupé"

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="prestataire_profile",
        limit_choices_to={"role": CustomUser.Role.PRESTATAIRE},
    )
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=30)
    photo = models.ImageField(upload_to="simplo/prestataires/", blank=True, null=True)
    ville = models.CharField(max_length=80)
    quartier_base = models.CharField(max_length=120)
    type_service = models.CharField(max_length=20, choices=ServiceType.choices)
    type_vehicule = models.CharField(max_length=80, blank=True)
    zone_couverte = models.CharField(
        max_length=220,
        blank=True,
        help_text="Quartiers couverts, séparés par des virgules.",
    )
    horaires = models.CharField(max_length=120, blank=True, default="06h00 - 22h00")
    statut = models.CharField(max_length=20, choices=Status.choices, default=Status.DISPONIBLE)
    note = models.DecimalField(max_digits=3, decimal_places=2, default=4.80)
    nombre_avis = models.PositiveIntegerField(default=0)
    nombre_courses = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil prestataire"
        verbose_name_plural = "Profils prestataires"
        indexes = [
            models.Index(fields=["ville", "quartier_base", "type_service", "statut"]),
        ]

    def __str__(self):
        return f"{self.nom} - {self.get_type_service_display()} - {self.quartier_base}"

    @property
    def telephone_whatsapp(self):
        """WhatsApp attend un numéro international sans signe plus."""
        return self.telephone.replace("+", "").replace(" ", "").replace("-", "")

    def get_status_toggle_url(self):
        return reverse("simplo_accounts:toggle_status")
