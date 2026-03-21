from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class RecruiterProfile(models.Model):
    SECTOR_CHOICES = [
        ("BTP", "BTP / Construction"),
        ("SANTE", "Santé / Médical"),
        ("IT", "Informatique / Tech"),
        ("COMPTA", "Comptabilité / Finance"),
        ("HOTEL", "Hôtellerie / Restauration"),
        ("AGRI", "Agriculture / Agroalimentaire"),
        ("INDUSTRIE", "Industrie / Logistique"),
        ("EDUCATION", "Éducation / Formation"),
        ("COMMERCE", "Commerce / Vente"),
        ("AUTRE", "Autre"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="recruiter_profile")
    company_name = models.CharField(max_length=150, blank=True)
    logo = models.ImageField(upload_to="recruiter_logos/", blank=True, null=True)
    description = models.TextField(blank=True, help_text="Présentation de l'entreprise")
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False, help_text="Entreprise vérifiée par l'équipe")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name or self.user.username}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("recruiters:public_profile", args=[self.pk])

class InterviewInviteStatus(models.TextChoices):
    SENT = "sent", "Envoyée"
    ACCEPTED = "accepted", "Acceptée"
    DECLINED = "declined", "Refusée"

class InterviewInvite(models.Model):
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invites")
    candidate_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_invites")

    subject = models.CharField(max_length=120, default="Invitation à entretien")
    message = models.TextField()

    status = models.CharField(max_length=20, choices=InterviewInviteStatus.choices, default=InterviewInviteStatus.SENT)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def accept(self):
        self.status = InterviewInviteStatus.ACCEPTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def decline(self):
        self.status = InterviewInviteStatus.DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def __str__(self):
        return f"Invite {self.recruiter.username} -> {self.candidate_user.username} ({self.status})"
