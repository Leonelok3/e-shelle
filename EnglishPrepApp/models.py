from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================
# TESTS D'ANGLAIS (MODULE SIMPLE)
# ============================

class EnglishTest(models.Model):
    EXAM_CHOICES = [
        ('GENERAL', 'Général anglais'),
        ('IELTS', 'IELTS'),
        ('TOEFL', 'TOEFL'),
        ('TOEIC', 'TOEIC'),
    ]

    LEVEL_CHOICES = [
        ('A1', 'A1 Débutant'),
        ('A2', 'A2 Élémentaire'),
        ('B1', 'B1 Intermédiaire'),
        ('B2', 'B2 Intermédiaire avancé'),
        ('C1', 'C1 Avancé'),
        ('C2', 'C2 Maîtrise'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    exam_type = models.CharField(max_length=20, choices=EXAM_CHOICES, default='GENERAL')
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, default='B1')
    duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)  # pour masquer/afficher un test

    def __str__(self):
        return f"{self.name} ({self.level})"


class EnglishQuestion(models.Model):
    SKILL_CHOICES = [
        ('READING', 'Reading'),
        ('LISTENING', 'Listening'),
        ('USE_OF_ENGLISH', 'Grammar / Vocabulary'),
    ]

    test = models.ForeignKey(EnglishTest, on_delete=models.CASCADE, related_name='questions')
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES, default='READING')
    question_text = models.TextField()

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    CORRECT_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    correct_option = models.CharField(max_length=1, choices=CORRECT_CHOICES)
    explanation = models.TextField(blank=True)

    # pour plus tard (listening)
    audio_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Q{self.id} - {self.test.name}"


class UserTestSession(models.Model):
    """
    Une tentative de test d'anglais pour un utilisateur.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='english_test_sessions')
    test = models.ForeignKey(EnglishTest, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)  # en pourcentage
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    

    def __str__(self):
        return f"Session {self.id} - {self.user} - {self.test} ({self.score}%)"


class UserAnswer(models.Model):
    """
    Réponse d'un utilisateur à une question d'anglais.
    """
    session = models.ForeignKey(UserTestSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(EnglishQuestion, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, choices=EnglishQuestion.CORRECT_CHOICES)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer by {self.session.user} to Q{self.question.id}"

# ============================
#  CONFIG GAMIFICATION ANGLAIS
# ============================

# Paliers de niveaux en XP (facile à ajuster)
LEVEL_THRESHOLDS = [
    (1, 0),
    (2, 100),
    (3, 250),
    (4, 500),
    (5, 900),
    (6, 1400),
]

# Facteur de difficulté selon le type d'examen
EXAM_XP_FACTOR = {
    "GENERAL": 1.0,
    "IELTS": 1.2,
    "TOEFL": 1.2,
    "TOEIC": 1.1,
}


def level_from_xp(xp: int) -> int:
    """
    Convertit l'XP en niveau.
    Au-delà du dernier palier, on ajoute +1 niveau tous les 400 XP.
    """
    xp = max(0, int(xp or 0))

    base_level = 1
    last_threshold = 0

    for lvl, threshold in LEVEL_THRESHOLDS:
        if xp >= threshold:
            base_level = lvl
            last_threshold = threshold
        else:
            break

    # Progression continue après le dernier palier
    max_level, max_xp = LEVEL_THRESHOLDS[-1]
    if xp <= max_xp:
        return base_level

    extra = xp - max_xp
    return max_level + extra // 400


def compute_badges_for_profile(profile) -> list[str]:
    """
    Génère la liste des badges à partir des stats du profil.
    Facile à étendre : on ajoute juste des if.
    """
    badges: list[str] = []

    # Progression générale
    if profile.total_tests >= 1:
        badges.append("Premier test ✅")
    if profile.total_tests >= 10:
        badges.append("Testeur régulier")
    if profile.total_tests >= 30:
        badges.append("Marathonien des tests")

    # XP
    if profile.xp >= 100:
        badges.append("Débutant")
    if profile.xp >= 500:
        badges.append("Intermédiaire")
    if profile.xp >= 1000:
        badges.append("Avancé")
    if profile.xp >= 2000:
        badges.append("Hard worker")

    # Scores
    if profile.best_score >= 80:
        badges.append("Solide en anglais")
    if profile.best_score >= 90:
        badges.append("Perfectionniste")

    return badges

class EnglishUserProfile(models.Model):
    """
    Profil global anglais : XP, niveau, badges, stats.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='english_profile')
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    total_tests = models.PositiveIntegerField(default=0)
    best_score = models.FloatField(default=0)
    badges = models.JSONField(default=list)  # Liste de strings

    def __str__(self):
        return f"Profil anglais de {self.user}"

    def add_result(self, score: float, questions_count: int, exam_type: str | None = None):
        """
        Mise à jour du profil après un test.

        - score : pourcentage 0–100
        - questions_count : nombre de questions du test
        - exam_type : 'IELTS', 'TOEFL', 'TOEIC' ou 'GENERAL'
        """

        # Sécurisation des valeurs
        score = float(score or 0.0)
        score = max(0.0, min(score, 100.0))

        questions_count = int(questions_count or 0)
        if questions_count < 1:
            questions_count = 1

        # 1) Calcul de l'XP brute
        # Idée : plus il y a de questions et plus le score est haut, plus l'XP monte.
        base_xp = (score / 100.0) * questions_count * 10  # 10 = facteur de base

        # 2) Pondération par type d'examen
        exam_type = (exam_type or "GENERAL").upper()
        factor = EXAM_XP_FACTOR.get(exam_type, 1.0)

        gained_xp = int(base_xp * factor)
        if gained_xp < 0:
            gained_xp = 0

        # 3) Application
        self.xp += gained_xp
        self.total_tests += 1

        if score > (self.best_score or 0):
            self.best_score = score

        # 4) Recalcul du niveau et des badges
        self.level = level_from_xp(self.xp)
        self.badges = compute_badges_for_profile(self)

        self.save()
        return gained_xp  # pratique si tu veux afficher "Tu as gagné +XX XP"


