from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import random


# ─── Clés applicatives E-Shelle ──────────────────────────────────────────────

class AppKey(models.TextChoices):
    ADGEN      = "adgen",      "AdGen — Publicités IA"
    RESTO      = "resto",      "E-Shelle Resto"
    RENCONTRES = "rencontres", "E-Shelle Love"
    NJANGI     = "njangi",     "Njangi Digital"
    EDU        = "edu",        "EduCam Pro"
    FORMATIONS = "formations", "Formations"
    BOUTIQUE   = "boutique",   "Boutique"
    AGRO       = "agro",       "E-Shelle Agro"
    GAZ        = "gaz",        "E-Shelle Gaz"

APP_ICONS = {
    "adgen":      "✨",
    "resto":      "🍽️",
    "rencontres": "❤️",
    "njangi":     "🤝",
    "edu":        "🎓",
    "formations": "📚",
    "boutique":   "🛒",
    "agro":       "🌿",
    "gaz":        "🔥",
}

APP_COLORS = {
    "adgen":      "#6C3FE8",
    "resto":      "#F97316",
    "rencontres": "#E8436A",
    "njangi":     "#1B6CA8",
    "edu":        "#0EA5E9",
    "formations": "#8B5CF6",
    "boutique":   "#10B981",
    "agro":       "#84CC16",
    "gaz":        "#FF6B00",
}


class Role(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", _("Super Admin")
    TEACHER    = "TEACHER",    _("Enseignant / Formateur")
    PARENT     = "PARENT",     _("Parent")
    STUDENT    = "STUDENT",    _("Élève / Apprenant")
    CLIENT     = "CLIENT",     _("Client / Entrepreneur")
    VENDOR     = "VENDOR",     _("Vendeur / Partenaire")


class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        help_text="Format international: +237612345678",
    )
    ville = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_admin(self):
        return self.role == Role.SUPERADMIN or self.is_superuser

    @property
    def is_teacher(self):
        return self.role == Role.TEACHER

    @property
    def is_client(self):
        return self.role == Role.CLIENT


def avatar_upload_path(instance, filename):
    return f"avatars/{instance.user.id}/{filename}"


class UserProfile(models.Model):
    """Profil étendu pour tous les utilisateurs SaaS."""
    user       = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    avatar     = models.ImageField(upload_to=avatar_upload_path, null=True, blank=True)
    bio        = models.TextField(blank=True, default="")
    telephone  = models.CharField(max_length=25, blank=True, default="")
    ville      = models.CharField(max_length=100, blank=True, default="")
    pays       = models.CharField(max_length=100, blank=True, default="Cameroun")
    site_web   = models.URLField(blank=True, default="")
    # Niveau CECR (utilisé par les cours de langues)
    LEVEL_CHOICES = [
        ("A1","A1"), ("A2","A2"), ("B1","B1"),
        ("B2","B2"), ("C1","C1"), ("C2","C2"),
    ]
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, blank=True, default="A1")
    # Solde virtuel (pour programme d'affiliation, crédits IA, etc.)
    solde      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Plan souscrit
    PLANS = [("free","Gratuit"),("pro","Pro"),("enterprise","Enterprise")]
    plan       = models.CharField(max_length=20, choices=PLANS, default="free")
    plan_expiry = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        # Initiales par défaut
        initials = (self.user.first_name[:1] + self.user.last_name[:1]).upper() or self.user.username[:2].upper()
        return f"https://ui-avatars.com/api/?name={initials}&background=2E7D32&color=fff&size=128"


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="student_profile")
    class_level = models.ForeignKey("curriculum.ClassLevel", on_delete=models.PROTECT, null=True, blank=True)
    series = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"Profil élève: {self.user.username}"


class ParentStudentLink(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="children_links")
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="parent_links")

    class Meta:
        unique_together = ("parent", "student")

    def __str__(self):
        return f"{self.parent.username} -> {self.student.username}"


# ─── Plans d'abonnement par application ──────────────────────────

class AppPlan(models.Model):
    """Un plan tarifaire pour une application E-Shelle donnée."""

    LEVEL_CHOICES = [
        ("free",       "Gratuit"),
        ("trial",      "Essai"),
        ("starter",    "Starter"),
        ("pro",        "Pro"),
        ("enterprise", "Enterprise"),
    ]

    app_key      = models.CharField(max_length=30, choices=AppKey.choices, db_index=True)
    slug         = models.SlugField(max_length=60, unique=True)   # ex: "adgen-pro"
    name         = models.CharField(max_length=100)               # ex: "AdGen Pro"
    level        = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="starter")
    description  = models.TextField(blank=True)
    price_xaf    = models.PositiveIntegerField(default=0)         # 0 = gratuit
    price_eur    = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)       # 0 = illimité
    features     = models.JSONField(default=list)                 # liste de strings
    is_free      = models.BooleanField(default=False)
    is_popular   = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)
    order        = models.PositiveSmallIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["app_key", "order"]
        verbose_name = "Plan d'application"
        verbose_name_plural = "Plans d'application"

    def __str__(self):
        return f"{self.name} ({self.get_app_key_display()})"

    @property
    def price_xaf_formatted(self):
        if self.price_xaf == 0:
            return "Gratuit"
        return f"{self.price_xaf:,} FCFA".replace(",", " ")

    @property
    def app_icon(self):
        return APP_ICONS.get(self.app_key, "📦")

    @property
    def app_color(self):
        return APP_COLORS.get(self.app_key, "#6B7280")


