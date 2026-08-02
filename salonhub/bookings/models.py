from django.db import models
from salonhub.salons.models import Salon, Service


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de confirmation"
        CONFIRMED = "confirmed", "Confirmé"
        CANCELLED = "cancelled", "Annulé"
        DONE = "done", "Terminé"

    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="appointments")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="appointments")
    client_name = models.CharField("Nom du client", max_length=150)
    client_phone = models.CharField("Téléphone du client", max_length=20)
    date = models.DateField("Date du rendez-vous")
    time = models.TimeField("Heure du rendez-vous")
    note = models.TextField("Note", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.client_name} — {self.salon.name} — {self.date} {self.time}"
