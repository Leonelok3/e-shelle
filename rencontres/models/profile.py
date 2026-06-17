from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class ProfilRencontre(models.Model):
    """Profil de rencontre lié au User existant du projet."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profil_rencontre'
    )

    # Identité
    prenom_affiche = models.CharField(max_length=50)
    date_naissance = models.DateField()
    genre = models.CharField(max_length=20, choices=[
        ('homme', 'Homme'),
        ('femme', 'Femme'),
        ('autre', 'Autre / Préfère ne pas préciser'),
    ])
    orientation = models.CharField(max_length=20, choices=[
        ('heterosexuel', 'Hétérosexuel(le)'),
        ('homosexuel', 'Homosexuel(le)'),
        ('bisexuel', 'Bisexuel(le)'),
        ('autre', 'Autre'),
    ], default='heterosexuel')

    # Localisation
    pays = models.CharField(max_length=100)
    ville = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Origine et diaspora
    origine_ethnique = models.CharField(
        max_length=100, blank=True,
        help_text="Ex: Bamiléké, Wolof, Yoruba, Européen, etc."
    )
    nationalite = models.CharField(max_length=100)
    est_diaspora = models.BooleanField(default=False)
    pays_residence = models.CharField(max_length=100, blank=True)

    # Apparence
    taille_cm = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(100), MaxValueValidator(250)]
    )
    morphologie = models.CharField(max_length=30, choices=[
        ('mince', 'Mince'),
        ('normale', 'Normale'),
        ('athletique', 'Athlétique'),
        ('ronde', 'Ronde / Enrobée'),
        ('grande', 'Grande'),
    ], blank=True)
    teint = models.CharField(max_length=30, blank=True)

    # Situation personnelle
    situation_matrimoniale = models.CharField(max_length=30, choices=[
        ('celibataire', 'Célibataire'),
        ('divorce', 'Divorcé(e)'),
        ('veuf', 'Veuf/Veuve'),
        ('separe', 'Séparé(e)'),
    ])
    a_des_enfants = models.BooleanField(default=False)
    nb_enfants = models.IntegerField(default=0)
    veut_des_enfants = models.CharField(max_length=20, choices=[
        ('oui', 'Oui'),
        ('non', 'Non'),
        ('peut_etre', 'Peut-être'),
        ('deja_assez', "J'en ai déjà assez"),
    ])

    # Formation et travail
    niveau_etude = models.CharField(max_length=50, choices=[
        ('primaire', 'Primaire'),
        ('secondaire', 'Secondaire / BAC'),
        ('bac2', 'BAC+2'),
        ('licence', 'Licence / BAC+3'),
        ('master', 'Master / BAC+5'),
        ('doctorat', 'Doctorat'),
    ])
    profession = models.CharField(max_length=100, blank=True)
    revenus = models.CharField(max_length=30, choices=[
        ('modeste', 'Modeste'),
        ('moyen', 'Moyen'),
        ('confortable', 'Confortable'),
        ('eleve', 'Élevé'),
        ('prefere_pas', 'Préfère ne pas dire'),
    ], blank=True)

    # Religion
    religion = models.CharField(max_length=50, choices=[
        ('chretien', 'Chrétien(ne)'),
        ('musulman', 'Musulman(e)'),
        ('aucune', 'Aucune'),
        ('autre', 'Autre'),
        ('spirituel', 'Spirituel(le)'),
    ], blank=True)
    pratique_religieuse = models.CharField(max_length=20, choices=[
        ('tres_pratiquant', 'Très pratiquant(e)'),
        ('pratiquant', 'Pratiquant(e)'),
        ('peu_pratiquant', 'Peu pratiquant(e)'),
        ('non_pratiquant', 'Non pratiquant(e)'),
    ], blank=True)

    # Langues parlées
    langues = models.JSONField(
        default=list,
        help_text="['Français', 'Anglais', 'Ewondo', ...]"
    )

    # À propos de moi
    biographie = models.TextField(max_length=1000, blank=True)
    ce_que_je_cherche = models.TextField(max_length=500, blank=True)
    interets = models.JSONField(
        default=list,
        help_text="['Voyage', 'Cuisine', 'Sport', ...]"
    )

    # Critères recherche partenaire
    recherche_age_min = models.IntegerField(default=18)
    recherche_age_max = models.IntegerField(default=60)
    recherche_genre = models.CharField(max_length=20, blank=True)
    recherche_pays = models.JSONField(default=list)
    recherche_religion = models.JSONField(default=list)
    recherche_distance_km = models.IntegerField(default=500)

    # Photo principale
    photo_principale = models.ImageField(
        upload_to='rencontres/photos/%Y/%m/',
        null=True, blank=True
    )

    # Statut et vérification
    est_verifie = models.BooleanField(default=False)
    badge_verifie = models.BooleanField(default=False)
    est_actif = models.BooleanField(default=True)
    est_premium = models.BooleanField(default=False)
    profil_complet = models.IntegerField(
        default=0,
        help_text="Pourcentage de complétion 0-100"
    )

    # Activité
    derniere_connexion = models.DateTimeField(auto_now=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    vues_profil = models.IntegerField(default=0)

    # Paramètres de confidentialité
    afficher_en_ligne = models.BooleanField(default=True)
    afficher_distance = models.BooleanField(default=True)
    qui_peut_ecrire = models.CharField(max_length=20, choices=[
        ('tous', 'Tout le monde'),
        ('matchs', 'Mes matchs uniquement'),
        ('premium', 'Membres premium uniquement'),
    ], default='tous')

    class Meta:
        verbose_name = "Profil de rencontre"
        verbose_name_plural = "Profils de rencontre"
        ordering = ['-derniere_connexion']

    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) <
            (self.date_naissance.month, self.date_naissance.day)
        )

    def calculer_completion(self):
        """Calcule le % de complétion du profil."""
        champs = [
            self.prenom_affiche,
            self.biographie,
            self.profession,
            self.photo_principale,
            self.origine_ethnique,
            self.ce_que_je_cherche,
            bool(self.interets),
        ]
        remplis = sum(1 for c in champs if c)
        self.profil_complet = int((remplis / len(champs)) * 100)
        self.save(update_fields=['profil_complet'])
        return self.profil_complet

    def get_matchs_actifs(self):
        from rencontres.models.matching import Match
        from django.db.models import Q
        return Match.objects.filter(
            Q(profil_1=self) | Q(profil_2=self),
            est_actif=True
        )

    def est_bloque_par(self, autre_profil):
        from rencontres.models.matching import Blocage
        return Blocage.objects.filter(bloqueur=autre_profil, bloque=self).exists()

    def a_bloque(self, autre_profil):
        from rencontres.models.matching import Blocage
        return Blocage.objects.filter(bloqueur=self, bloque=autre_profil).exists()

    def __str__(self):
        return f"{self.prenom_affiche}, {self.age()} ans — {self.ville}"


class PhotoProfil(models.Model):
    profil = models.ForeignKey(
        ProfilRencontre,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to='rencontres/photos/%Y/%m/')
    est_principale = models.BooleanField(default=False)
    est_approuvee = models.BooleanField(default=False)
    ordre = models.IntegerField(default=0)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Photo de profil"
        verbose_name_plural = "Photos de profil"
        ordering = ['ordre']

    def save(self, *args, **kwargs):
        # Si cette photo est définie comme principale, retirer le statut des autres
        if self.est_principale:
            PhotoProfil.objects.filter(
                profil=self.profil, est_principale=True
            ).exclude(pk=self.pk).update(est_principale=False)
        super().save(*args, **kwargs)

    @property
    def is_visible(self):
        return self.est_approuvee

    def __str__(self):
        return f"Photo {self.ordre} — {self.profil.prenom_affiche}"
