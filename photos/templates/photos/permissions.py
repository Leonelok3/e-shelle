# photos/permissions.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

from billing.services import has_access


def require_access_or_redirect(view_func):
    """
    Si l'utilisateur n'a pas d'accès (pass actif OU session accès),
    on le redirige vers billing:access avec un next= pour revenir après paiement/code.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if has_access(request):
            return view_func(request, *args, **kwargs)
        messages.info(request, "🔒 Accès requis pour télécharger en HD. Activez votre code ou achetez un accès.")
        dest = reverse("billing:access")
        return redirect(f"{dest}?next={request.get_full_path()}")
    return _wrapped
