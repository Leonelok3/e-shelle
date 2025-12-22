# preparation_tests/services/feedback.py

def build_smart_feedback(
    exam_code: str,
    global_pct: int,
    per_section: dict,
    unlocked_info: dict | None = None,
):
    """
    Génère un feedback pédagogique intelligent après test blanc
    """

    # 🎯 TON GLOBAL
    if global_pct >= 85:
        tone = "excellent"
        global_message = (
            "🚀 Niveau excellent. Tu es très proche (ou déjà prêt) "
            "pour l’examen officiel."
        )
    elif global_pct >= 70:
        tone = "good"
        global_message = (
            "💪 Bon niveau global. Quelques ajustements ciblés "
            "te feront passer au niveau supérieur."
        )
    elif global_pct >= 50:
        tone = "warning"
        global_message = (
            "🧱 Niveau intermédiaire. Les bases sont là, "
            "mais un travail structuré est nécessaire."
        )
    else:
        tone = "danger"
        global_message = (
            "⚠️ Niveau fragile. Pas d’inquiétude : "
            "un parcours progressif va t’aider à remonter."
        )

    # 📊 FEEDBACK PAR COMPÉTENCE
    skill_feedback = []
    weak_skills = []

    for skill, data in per_section.items():
        pct = data.get("pct", 0)

        if pct >= 80:
            status = "good"
            message = "Très solide"
        elif pct >= 60:
            status = "mid"
            message = "Correct mais améliorable"
        else:
            status = "low"
            message = "Priorité de travail"

        if pct < 60:
            weak_skills.append(skill)

        skill_feedback.append({
            "skill": skill,
            "pct": pct,
            "status": status,
            "message": message,
        })

    # 🎯 RECOMMANDATION STRATÉGIQUE
    if weak_skills:
        recommendation = (
            "👉 Priorité : retravailler "
            + ", ".join(weak_skills)
            + " avec les leçons guidées."
        )
    else:
        recommendation = (
            "👏 Très bon équilibre. "
            "Continue avec des examens blancs complets."
        )

    return {
        "tone": tone,
        "global_message": global_message,
        "skill_feedback": skill_feedback,
        "recommendation": recommendation,
        "unlocked": unlocked_info or {"unlocked": False},
    }
