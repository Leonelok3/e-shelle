from django.db import models


class Resource(models.Model):

    CATEGORY_CHOICES = [
        ("guides_pdf",        "Guides PDF"),
        ("tableaux_excel",    "Tableaux Excel"),
        ("preparation_tcf",   "Préparation TCF"),
        ("visa_immigration",  "Visa & Immigration"),
        ("emploi_international", "Emploi International"),
    ]

    TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("xls", "Excel"),
        ("doc", "Word"),
        ("other", "Autre"),
    ]

    DESTINATION_CHOICES = [
        ("canada",       "Canada"),
        ("italie",       "Italie"),
        ("uk",           "UK"),
        ("japon",        "Japon"),
        ("espagne",      "Espagne"),
        ("europe",       "Europe"),
        ("international","International"),
        ("france",       "France"),
        ("belgique",     "Belgique"),
        ("maroc",        "Maroc"),
    ]

    cover_image  = models.ImageField("Image de couverture", upload_to="resources/covers/", blank=True, null=True)
    price_xaf    = models.PositiveIntegerField("Prix (XAF)", default=0, help_text="0 = gratuit")
    price_eur    = models.DecimalField("Prix (EUR)", max_digits=6, decimal_places=2, default=0)
    is_free      = models.BooleanField("Gratuit", default=False)
    preview_url  = models.URLField("Aperçu (lien externe)", blank=True, default="")
    title        = models.CharField("Titre", max_length=255)
    description  = models.TextField("Description courte")
    category     = models.CharField("Catégorie", max_length=50, choices=CATEGORY_CHOICES)
    destination  = models.CharField("Destination", max_length=50, choices=DESTINATION_CHOICES, default="international")
    resource_type= models.CharField("Type de fichier", max_length=10, choices=TYPE_CHOICES, default="pdf")
    file         = models.FileField("Fichier", upload_to="resources/", blank=True, null=True)
    file_size    = models.CharField("Taille affichée", max_length=20, blank=True,
                                    help_text="Ex : 2.4 Mo — rempli auto si vide")
    is_active    = models.BooleanField("Visible", default=True)
    is_premium   = models.BooleanField("Réservé Premium", default=False)
    order        = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"

    def __str__(self):
        return self.title

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
