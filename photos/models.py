from django.db import models

PHOTO_TYPES = [
    ("dv_lottery", "DV Lottery (Green Card)"),
    ("visa_france", "Visa France"),
    ("visa_uk", "Visa UK"),
    ("visa_canada", "Visa Canada"),
]

class Photo(models.Model):
    photo_type = models.CharField(max_length=32, choices=PHOTO_TYPES)
    image = models.ImageField(upload_to="input/")
    # Pour le MVP on copie juste l’upload dans processed_image
    processed_image = models.ImageField(upload_to="output/", blank=True, null=True)
    is_paid = models.BooleanField(default=False)  # gardé si tu veux activer un paiement plus tard
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_photo_type_display()} #{self.pk}"
