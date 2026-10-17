from functools import wraps

from django.http import Http404


def staff_only_noindex(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not (user.is_staff or user.is_superuser):
            raise Http404

        response = view_func(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    return wrapped
