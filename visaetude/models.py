from django.db import models
from django.contrib.auth.models import User

# Modèle Profil Utilisateur
class UserProfile(models.Model):
    STUDY_LEVELS = [
        ('licence', 'Licence'),
        ('master', 'Master'),
        ('doctorat', 'Doctorat'),
    ]
    
    COUNTRIES = [
        ('cameroun', 'Cameroun'),
        ('senegal', 'Sénégal'),
        ('cote_ivoire', "Côte d'Ivoire"),
        ('autre', 'Autre'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    pays_origine = models.CharField(max_length=50, choices=COUNTRIES)
    niveau_etude = models.CharField(max_length=20, choices=STUDY_LEVELS)
    domaine_etude = models.CharField(max_length=100)
    budget_disponible = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profil de {self.user.username}"
    
    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"


# Modèle Pays Destination
class Country(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)  # CAN, USA, FRA, etc.
    description = models.TextField()
    delai_traitement = models.CharField(max_length=100)  # Ex: "2-4 mois"
    cout_visa = models.DecimalField(max_digits=10, decimal_places=2)
    taux_acceptation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Pourcentage
    image = models.ImageField(upload_to='countries/', null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"


# Modèle Information par Pays
class CountryGuide(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='guides')
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    ordre = models.IntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.pays.nom} - {self.titre}"
    
    class Meta:
        verbose_name = "Guide Pays"
        verbose_name_plural = "Guides Pays"
        ordering = ['ordre']


# Modèle Document Requis
class RequiredDocument(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='documents_requis')
    nom = models.CharField(max_length=200)
    description = models.TextField()
    exemple = models.FileField(upload_to='documents/exemples/', null=True, blank=True)
    obligatoire = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.pays.nom} - {self.nom}"
    
    class Meta:
        verbose_name = "Document Requis"
        verbose_name_plural = "Documents Requis"
        ordering = ['ordre']


# Modèle Checklist Utilisateur
class UserChecklist(models.Model):
    STATUS_CHOICES = [
        ('non_commence', 'Non commencé'),
        ('en_cours', 'En cours'),
        ('complete', 'Complété'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checklists')
    pays = models.ForeignKey(Country, on_delete=models.CASCADE)
    document = models.ForeignKey(RequiredDocument, on_delete=models.CASCADE)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='non_commence')
    fichier = models.FileField(upload_to='documents/users/', null=True, blank=True)
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.document.nom}"
    
    class Meta:
        verbose_name = "Checklist Utilisateur"
        verbose_name_plural = "Checklists Utilisateurs"
        unique_together = ['user', 'document']


# Modèle Timeline/Jalons
class Milestone(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jalons')
    pays = models.ForeignKey(Country, on_delete=models.CASCADE)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date_prevue = models.DateField()
    complete = models.BooleanField(default=False)
    date_completion = models.DateField(null=True, blank=True)
    ordre = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.titre}"
    
    class Meta:
        verbose_name = "Jalon"
        verbose_name_plural = "Jalons"
        ordering = ['ordre', 'date_prevue']


# Modèle FAQ
class FAQ(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='faqs', null=True, blank=True)
    question = models.CharField(max_length=500)
    reponse = models.TextField()
    ordre = models.IntegerField(default=0)
    populaire = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['-populaire', 'ordre']