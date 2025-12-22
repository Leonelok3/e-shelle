from django.db import transaction
import uuid

from core.constants import LEVEL_ORDER
from preparation_tests.models import UserSkillProgress, CEFRCertificate
from preparation_tests.services.certificates import generate_cefr_certificate


# 🎯 Seuils réalistes CECR (premium)
LEVEL_THRESHOLDS = {
    "A1": 65,
    "A2": 70,
    "B1": 75,
    "B2": 80,
    "C1": 85,
    "C2": 101,  # verrou
}

# 🔒 Ordre CECR FIXE
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def try_unlock_next_level(
    *,
    user,
    exam_code: str,
    skill: str,
    score_percent: int,
) -> dict:
    """
    🔓 Moteur CECR officiel – multi-examens / multi-compétences
    """

    exam_code = exam_code.upper()
    skill = skill.lower()

    progress, _ = UserSkillProgress.objects.get_or_create(
        user=user,
        exam_code=exam_code,
        skill=skill,
        defaults={
            "score_percent": 0,
            "current_level": "A1",
            "total_attempts": 0,
        },
    )

    current_level = progress.current_level
    current_index = CEFR_LEVELS.index(current_level)

    # 🚫 Niveau max
    if current_level == "C2":
        return {
            "unlocked": False,
            "old_level": current_level,
            "reason": "already_max",
        }

    required_score = LEVEL_THRESHOLDS[current_level]

    # ❌ Score insuffisant
    if score_percent < required_score:
        return {
            "unlocked": False,
            "old_level": current_level,
            "score": score_percent,
            "required": required_score,
            "reason": "score_too_low",
        }

    new_level = CEFR_LEVELS[current_index + 1]
    certificate_generated = False

    # 🔒 TRANSACTION ATOMIQUE
    with transaction.atomic():
        # 📊 Progression
        progress.current_level = new_level
        progress.score_percent = score_percent
        progress.total_attempts += 1
        progress.save()

        # 🎓 Certificat CECR (1 par niveau / examen)
        cert, created = CEFRCertificate.objects.get_or_create(
            user=user,
            exam_code=exam_code,
            level=new_level,
        )

        if created:
            # 🔐 ID public vérifiable (QR / lien public)
            cert.public_id = uuid.uuid4().hex[:12].upper()
            cert.save(update_fields=["public_id"])

            # 📄 Génération PDF premium
            generate_cefr_certificate(
                user=user,
                exam_code=exam_code,
                level=new_level,
                public_id=cert.public_id,
            )

            certificate_generated = True

    return {
        "unlocked": True,
        "old_level": current_level,
        "new_level": new_level,
        "score": score_percent,
        "certificate_generated": certificate_generated,
        "reason": "success",
    }


def get_cefr_progress(*, user, exam_code: str, skill: str) -> dict:
    """
    📊 Données CECR prêtes pour l’UI (barre graphique)
    """

    exam_code = exam_code.upper()
    skill = skill.lower()

    progress = UserSkillProgress.objects.filter(
        user=user,
        exam_code=exam_code,
        skill=skill,
    ).first()

    current_level = progress.current_level if progress else "A1"
    score = progress.score_percent if progress else 0

    current_index = CEFR_LEVELS.index(current_level)
    global_progress = round(
        (current_index / (len(CEFR_LEVELS) - 1)) * 100
    )

    return {
        "current_level": current_level,
        "score_percent": score,
        "levels": CEFR_LEVELS,
        "current_index": current_index,
        "global_progress": global_progress,
    }
