from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from business.models import AppPromotionSlide, BusinessProfile, HomeAdSlide, PartnerLogo, PresentationSlide


def normalize_url(value):
    if not value:
        return value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    public_paths = getattr(settings, "ESHELLE_SUBDOMAIN_PUBLIC_PATHS", {})
    if host not in public_paths:
        return value
    public_path = public_paths[host]
    return parsed.path if parsed.path.startswith(public_path) else public_path


class Command(BaseCommand):
    help = "Convertit les anciens liens *.e-shelle.com en chemins du domaine principal."

    def handle(self, *args, **options):
        targets = [
            (AppPromotionSlide, "cta_url"),
            (PresentationSlide, "cta_url"),
            (HomeAdSlide, "cta_url"),
            (BusinessProfile, "promo_url"),
            (PartnerLogo, "website_url"),
        ]
        updated = 0
        for model, field in targets:
            for obj in model.objects.exclude(**{field: ""}).iterator():
                current = getattr(obj, field)
                normalized = normalize_url(current)
                if normalized != current:
                    setattr(obj, field, normalized)
                    obj.save(update_fields=[field])
                    updated += 1
                    self.stdout.write(f"{model.__name__}.{field} #{obj.pk}: {current} -> {normalized}")
        self.stdout.write(self.style.SUCCESS(f"{updated} URL(s) normalisee(s)."))
