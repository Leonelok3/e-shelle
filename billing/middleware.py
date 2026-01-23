# billing/middleware.py
from django.utils.deprecation import MiddlewareMixin

from .models import AffiliateProfile


class ReferralTrackingMiddleware(MiddlewareMixin):
    """
    Middleware qui capture un code parrain:
    - depuis ?ref=XXXX
    - ou ?ref_code=XXXX
    - puis le stocke dans un cookie "ref" (30 jours)
    """

    COOKIE_NAME = "ref"
    COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 jours

    def process_response(self, request, response):
        # Si cookie déjà présent, ne rien faire
        if request.COOKIES.get(self.COOKIE_NAME):
            return response

        ref_code = request.GET.get("ref") or request.GET.get("ref_code")
        if not ref_code:
            return response

        ref_code = str(ref_code).strip()
        if not ref_code:
            return response

        # Vérifier que le code existe vraiment (évite spam / fake)
        if not AffiliateProfile.objects.filter(ref_code=ref_code).exists():
            return response

        # Stocker en cookie
        response.set_cookie(
            self.COOKIE_NAME,
            ref_code,
            max_age=self.COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=False if getattr(request, "is_secure", lambda: False)() is False else True,
        )
        return response
