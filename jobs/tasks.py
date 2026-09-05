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
        log.exception(f"fetch_canada_jobs_task: Erreur lors de l'exécution : {e}")
        raise


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
        log.exception(f"fetch_canada_scholarships_task: Erreur lors de la recherche : {e}")
        raise


@shared_task
def fetch_canada_visitor_opps_task():
    """
    Tâche Celery quotidienne pour récupérer les opportunités facilitant l'obtention
    d'un visa de tourisme (visiteur) au Canada (conférences, séminaires, etc.).
    """
    log.info("fetch_canada_visitor_opps_task: Démarrage de la recherche d'opportunités visa visiteur...")
    try:
        call_command("fetch_canada_visitor_opps")
        log.info("fetch_canada_visitor_opps_task: Recherche terminée avec succès.")
    except Exception as e:
        log.exception(f"fetch_canada_visitor_opps_task: Erreur lors de la recherche : {e}")
        raise


@shared_task
def fetch_canada_news_task():
    """
    Tâche Celery quotidienne pour récupérer les actualités d'immigration Canada.
    """
    log.info("fetch_canada_news_task: Démarrage de la recherche d'actualités...")
    try:
        call_command("fetch_canada_news")
        log.info("fetch_canada_news_task: Recherche d'actualités terminée avec succès.")
    except Exception as e:
        log.exception(f"fetch_canada_news_task: Erreur lors de la recherche : {e}")
        raise



