from preparation_tests.models import CourseLesson
from core.constants import LEVEL_ORDER


def recommend_lessons(
    *,
    user,
    exam_code: str,
    per_section: dict,
    limit_per_skill: int = 2,
):
    """
    🎯 Recommande des leçons ciblées par compétence
    en fonction des faiblesses détectées
    """

    profile = getattr(user, "profile", None)
    user_level = profile.level if profile and profile.level else "A1"
    user_level_order = LEVEL_ORDER.get(user_level, 0)

    recommendations = []

    for skill, data in per_section.items():
        pct = data["pct"]

        # 👉 seuil : on recommande si < 70%
        if pct >= 70:
            continue

        # section en minuscule (CO → co)
        section_code = skill.lower()

        # leçons accessibles uniquement
        lessons = (
            CourseLesson.objects.filter(
                exams__code__iexact=exam_code,
                section=section_code,
                is_published=True,
            )
            .order_by("level", "order")
        )

        added = 0

        for lesson in lessons:
            lesson_level_order = LEVEL_ORDER.get(lesson.level, 0)

            # 🔒 verrouillage CECRL
            if lesson_level_order > user_level_order:
                continue

            recommendations.append(
                {
                    "skill": skill,
                    "lesson": lesson,
                    "reason": f"Score {pct}% — renforcement recommandé",
                }
            )

            added += 1
            if added >= limit_per_skill:
                break

    return recommendations
