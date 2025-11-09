from rest_framework.permissions import BasePermission, SAFE_METHODS

def user_is_subscriber(user):
    # TODO: branchement réel sur app billing
    return user.is_authenticated

class IsSubscriberOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return user_is_subscriber(request.user)
