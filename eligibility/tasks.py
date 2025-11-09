from celery import shared_task

@shared_task
def refresh_programs():
    # TODO: appeler des clients officiels / scrapers conformes
    return "ok"

@shared_task
def rebuild_embeddings():
    # TODO: reconstruire l'index vecteur pour RAG
    return "ok"
