from .services import has_active_access, has_session_access

def premium_status(request):
    if request.user.is_authenticated:
        return {
            "has_premium": has_active_access(request.user),
            "has_temp_access": has_session_access(request),
        }
    return {
        "has_premium": False,
        "has_temp_access": False,
    }
