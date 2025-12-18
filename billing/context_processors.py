# billing/context_processors.py

from billing.services import has_active_access, has_session_access
from billing.models import Subscription
from django.utils import timezone


def premium_status(request):
    """
    Rend disponible dans TOUS les templates :
    - has_premium
    - has_temp_access
    - subscription
    """

    has_premium = False
    has_temp_access = False
    subscription = None

    if request.user.is_authenticated:
        now = timezone.now()

        subscription = (
            Subscription.objects
            .filter(
                user=request.user,
                is_active=True,
                expires_at__gt=now
            )
            .order_by("-expires_at")
            .first()
        )

        has_premium = subscription is not None
        has_temp_access = has_session_access(request)

    return {
        "has_premium": has_premium,
        "has_temp_access": has_temp_access,
        "subscription": subscription,
    }
