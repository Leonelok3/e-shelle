from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

GERMAN_LEVEL_CHOICES = [
    ("A1", "A1"),
    ("A2", "A2"),
    ("B1", "B1"),
    ("B2", "B2"),
    ("C1", "C1"),
    ("C2", "C2"),
]


class GermanExam(models.Model):
    """
    Parcours / examen d'allemand :
    - Goethe, telc, TestDaF, DSH, général / visa...
    - associé à un niveau CECR (A1–C2).
    """
    EXAM_TYPES = [
        ("GOETHE", "Goethe-Zertifikat"),
        ("TELC", "telc Deutsch"),
        ("TESTDAF", "TestDaF"),
        ("DSH", "DSH"),
        ("GENERAL", "Général / Visa"),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default="GENERAL")
    level = models.CharField(max_length=2, choices=GERMAN_LEVEL_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.level})"


class GermanLesson(models.Model):
    """
    Leçon de cours pour un examen donné.
    """
    SKILL_CHOICES = [
        ("HOREN", "Hören (Compréhension orale)"),
        ("LESEN", "Lesen (Compréhension écrite)"),
        ("SPRECHEN", "Sprechen (Expression orale)"),
        ("SCHREIBEN", "Schreiben (Expression écrite)"),
        ("GRAMMATIK", "Grammatik"),
        ("WORTSCHATZ", "Wortschatz (Vocabulaire)"),
    ]

    exam = models.ForeignKey(
        GermanExam,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES, default="GRAMMATIK")
    order = models.PositiveIntegerField(default=1)
    intro = models.TextField(blank=True)
    content = models.TextField(
        help_text="Contenu de la leçon (texte, explications, exemples). "
                  "Tu peux mettre du HTML simple ou du Markdown."
    )

    class Meta:
        ordering = ["exam", "order"]

    def __str__(self):
        return f"{self.exam.title} – {self.title}"


class GermanExercise(models.Model):
    """
    Exercice type QCM lié à une leçon.
    """
    lesson = models.ForeignKey(
        GermanLesson,
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    question_text = models.TextField()

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    CORRECT_CHOICES = [
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    ]
    correct_option = models.CharField(max_length=1, choices=CORRECT_CHOICES)

    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Exercice {self.id} – {self.lesson.title}"


class GermanResource(models.Model):
    """
    Ressource associée à un examen ou une leçon :
    - PDF (cours / exercices corrigés)
    - vidéo YouTube
    - article externe...
    """
    RESOURCE_TYPES = [
        ("PDF", "PDF (cours / exercices)"),
        ("VIDEO", "Vidéo"),
        ("LINK", "Lien / article"),
        ("AUDIO", "Audio / podcast"),
        ("OTHER", "Autre"),
    ]

    exam = models.ForeignKey(
        GermanExam,
        on_delete=models.CASCADE,
        related_name="resources",
        null=True,
        blank=True,
        help_text="Laisse vide si la ressource ne dépend que de la leçon.",
    )
    lesson = models.ForeignKey(
        GermanLesson,
        on_delete=models.CASCADE,
        related_name="resources",
        null=True,
        blank=True,
        help_text="Optionnel. Pour lier une ressource à une leçon précise.",
    )
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES, default="PDF")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(
        help_text="Lien vers le PDF / vidéo / ressource (Drive, YouTube, site externe...)."
    )

    def __str__(self):
        return f"{self.title} ({self.resource_type})"


class GermanPlacementQuestion(models.Model):
    """
    Questions du test de niveau d’entrée (placement test).
    """
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    CORRECT_CHOICES = [
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    ]
    correct_option = models.CharField(max_length=1, choices=CORRECT_CHOICES)

    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Placement Q{self.order} – {self.question_text[:40]}..."


class GermanTestSession(models.Model):
    """
    Une simulation d'examen allemand pour un utilisateur.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="german_test_sessions",
    )
    exam = models.ForeignKey(
        GermanExam,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)  # en %
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"DE Session {self.id} – {self.user} – {self.exam} ({self.score}%)"


class GermanUserAnswer(models.Model):
    """
    Réponse d'un utilisateur dans une session d'examen.
    """
    session = models.ForeignKey(
        GermanTestSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    exercise = models.ForeignKey(GermanExercise, on_delete=models.CASCADE)
    selected_option = models.CharField(
        max_length=1,
        choices=GermanExercise.CORRECT_CHOICES,
    )
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session.user} – Ex {self.exercise.id}"


class GermanUserProfile(models.Model):
    """
    Profil global allemand : XP, niveau, badges, stats + niveau conseillé.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="german_profile",
    )
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    total_tests = models.PositiveIntegerField(default=0)
    best_score = models.FloatField(default=0)
    badges = models.JSONField(default=list)

    # Niveau conseillé par le test de placement (A1–C2)
    placement_level = models.CharField(
        max_length=2,
        choices=GERMAN_LEVEL_CHOICES,
        blank=True,
        null=True,
    )
    placement_score = models.FloatField(
        blank=True,
        null=True,
        help_text="Score (%) obtenu au dernier test de placement.",
    )

    def __str__(self):
        return f"Profil allemand de {self.user}"

    def add_result(self, score: float, questions_count: int):
        if questions_count < 1:
            questions_count = 1

        gained_xp = int(score * questions_count / 10)
        self.xp += max(gained_xp, 0)
        self.total_tests += 1

        if score > self.best_score:
            self.best_score = score

        self.level = self.compute_level()
        self.badges = self.compute_badges()
        self.save()

    def compute_level(self) -> int:
        xp = self.xp
        if xp < 100:
            return 1
        elif xp < 250:
            return 2
        elif xp < 500:
            return 3
        elif xp < 900:
            return 4
        elif xp < 1400:
            return 5
        else:
            extra = xp - 1400
            return 6 + extra // 400

    def compute_badges(self) -> list:
        badges = []
        if self.xp >= 100:
            badges.append("Starter A1-A2")
        if self.xp >= 500:
            badges.append("Mittelstufe B1-B2")
        if self.xp >= 1000:
            badges.append("Fortgeschritten C1-C2")
        if self.best_score >= 90:
            badges.append("Perfektionist")
        if self.total_tests >= 20:
            badges.append("Prüfungsprofi")
        return badges