# --- NOUVEAUX MODÈLES POUR COURS & EXERCICES ---

class SkillArea(models.TextChoices):
    LISTENING = "LISTENING", "CO – Compréhension orale (Listening)"
    READING = "READING", "CE – Compréhension écrite (Reading)"
    WRITING = "WRITING", "EE – Expression écrite (Writing)"
    SPEAKING = "SPEAKING", "EO – Expression orale (Speaking)"
    USE_OF_ENGLISH = "USE_OF_ENGLISH", "Grammaire / Vocabulaire"


class EnglishLesson(models.Model):
    """
    Leçon liée à un examen précis (IELTS, TOEFL, etc.)
    Exemple : 'CO – Stratégies Listening pour IELTS B2'
    """
    test = models.ForeignKey(
        "EnglishTest",
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=200)
    skill = models.CharField(
        max_length=32,
        choices=SkillArea.choices,
        help_text="CO / CE / EO / EE / Grammaire.",
    )
    goal = models.CharField(
        max_length=120,
        blank=True,
        help_text="Ex : Immigration Canada, Études, Travail.",
    )
    level = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex : B1, B2, C1… (optionnel).",
    )
    short_description = models.TextField(blank=True)
    content = models.TextField(
        blank=True,
        help_text="Texte de cours, plan de leçon, lien vers PDF, etc.",
    )
    video_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["skill", "order", "title"]

    def __str__(self):
        return f"{self.title} ({self.get_skill_display()})"


class EnglishExercise(models.Model):
    """
    Exercice rattaché à une leçon (drills, fiches, lien externe, etc.)
    """
    class Difficulty(models.TextChoices):
        EASY = "EASY", "Facile"
        MEDIUM = "MEDIUM", "Intermédiaire"
        HARD = "HARD", "Avancé"

    lesson = models.ForeignKey(
        EnglishLesson,
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    title = models.CharField(max_length=200)
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
    )
    description = models.TextField(blank=True)
    content = models.TextField(
        blank=True,
        help_text="Consignes, texte de l’exercice, etc.",
    )
    external_url = models.URLField(
        blank=True,
        help_text="Lien vers vidéo, doc, Google Drive, etc. (optionnel).",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["lesson", "order", "title"]

    def __str__(self):
        return f"{self.title} – {self.get_difficulty_display()}"
