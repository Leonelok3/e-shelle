# preparation_tests/services/study_plan.py

from preparation_tests.models import (
    CourseLesson,
    StudyPlanProgress,
)

# =====================================================
# 🧭 CONFIGURATION DES PLANS PAR NIVEAU CECRL
# =====================================================

CEFR_PLAN = {
    "A1": {
        "days": 14,
        "focus": ["co", "ce"],
    },
    "A2": {
        "days": 21,
        "focus": ["co", "ce", "ee"],
    },
    "B1": {
        "days": 28,
        "focus": ["co", "ce", "ee", "eo"],
    },
    "B2": {
        "days": 30,
        "focus": ["co", "ce", "ee", "eo"],
    },
    "C1": {
        "days": 30,
        "focus": ["co", "ce", "ee", "eo"],
    },
    "C2": {
        "days": 30,
        "focus": ["co", "ce", "ee", "eo"],
    },
}


# =====================================================
# 🗺️ CONSTRUCTION DU PLAN D’ÉTUDE PERSONNALISÉ
# =====================================================

def build_study_plan(*, user, exam_code):
    """
    Génère OU récupère un plan d’étude personnalisé basé sur :
    - le niveau CECRL de l’utilisateur
    - l’examen (TEF / TCF / DELF / DALF)
    - la progression sauvegardée
    """

    # 🔐 Sécurité
    if not user or not user.is_authenticated:
        return None

    exam_code = exam_code.lower()

    # 🎓 Niveau utilisateur (fallback sécurisé)
    profile = getattr(user, "profile", None)
    level = getattr(profile, "level", "A1")
    level = level.upper()

    config = CEFR_PLAN.get(level, CEFR_PLAN["A1"])

    # 📌 Création ou récupération de la progression
    progress, _ = StudyPlanProgress.objects.get_or_create(
        user=user,
        exam_code=exam_code,
        defaults={
            "current_day": 1,
            "total_days": config["days"],
            "is_active": True,
        },
    )

    # 📚 Leçons disponibles (filtrage strict & sûr)
    lessons_qs = (
        CourseLesson.objects.filter(
            exam__code__iexact=exam_code,
            level=level,
            section__in=config["focus"],
            is_published=True,
        )
        .order_by("section", "order", "id")
    )

    lessons = list(lessons_qs)

    # 🧩 Construction des jours
    days = []
    lesson_index = 0
    total_days = progress.total_days

    for day in range(1, total_days + 1):

        lesson = lessons[lesson_index] if lesson_index < len(lessons) else None

        days.append({
            "day": day,
            "is_current": day == progress.current_day,
            "is_completed": day < progress.current_day,
            "section": lesson.section.upper() if lesson else None,
            "lesson": lesson,
        })

        if lesson:
            lesson_index += 1

    # 📊 Résultat final pour l’UI
    return {
        "exam_code": exam_code,
        "level": level,
        "current_day": progress.current_day,
        "total_days": total_days,
        "progress_percent": int(
            (max(progress.current_day - 1, 0) / total_days) * 100
        ),
        "days": days,
        "is_completed": progress.is_completed,
        "is_active": progress.is_active,
    }


# =====================================================
# ⏭️ AVANCER DANS LE PLAN
# =====================================================

def advance_study_day(*, user, exam_code):
    """
    Passe au jour suivant du plan d’étude
    """

    if not user or not user.is_authenticated:
        return None

    exam_code = exam_code.lower()

    plan = StudyPlanProgress.objects.filter(
        user=user,
        exam_code=exam_code,
        is_active=True,
    ).first()

    if not plan:
        return None

    if plan.is_completed:
        return plan

    if plan.current_day < plan.total_days:
        plan.current_day += 1
        plan.save(update_fields=["current_day"])
    else:
        plan.is_completed = True
        plan.is_active = False
        plan.save(update_fields=["is_completed", "is_active"])

    return plan


# =====================================================
# 🧠 ADAPTATION IA (POST-RÉSULTATS)
# =====================================================

def get_priority_sections(per_section):
    """
    Classe les compétences du plus faible au plus fort
    per_section = {
        "CO": {"pct": 65},
        "CE": {"pct": 80},
        ...
    }
    """

    if not per_section:
        return []

    return sorted(
        per_section.items(),
        key=lambda x: x[1].get("pct", 0)
    )


def adapt_study_plan(*, plan_data, per_section):
    """
    Réorganise le plan selon les faiblesses détectées
    (sans casser la structure des jours)
    """

    if not plan_data or not per_section:
        return plan_data

    priorities = get_priority_sections(per_section)
    ordered_sections = [p[0].lower() for p in priorities]

    adapted_days = []

    for day in plan_data["days"]:
        lesson = day.get("lesson")

        if lesson:
            # 🔁 Priorité aux sections faibles
            if lesson.section.lower() in ordered_sections:
                adapted_days.append(day)
            else:
                adapted_days.append(day)
        else:
            adapted_days.append(day)

    plan_data["days"] = adapted_days
    return plan_data
