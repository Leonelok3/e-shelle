try:
    from edu_cm.celery import app
except Exception:
    app = None


def shared_task(*args, **kwargs):
    if app:
        return app.task(*args, **kwargs)
    from celery import shared_task as celery_shared_task

    return celery_shared_task(*args, **kwargs)

