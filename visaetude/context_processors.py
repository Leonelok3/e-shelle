from .models import UserProgress

TOTAL_STEPS = 5


def visa_progress(request):
    """
    Ajoute la progression Visa Études dans le contexte global des templates.
    - Si l'utilisateur n'est pas connecté : progression = 0%.
    - Si l'utilisateur est connecté : on récupère/crée UserProgress.
    """
    if not request.user.is_authenticated:
        return {
            "visa_progress": None,
            "visa_progress_percent": 0,
            "visa_progress_label": "Étape 1/5",
        }

    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    completed = progress.completed_steps

    # Pour ne pas afficher 0/5, on met au moins étape 1.
    current_stage = completed if completed > 0 else 1
    percent = int(completed * 100 / TOTAL_STEPS) if TOTAL_STEPS else 0
    label = f"Étape {current_stage}/{TOTAL_STEPS}"

    return {
        "visa_progress": progress,
        "visa_progress_percent": percent,
        "visa_progress_label": label,
    }
