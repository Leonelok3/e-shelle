from django.core.management.base import BaseCommand
from radar.models import Source

DEFAULT = [
    {"code":"IRCC","name":"IRCC (Canada) – programmes & actus","url":"https://www.canada.ca/"},
    {"code":"CAMPUSFR","name":"Campus France – bourses","url":"https://www.campusfrance.org/"},
    {"code":"DAAD","name":"DAAD – scholarships","url":"https://www.daad.de/en/"},
    {"code":"UKVI","name":"UKVI – sponsors list","url":"https://www.gov.uk/"},
    {"code":"US_EDU","name":"EducationUSA","url":"https://educationusa.state.gov/"},
]

class Command(BaseCommand):
    help = "Crée les sources par défaut pour le radar"

    def handle(self, *args, **kwargs):
        for s in DEFAULT:
            obj, _ = Source.objects.get_or_create(code=s["code"], defaults=s)
            self.stdout.write(self.style.SUCCESS(f"OK: {obj.code}"))
