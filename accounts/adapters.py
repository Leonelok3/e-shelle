"""
accounts/adapters.py
Adaptateurs allauth pour E-Shelle.
- AccountAdapter    : redirect post-login vers home
- SocialAccountAdapter : crée UserProfile + attribue rôle CLIENT pour chaque
                         inscription via Google ou Facebook
"""
import logging
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """Adaptateur pour les comptes classiques (email/password)."""

    def get_login_redirect_url(self, request):
        return "/"

    def get_logout_redirect_url(self, request):
        return "/accounts/login/"


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptateur pour les connexions sociales (Google, Facebook)."""

    def get_app(self, request, provider, client_id=None):
        # A separate Google project lets Immigration97 own its consent branding.
        # Never replace the shared E-Shelle credentials globally.
        from django.conf import settings
        dedicated_id = getattr(settings, "IMMIGRATION97_GOOGLE_CLIENT_ID", "")
        dedicated_secret = getattr(settings, "IMMIGRATION97_GOOGLE_CLIENT_SECRET", "")
        if (getattr(request, "is_immigration97", False) and provider == "google"
                and dedicated_id and dedicated_secret):
            from allauth.socialaccount.models import SocialApp
            if client_id and client_id != dedicated_id:
                raise SocialApp.DoesNotExist()
            return SocialApp(provider="google", name="Immigration97",
                             client_id=dedicated_id, secret=dedicated_secret)
        return super().get_app(request, provider, client_id=client_id)

    def is_open_for_signup(self, request, sociallogin):
        """Toujours autoriser les nouvelles inscriptions via social."""
        return True

    def save_user(self, request, sociallogin, form=None):
        """
        Appelé lors de la PREMIÈRE connexion sociale.
        Crée le CustomUser + UserProfile + attribue le rôle CLIENT.
        """
        from accounts.models import UserProfile

        user = super().save_user(request, sociallogin, form)

        # Rôle par défaut pour les inscrits via social
        try:
            from accounts.models import Role
            if not getattr(user, "role", None):
                user.role = Role.CLIENT
                user.save(update_fields=["role"])
        except Exception as e:
            logger.warning(f"SocialAccountAdapter.save_user role error: {e}")

        # Créer le profil si absent
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                # Pré-remplir la ville si dispo dans les données sociales
                extra = sociallogin.account.extra_data or {}
                locale = extra.get("locale", "")
                if "CM" in locale.upper() or not locale:
                    profile.pays = "CM"
                    profile.save(update_fields=["pays"])
                logger.info(f"UserProfile créé pour {user.email} (social: {sociallogin.account.provider})")
        except Exception as e:
            logger.error(f"SocialAccountAdapter.save_user profile error: {e}")

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return "/"

    def populate_user(self, request, sociallogin, data):
        """
        Enrichit le user avec les données Google/Facebook.
        Garantit un username unique si absent.
        """
        user = super().populate_user(request, sociallogin, data)

        # Générer un username propre si allauth en met un vide
        if not user.username:
            base = (data.get("email") or "user").split("@")[0]
            base = "".join(c for c in base if c.isalnum() or c in "_-")[:30] or "user"
            from accounts.models import CustomUser
            import uuid
            username = base
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base}_{uuid.uuid4().hex[:5]}"
            user.username = username

        return user
