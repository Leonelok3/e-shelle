from billing.models import Subscription

def user_has_premium(user):
    return Subscription.objects.filter(
        user=user,
        is_active=True
    ).exists()
