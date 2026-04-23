from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Resource(models.Model):

    CATEGORY_CHOICES = [
        ("guides_pdf",           "Guides PDF"),
        ("tableaux_excel",       "Tableaux Excel"),
        ("preparation_tcf",      "Préparation TCF/TEF"),
        ("visa_immigration",     "Visa & Immigration"),
        ("emploi_international", "Emploi International"),
        ("lettres_modeles",      "Lettres & Modèles"),
        ("formation_langue",     "Formation Langue"),
    ]

    TYPE_CHOICES = [
        ("pdf",   "PDF"),
        ("xls",   "Excel"),
        ("doc",   "Word"),
        ("zip",   "ZIP"),
        ("other", "Autre"),
    ]

    DESTINATION_CHOICES = [
        ("canada",        "Canada"),
        ("france",        "France"),
        ("italie",        "Italie"),
        ("allemagne",     "Allemagne"),
        ("uk",            "Royaume-Uni"),
        ("belgique",      "Belgique"),
        ("espagne",       "Espagne"),
        ("europe",        "Europe"),
        ("japon",         "Japon"),
        ("maroc",         "Maroc"),
        ("international", "International"),
    ]

    title         = models.CharField("Titre", max_length=255)
    slug          = models.SlugField("Slug", max_length=255, unique=True, blank=True)
    description   = models.TextField("Description courte")
    long_description = models.TextField("Description longue (page détail)", blank=True,
                                        help_text="HTML simple ou markdown. Affiché sur la page produit.")
    what_inside   = models.TextField("Ce que contient le fichier (bullet points)", blank=True,
                                     help_text="Une ligne par point. Ex : ✅ 50 questions d'entraînement")
    category      = models.CharField("Catégorie", max_length=50, choices=CATEGORY_CHOICES)
    destination   = models.CharField("Destination", max_length=50, choices=DESTINATION_CHOICES, default="international")
    resource_type = models.CharField("Type de fichier", max_length=10, choices=TYPE_CHOICES, default="pdf")
    cover_image   = models.ImageField("Image de couverture", upload_to="resources/covers/", blank=True, null=True)
    preview_url   = models.URLField("Aperçu / extrait (lien externe)", blank=True, default="",
                                    help_text="Lien Google Drive, Canva ou PDF partiel visible avant achat.")
    file          = models.FileField("Fichier à télécharger", upload_to="resources/", blank=True, null=True)
    file_size     = models.CharField("Taille affichée", max_length=20, blank=True,
                                     help_text="Ex : 2.4 Mo — calculé automatiquement si vide")
    price_xaf     = models.PositiveIntegerField("Prix (XAF)", default=0, help_text="0 = gratuit")
    price_eur     = models.DecimalField("Prix (EUR)", max_digits=6, decimal_places=2, default=0)
    is_free       = models.BooleanField("Gratuit", default=False)
    is_premium    = models.BooleanField("Inclus abonnement Premium", default=False,
                                        help_text="Si coché, les abonnés Premium téléchargent gratuitement.")
    is_active     = models.BooleanField("Visible", default=True)
    is_featured   = models.BooleanField("Mis en avant (hero)", default=False)
    order         = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)
    downloads     = models.PositiveIntegerField("Nb téléchargements", default=0, editable=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Resource.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_category_label(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def get_destination_label(self):
        return dict(self.DESTINATION_CHOICES).get(self.destination, self.destination)

    def get_file_size_display(self):
        if self.file_size:
            return self.file_size
        if self.file:
            try:
                size = self.file.size
                if size < 1024:
                    return f"{size} o"
                elif size < 1024 ** 2:
                    return f"{size / 1024:.0f} Ko"
                else:
                    return f"{size / 1024 ** 2:.1f} Mo"
            except Exception:
                pass
        return ""

    def is_paid(self):
        """Ressource vendue à l'unité (prix > 0 et non gratuite)."""
        return not self.is_free and self.price_xaf > 0

    def whatsapp_buy_url(self, phone="237693649944"):
        """Lien WhatsApp pré-rempli pour acheter cette ressource."""
        import urllib.parse
        msg = (
            f"Bonjour, je voudrais acheter la ressource *{self.title}* "
            f"({self.price_xaf:,} XAF) sur Immigration97. "
            f"Pouvez-vous m'indiquer la marche à suivre ? 🙏"
        )
        return f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"

    def get_what_inside_list(self):
        if not self.what_inside:
            return []
        return [line.strip() for line in self.what_inside.splitlines() if line.strip()]


class ResourcePurchase(models.Model):
    """Achat individuel d'une ressource (hors abonnement)."""
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resource_purchases")
    resource       = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="purchases")
    amount_paid_xaf = models.PositiveIntegerField("Montant payé (XAF)", default=0)
    payment_method = models.CharField("Méthode de paiement", max_length=50, blank=True,
                                      help_text="Ex : Wave, MTN MoMo, Orange Money, PayPal…")
    payment_ref    = models.CharField("Référence paiement", max_length=100, blank=True)
    purchased_at   = models.DateTimeField("Date d'achat", auto_now_add=True)
    notes          = models.TextField("Notes admin", blank=True)
    is_active      = models.BooleanField("Accès actif", default=True,
                                         help_text="Décocher pour désactiver l'accès (remboursement, etc.)")

    class Meta:
        ordering = ["-purchased_at"]
        unique_together = [("user", "resource")]
        verbose_name = "Achat ressource"
        verbose_name_plural = "Achats ressources"

    def __str__(self):
        return f"{self.user} → {self.resource} ({self.amount_paid_xaf} XAF)"