# ─── Abonnements utilisateur ──────────────────────────────────────

class AppSubscription(models.Model):
    """Abonnement d'un utilisateur à un plan d'une application."""

    STATUS_CHOICES = [
        ("trial",     "Essai gratuit"),
        ("active",    "Actif"),
        ("expired",   "Expiré"),
        ("cancelled", "Annulé"),
        ("pending",   "En attente"),
    ]

    user       = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE,
        related_name="app_subscriptions"
    )
    plan       = models.ForeignKey(AppPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    payment_ref = models.CharField(max_length=200, blank=True, default="")
    auto_renew = models.BooleanField(default=False)
    notes      = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

    def __str__(self):
        return f"{self.user.username} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        if self.status in ("cancelled", "pending"):
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return self.status in ("active", "trial")

    @property
    def days_remaining(self):
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def is_expiring_soon(self):
        r = self.days_remaining
        return r is not None and r <= 7

    def check_expiry(self):
        """Marque expired si dépassé. Retourne True si statut changé."""
        if self.is_active and self.expires_at and timezone.now() > self.expires_at:
            self.status = "expired"
            self.save(update_fields=["status"])
            return True
        return False

    @classmethod
    def get_active_for_user(cls, user, app_key):
        """Retourne l'abonnement actif pour user + app, ou None."""
        subs = cls.objects.filter(
            user=user,
            plan__app_key=app_key,
        ).select_related("plan").order_by("-started_at")
        for sub in subs:
            if sub.is_active:
                return sub
        return None

    @classmethod
    def grant_free(cls, user, app_key):
        """Attribue automatiquement le plan gratuit d'une app si aucun abonnement."""
        existing = cls.objects.filter(user=user, plan__app_key=app_key).exists()
        if existing:
            return None
        try:
            plan = AppPlan.objects.get(app_key=app_key, is_free=True, is_active=True)
        except AppPlan.DoesNotExist:
            return None
        return cls.objects.create(user=user, plan=plan, status="active", expires_at=None)


# ─── Historique des paiements ─────────────────────────────────────

class PaymentHistory(models.Model):
    """Trace tous les paiements effectués sur la plateforme."""

    METHOD_CHOICES = [
        ("orange_money", "Orange Money"),
        ("mtn_momo",     "MTN MoMo"),
        ("stripe",       "Carte bancaire"),
        ("cinetpay",     "CinetPay"),
        ("manual",       "Manuel (admin)"),
        ("free",         "Gratuit"),
    ]

    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("success", "Succès"),
        ("failed",  "Échec"),
        ("refunded","Remboursé"),
    ]

    user         = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE,
        related_name="payment_history"
    )
    subscription = models.ForeignKey(
        AppSubscription, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payments"
    )
    amount_xaf   = models.PositiveIntegerField(default=0)
    method       = models.CharField(max_length=30, choices=METHOD_CHOICES, default="manual")
    reference    = models.CharField(max_length=200, unique=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description  = models.TextField(blank=True, default="")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paiement"
        verbose_name_plural = "Historique paiements"

    def __str__(self):
        return f"{self.user.username} — {self.amount_xaf} FCFA — {self.status}"

    @property
    def amount_formatted(self):
        if self.amount_xaf == 0:
            return "Gratuit"
        return f"{self.amount_xaf:,} FCFA".replace(",", " ")


# ─── Codes d'accès globaux (créés par l'admin, activés par le client) ───────

import secrets as _secrets
import string as _string


def _generate_code():
    """Génère un code unique format XXXX-XXXX-XXXX (ex: A3F2-9KL1-BT7W)."""
    chars = _string.ascii_uppercase + _string.digits
    parts = ["".join(_secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return "-".join(parts)


class GlobalAccessCode(models.Model):
    """
    Code d'accès créé par l'administrateur E-Shelle.
    Le client paie par Orange Money/MTN → l'admin crée un code → l'envoie au client.
    Le client l'active sur /accounts/activer/ → ses abonnements sont créés automatiquement.
    """

    PAYMENT_METHOD_CHOICES = [
        ("orange_money", "Orange Money"),
        ("mtn_momo",     "MTN MoMo"),
        ("wave",         "Wave"),
        ("cash",         "Espèces"),
        ("offert",       "Offert / Test"),
    ]

    # Le code lui-même
    code          = models.CharField(max_length=20, unique=True, default=_generate_code)
    label         = models.CharField(max_length=150, help_text="Ex: Pack AdGen Pro 30j — Jean Dupont")

    # Ce que donne le code
    apps          = models.JSONField(
        default=list,
        help_text="Liste des app_key accessibles. Ex: [\"adgen\", \"njangi\"] ou [\"all\"] pour tout."
    )
    duration_days = models.PositiveIntegerField(default=30, help_text="Durée d'accès en jours")
    price_xaf     = models.PositiveIntegerField(default=0, help_text="Montant reçu en FCFA")

    # Paiement reçu
    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="orange_money")
    payment_ref     = models.CharField(max_length=200, blank=True, default="", help_text="Référence paiement MoMo/Wave")
    client_name     = models.CharField(max_length=150, blank=True, default="", help_text="Nom du client pour référence")
    client_phone    = models.CharField(max_length=25, blank=True, default="", help_text="Téléphone du client")
    notes           = models.TextField(blank=True, default="", help_text="Notes internes (non visibles du client)")

    # Statut
    is_active     = models.BooleanField(default=True, help_text="Désactiver pour invalider le code")
    is_used       = models.BooleanField(default=False)
    activated_by  = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="activated_codes"
    )
    activated_at  = models.DateTimeField(null=True, blank=True)
    expires_at    = models.DateTimeField(null=True, blank=True, help_text="Calculé automatiquement à l'activation")

    created_at    = models.DateTimeField(auto_now_add=True)
    created_by    = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_codes"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Code d'accès"
        verbose_name_plural = "Codes d'accès"

    def __str__(self):
        status = "Utilisé" if self.is_used else "Disponible"
        return f"{self.code} — {self.label} [{status}]"

    @property
    def price_formatted(self):
        if self.price_xaf == 0:
            return "Gratuit / Offert"
        return f"{self.price_xaf:,} FCFA".replace(",", " ")

    @property
    def apps_display(self):
        if "all" in self.apps:
            return "Toutes les applications"
        labels = {k: v for k, v in AppKey.choices}
        return ", ".join(labels.get(a, a) for a in self.apps)

    def activate(self, user):
        """
        Active le code pour un utilisateur :
        - Crée les AppSubscription pour chaque app
        - Marque le code comme utilisé
        Retourne (True, message) ou (False, erreur).
        """
        from django.utils import timezone
        from datetime import timedelta

        if not self.is_active:
            return False, "Ce code a été désactivé."
        if self.is_used:
            return False, "Ce code a déjà été utilisé."

        # Déterminer les apps à activer
        all_keys = [k for k, _ in AppKey.choices]
        apps_to_activate = all_keys if "all" in self.apps else self.apps

        expires = timezone.now() + timedelta(days=self.duration_days)
        subs_created = []

        for app_key in apps_to_activate:
            # Chercher le plan pro/starter de cette app (le premier non-free actif)
            plan = (
                AppPlan.objects
                .filter(app_key=app_key, is_active=True, is_free=False)
                .order_by("order")
                .first()
            )
            if not plan:
                # Fallback : plan gratuit
                plan = AppPlan.objects.filter(app_key=app_key, is_active=True).order_by("order").first()
            if not plan:
                continue

            sub = AppSubscription.objects.create(
                user=user,
                plan=plan,
                status="active",
                expires_at=expires,
                payment_ref=f"CODE:{self.code}",
                notes=f"Activé via code {self.code}",
            )
            subs_created.append(sub)

        # Marquer le code
        self.is_used = True
        self.activated_by = user
        self.activated_at = timezone.now()
        self.expires_at = expires
        self.save(update_fields=["is_used", "activated_by", "activated_at", "expires_at"])

        # Enregistrer dans l'historique paiements
        if self.price_xaf > 0:
            import uuid
            PaymentHistory.objects.create(
                user=user,
                amount_xaf=self.price_xaf,
                method=self.payment_method,
                reference=f"CODE-{self.code}-{uuid.uuid4().hex[:8]}",
                status="success",
                description=f"Activation code {self.code} — {self.label}",
            )

        nb = len(subs_created)
        return True, f"{nb} application{'s' if nb > 1 else ''} activée{'s' if nb > 1 else ''} pendant {self.duration_days} jours."


# ─── Vérification d'email par code 6 chiffres ────────────────────

class EmailVerification(models.Model):
    user        = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="email_verification"
    )
    code        = models.CharField(max_length=6)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()
    tentatives  = models.PositiveSmallIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Vérification email"

    def __str__(self):
        return f"{self.user.email} — code:{self.code} — vérifié:{self.is_verified}"

    @property
    def est_expire(self):
        return timezone.now() > self.expires_at

    @classmethod
    def generer(cls, user):
        """Génère (ou renouvelle) un code 6 chiffres, valable 15 min."""
        code = str(random.randint(100000, 999999))
        obj, _ = cls.objects.update_or_create(
            user=user,
            defaults={
                "code":        code,
                "expires_at":  timezone.now() + timedelta(minutes=15),
                "tentatives":  0,
                "is_verified": False,
            },
        )
        return obj
