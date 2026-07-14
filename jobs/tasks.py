import logging
from celery import shared_task
from django.core.management import call_command

log = logging.getLogger(__name__)

@shared_task
def fetch_canada_jobs_task():
    """
    Tâche Celery quotidienne pour récupérer les offres d'emploi d'employeurs canadiens
    qui recrutent à l'étranger (EIMT/LMIA).
    """
    log.info("fetch_canada_jobs_task: Démarrage de l'importation des offres Canada...")
    try:
        call_command("fetch_canada_jobs")
        log.info("fetch_canada_jobs_task: Importation réussie.")
    except Exception as e:
        log.error(f"fetch_canada_jobs_task: Erreur lors de l'exécution : {e}")


@shared_task
def fetch_canada_scholarships_task():
    """
    Tâche Celery quotidienne pour récupérer les bourses d'études au Canada
    destinées aux étudiants internationaux.
    """
    log.info("fetch_canada_scholarships_task: Démarrage de la recherche de bourses...")
    try:
        call_command("fetch_canada_scholarships")
        log.info("fetch_canada_scholarships_task: Recherche terminée avec succès.")
    except Exception as e:
        log.error(f"fetch_canada_scholarships_task: Erreur lors de la recherche : {e}")

