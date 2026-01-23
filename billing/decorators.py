# billing/decorators.py
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


def subscription_required(view_func=None, *, allow_session_access=True):
    """
    Protéger une view :
    - si utilisateur non connecté -> redirect login avec next
    - si connecté mais pas d'abonnement actif -> redirect billing:access avec next
    - option: allow_session_access=True => autorise aussi l'accès temporaire (session)
    """

    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            # import ici pour éviter les import circulaires
            from billing.services import has_active_access, has_session_access

            # 1) pas connecté -> login
            if not request.user.is_authenticated:
                # adapte si ton login s'appelle différemment
                login_url = reverse("authentification:login")
                return redirect(f"{login_url}?next={request.get_full_path()}")

            # 2) accès OK (abonnement) ou (session si autorisée)
            if has_active_access(request.user):
                return func(request, *args, **kwargs)

            if allow_session_access and has_session_access(request):
                return func(request, *args, **kwargs)

            # 3) sinon -> page billing/access
            messages.error(request, "🔒 Accès réservé aux abonnés. Active un pass pour continuer.")
            access_url = reverse("billing:access")
            return redirect(f"{access_url}?next={request.get_full_path()}")

        return _wrapped

    if view_func is None:
        return decorator
    return decorator(view_func)
