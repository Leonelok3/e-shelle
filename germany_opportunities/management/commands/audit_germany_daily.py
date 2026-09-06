from django.core.management.base import BaseCommand
from django.db.models import Q, Max
from django.utils import timezone


class Command(BaseCommand):
    help = "Diagnostic allemand en lecture seule: offres, bourses et générations pédagogiques."

    def handle(self, *args, **options):
        from germany_opportunities.models import AusbildungOffer, ScholarshipOpportunity
        from germany_opportunities.availability import available_offers, available_scholarships
        from GermanPrepApp.models import GermanExam, GermanLesson, GermanPlacementQuestion, GermanPastExam
        from django_celery_beat.models import PeriodicTask
        self.stdout.write(f"Diagnostic: {timezone.now().isoformat()}")
        self.stdout.write(f"Offres: {AusbildungOffer.objects.count()} conservées, {available_offers().count()} visibles, dernière collecte={AusbildungOffer.objects.aggregate(last=Max('last_seen'))['last']}")
        self.stdout.write(f"Bourses: {ScholarshipOpportunity.objects.count()} conservées, {available_scholarships().count()} visibles")
        self.stdout.write("Bourses: aucun importeur DAAD implémenté; les échéances connues sont contrôlées.")
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            self.stdout.write(f"{level}: examens={GermanExam.objects.filter(level=level, is_active=True).count()}, leçons={GermanLesson.objects.filter(exam__level=level).count()}, examens blancs={GermanPastExam.objects.filter(exam__level=level, is_active=True).count()}")
        self.stdout.write(f"Questions de niveau actives={GermanPlacementQuestion.objects.filter(is_active=True).count()}, audios HOREN manquants={GermanLesson.objects.filter(skill='HOREN', audio_url='').count()}")
        for task in PeriodicTask.objects.filter(Q(task__startswith="germany_opportunities.") | Q(task__startswith="GermanPrepApp.")):
            self.stdout.write(f"{task.name}: active={task.enabled}, horaire={task.schedule}, dernier lancement={task.last_run_at}")
