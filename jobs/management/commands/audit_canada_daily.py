"""Read-only production evidence, without exposing credentials."""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone
from jobs.models import CanadaJobOffer, CanadaScholarship, CanadaVisitorOpportunity, CanadaNews


class Command(BaseCommand):
    help = "Diagnostic en lecture seule des quatre générations quotidiennes Canada."

    def handle(self, *args, **options):
        self.stdout.write(f"Heure du diagnostic: {timezone.now().isoformat()}")
        self.stdout.write(f"Fuseau Celery: {getattr(settings, 'CELERY_TIMEZONE', settings.TIME_ZONE)}")
        cutoff = timezone.now() - timezone.timedelta(hours=36)
        for model in (CanadaJobOffer, CanadaScholarship, CanadaVisitorOpportunity, CanadaNews):
            qs = model.objects.all()
            latest = qs.aggregate(latest=Max('last_seen'))['latest']
            self.stdout.write(
                f"{model.__name__}: total={qs.count()}, actives={qs.filter(is_active=True).count()}, "
                f"revues_36h={qs.filter(last_seen__gte=cutoff).count()}, derniere_maj={latest}"
            )
        from django_celery_beat.models import PeriodicTask
        tasks = PeriodicTask.objects.filter(task__startswith="jobs.tasks.fetch_canada_")
        for task in tasks:
            self.stdout.write(
                f"Planification {task.name}: active={task.enabled}, horaire={task.schedule}, "
                f"dernier_declenchement={task.last_run_at}, declenchements={task.total_run_count}"
            )
        if not tasks.exists():
            self.stdout.write("ATTENTION: aucune tâche Canada enregistrée dans django-celery-beat.")
        self.stdout.write("Une mise à jour récente ou un déclenchement ne prouve pas à lui seul le succès complet: consulter les journaux Celery.")
