"""Shared visibility rules; preserve saved applications and historical rows."""
from django.db.models import Q
from django.utils import timezone
from .models import AusbildungOffer, ScholarshipOpportunity


def available_offers():
    return AusbildungOffer.objects.filter(is_active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__gte=timezone.localdate())
    ).filter(last_seen__gte=timezone.now() - timezone.timedelta(days=7))


def available_scholarships():
    # Undated scholarship cycles cannot be established as open.
    return ScholarshipOpportunity.objects.filter(is_active=True, deadline__gte=timezone.localdate())


def clean_unavailable(dry_run=False):
    offers = AusbildungOffer.objects.filter(is_active=True).filter(
        Q(start_date__lt=timezone.localdate()) |
        Q(last_seen__lt=timezone.now() - timezone.timedelta(days=7))
    )
    scholarships = ScholarshipOpportunity.objects.filter(is_active=True).filter(
        Q(deadline__lt=timezone.localdate()) | Q(deadline__isnull=True)
    )
    result = {"offers_hidden": offers.count(), "scholarships_hidden": scholarships.count()}
    if not dry_run:
        offers.update(is_active=False)
        scholarships.update(is_active=False)
    return result
