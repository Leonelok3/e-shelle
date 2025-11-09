from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSubscriberOrReadOnly(BasePermission):
    """
    Autorise lecture à tous mais écriture/score aux abonnés.
    Intègre ton endpoint 'check-entitlement' : request.user.profile.is_subscriber par ex.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_subscriber", True))
