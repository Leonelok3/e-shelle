"""
Modèles de contenu : matières, documents d'examen, leçons vidéo.
"""
from django.db import models
from django.utils.text import slugify


class Subject(models.Model):
    """Matière / Cours pour un niveau d'examen donné."""
    LEVEL_CHOICES = [
        ('bepc', 'BEPC'),
        ('probatoire', 'Probatoire'),
        ('bac', 'Baccalauréat'),
        ('licence', 'Licence'),
        ('master', 'Master'),
    ]
    SUBJECT_TYPES = [
        ('math', 'Mathématiques'),
        ('french', 'Français'),
        ('physics', 'Physique-Chimie'),
        ('biology', 'SVT'),
        ('history', 'Histoire-Géo'),
        ('english', 'Anglais'),
        ('philosophy', 'Philosophie'),
        ('economics', 'Économie'),
        ('computer', 'Informatique'),
        ('other', 'Autre'),
    ]

    title = models.CharField(max_length=200, verbose_name='Titre')
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subject_type = models.CharField(max_length=30, choices=SUBJECT_TYPES, verbose_name='Type')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name='Niveau')
    year = models.IntegerField(null=True, blank=True, verbose_name='Année d\'examen')
    description = models.TextField(blank=True, verbose_name='Description')
    thumbnail = models.ImageField(
        upload_to='edu_platform/subjects/',
        null=True, blank=True,
        verbose_name='Image de couverture'
    )
    is_premium = models.BooleanField(default=True, verbose_name='Contenu premium')
    is_published = models.BooleanField(default=False, verbose_name='Publié')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.IntegerField(default=0, verbose_name='Ordre d\'affichage')
    allowed_plans = models.ManyToManyField(
        'edu_platform.SubscriptionPlan',
        blank=True,
        verbose_name='Plans autorisés'
    )

    class Meta:
        verbose_name = 'Matière'
        verbose_name_plural = 'Matières'
        ordering = ['level', 'order', 'title']

    def __str__(self):
        year_str = f" ({self.year})" if self.year else ""
        return f"{self.get_subject_type_display()} — {self.get_level_display()}{year_str}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"{self.get_subject_type_display()}-{self.get_level_display()}"
            if self.year:
                base += f"-{self.year}"
            self.slug = slugify(base)
            # Unicité du slug
            original = self.slug
            counter = 1
            while Subject.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def document_count(self):
        return self.documents.count()

    @property
    def video_count(self):
        return self.videos.count()


class ExamDocument(models.Model):
    """Sujet d'examen ou correction (PDF protégé)."""
    DOC_TYPE = [
        ('subject', 'Sujet d\'examen'),
        ('correction', 'Correction officielle'),
        ('correction_proposed', 'Correction proposée'),
        ('course_notes', 'Cours / Résumé'),
    ]

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Matière'
    )
    doc_type = models.CharField(max_length=30, choices=DOC_TYPE, verbose_name='Type de document')
    title = models.CharField(max_length=200, verbose_name='Titre')
    file = models.FileField(
        upload_to='edu_platform/documents/',
        verbose_name='Fichier PDF'
    )
    preview_pages = models.IntegerField(default=2, verbose_name='Pages en aperçu gratuit')
    is_downloadable = models.BooleanField(default=False, verbose_name='Téléchargeable')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size_kb = models.IntegerField(default=0, verbose_name='Taille (Ko)')

    class Meta:
        verbose_name = 'Document d\'examen'
        verbose_name_plural = 'Documents d\'examen'
        ordering = ['subject', 'doc_type', '-uploaded_at']

    def __str__(self):
        return f"{self.title} [{self.get_doc_type_display()}]"


class VideoLesson(models.Model):
    """Leçon vidéo liée à une matière."""
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='Matière'
    )
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(blank=True, verbose_name='Description')
    video_url = models.URLField(blank=True, verbose_name='URL YouTube/Vimeo (gratuit)')
    video_file = models.FileField(
        upload_to='edu_platform/videos/',
        null=True, blank=True,
        verbose_name='Fichier vidéo (premium)'
    )
    duration_minutes = models.IntegerField(default=0, verbose_name='Durée (minutes)')
    thumbnail = models.ImageField(
        upload_to='edu_platform/video_thumbnails/',
        null=True, blank=True,
        verbose_name='Miniature'
    )
    is_preview = models.BooleanField(default=False, verbose_name='Extrait gratuit')
    order = models.IntegerField(default=0, verbose_name='Ordre')
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.IntegerField(default=0, verbose_name='Nombre de vues')

    class Meta:
        verbose_name = 'Leçon vidéo'
        verbose_name_plural = 'Leçons vidéo'
        ordering = ['subject', 'order']

    def __str__(self):
        return f"{self.title} ({self.duration_minutes} min)"

    def increment_views(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
