"""
Configuration Celery pour E-Shelle.
Lance les workers avec: celery -A edu_cm worker -l info
Lance le scheduler avec: celery -A edu_cm beat -l info
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")

app = Celery("edu_cm")

# Charger la config depuis Django settings (clé CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodécouverte des tâches dans tous les apps installées
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# ── Facebook Agent IA — Beat Schedule ─────────────────────────────
app.conf.beat_schedule = {
    # Publications automatiques par section
    # Annonces : 9h, 14h, 20h
    "fb-annonces-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=9,  minute=0),
        "args": ("annonces",),
    },
    "fb-annonces-midi": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=14, minute=0),
        "args": ("annonces",),
    },
    "fb-annonces-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=20, minute=0),
        "args": ("annonces",),
    },

    # Immobilier : 10h30 (1x/jour)
    "fb-immobilier-quotidien": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=10, minute=30),
        "args": ("immobilier",),
    },

    # Auto : 11h (1x/jour)
    "fb-auto-quotidien": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=11, minute=0),
        "args": ("auto",),
    },

    # Agro : 7h30 (marchés du matin, 1x/jour)
    "fb-agro-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=7, minute=30),
        "args": ("agro",),
    },

    # Rencontres Love : 8h et 21h
    "fb-rencontres-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=8,  minute=0),
        "args": ("rencontres",),
    },
    "fb-rencontres-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=21, minute=0),
        "args": ("rencontres",),
    },

    # Njangi : 18h
    "fb-njangi-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=18, minute=0),
        "args": ("njangi",),
    },

    # Promo : lundi, mercredi, vendredi à 12h
    "fb-promo-semaine": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=12, minute=0, day_of_week="1,3,5"),
        "args": ("promo",),
    },

    # Général : 19h (tous les jours)
    "fb-general-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=19, minute=0),
        "args": ("general",),
    },

    # Croissance Douala — services à forte demande
    "fb-chat-ai-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=8, minute=30),
        "args": ("chat_ai",),
    },
    "fb-gaz-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=7, minute=0),
        "args": ("gaz",),
    },
    "fb-gaz-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=21, minute=0),
        "args": ("gaz",),
    },
    "fb-resto-midi": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=11, minute=30),
        "args": ("resto",),
    },
    "fb-pressing-matin": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=7, minute=45),
        "args": ("pressing",),
    },
    "fb-sante-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=19, minute=30),
        "args": ("sante",),
    },
    "fb-jobs-apres-midi": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=15, minute=0),
        "args": ("jobs",),
    },
    "fb-business-soir": {
        "task": "facebook_agent.tasks.generate_and_publish_post",
        "schedule": crontab(hour=18, minute=30),
        "args": ("business",),
    },

    # Maintenance — vérifier les posts planifiés toutes les 5 minutes
    "fb-process-scheduled": {
        "task": "facebook_agent.tasks.process_pending_scheduled_posts",
        "schedule": crontab(minute="*/5"),
    },

    # Sync statistiques Facebook toutes les 6h
    "fb-sync-stats": {
        "task": "facebook_agent.tasks.sync_post_stats",
        "schedule": crontab(hour="*/6", minute=0),
    },

    # Vérification du token chaque matin à 6h
    "fb-check-token": {
        "task": "facebook_agent.tasks.check_token_validity",
        "schedule": crontab(hour=6, minute=0),
    },

    # Stats journalières toutes les heures (à H+30)
    "fb-update-daily-stats": {
        "task": "facebook_agent.tasks.update_daily_stats",
        "schedule": crontab(minute=30),
    },

    # ── Njangi Digital — Tontine & Fond commun ──────────────────────────────

    # Calcul intérêts mensuels — 1er de chaque mois à 2h00
    "njangi-monthly-interests": {
        "task": "njangi.tasks.calculate_monthly_interests_all",
        "schedule": crontab(hour=2, minute=0, day_of_month=1),
    },

    # Application des pénalités de retard — chaque jour à 6h30
    "njangi-daily-penalties": {
        "task": "njangi.tasks.apply_penalties_all",
        "schedule": crontab(hour=6, minute=30),
    },

    # Vérification défauts de prêts — chaque jour à 7h30
    "njangi-check-defaults": {
        "task": "njangi.tasks.check_loan_defaults",
        "schedule": crontab(hour=7, minute=30),
    },

    # Mise à jour scores de fiabilité — chaque dimanche à 3h
    "njangi-reliability-scores": {
        "task": "njangi.tasks.update_reliability_scores",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
}
