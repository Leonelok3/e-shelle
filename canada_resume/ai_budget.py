"""Persisted daily limits prevent a new browser session from resetting usage."""
from functools import wraps
from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from .models import ImmigrationAIUsage


def ai_budget(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST' or not request.user.is_authenticated:
            return view(request, *args, **kwargs)
        limit = max(0, int(getattr(settings, 'IMMIGRATION97_DAILY_AI_LIMIT', 20)))
        row, _ = ImmigrationAIUsage.objects.get_or_create(user=request.user, day=timezone.localdate())
        if not ImmigrationAIUsage.objects.filter(pk=row.pk, attempts__lt=limit).update(attempts=F('attempts') + 1):
            message = 'Votre limite quotidienne de demandes IA est atteinte. Vos leçons, corrections enregistrées et brouillons restent accessibles. Revenez demain.'
            return JsonResponse({'ok': False, 'error': 'daily_ai_limit', 'reply': message,
                                 'message': message, 'messages_left': 0}, status=429)
        response = view(request, *args, **kwargs)
        # Invalid input did not require a provider; restore the reservation.
        if 400 <= response.status_code < 500:
            ImmigrationAIUsage.objects.filter(pk=row.pk, attempts__gt=0).update(attempts=F('attempts') - 1)
        return response
    return wrapped
