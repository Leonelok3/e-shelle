"""
Vues d'authentification EduCam Pro.
"""
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator

from edu_platform.forms.auth_forms import EduRegisterForm, EduLoginForm, ActivateCodeForm
from edu_platform.models import EduProfile, AccessCode
from edu_platform.services.device_service import bind_device, DeviceConflictException

logger = logging.getLogger('edu_platform')
User = get_user_model()


class EduLandingView(View):
    """Page d'accueil de la plateforme EduCam Pro."""
    template_name = 'edu_platform/landing.html'

    def get(self, request):
        from edu_platform.models import Subject, SubscriptionPlan
        context = {
            'plans': SubscriptionPlan.objects.filter(is_active=True),
            'subjects_count': Subject.objects.filter(is_published=True).count(),
            'levels': ['BEPC', 'Probatoire', 'Baccalauréat'],
        }
        return render(request, self.template_name, context)


class EduRegisterView(View):
    """Inscription à EduCam Pro."""
    template_name = 'edu_platform/auth/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('edu:dashboard')
        return render(request, self.template_name, {'form': EduRegisterForm()})

    def post(self, request):
        form = EduRegisterForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Utiliser l'email comme username
            username = cd['email'].split('@')[0].lower()
            # Unicité du username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=cd['email'],
                password=cd['password1'],
                first_name=cd['first_name'],
                last_name=cd['last_name'],
            )
            EduProfile.objects.create(
                user=user,
                phone_number=cd['phone_number'],
            )
            login(request, user)
            messages.success(request, f"Bienvenue {user.first_name} ! Choisissez votre forfait pour commencer.")
            logger.info('Nouvel utilisateur EduCam: %s', user.username)
            return redirect('edu:plans')

        return render(request, self.template_name, {'form': form})


class EduLoginView(View):
    """Connexion à EduCam Pro."""
    template_name = 'edu_platform/auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('edu:dashboard')
        next_url = request.GET.get('next', '')
        return render(request, self.template_name, {
            'form': EduLoginForm(),
            'next': next_url,
        })

    def post(self, request):
        # EduLoginForm hérite de AuthenticationForm qui prend request
        form = EduLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if next_url and next_url.startswith('/edu/'):
                return redirect(next_url)
            return redirect('edu:dashboard')

        return render(request, self.template_name, {'form': form})


class EduLogoutView(View):
    """Déconnexion."""
    def post(self, request):
        logout(request)
        messages.info(request, "Vous avez été déconnecté.")
        return redirect('edu:landing')

    def get(self, request):
        # Support GET pour le bouton de déconnexion simple
        logout(request)
        return redirect('edu:landing')


class ActivateCodeView(View):
    """Saisie et activation du code d'accès."""
    template_name = 'edu_platform/auth/activate_code.html'

    @method_decorator(login_required(login_url='/edu/login/'))
    def get(self, request):
        return render(request, self.template_name, {'form': ActivateCodeForm()})

    @method_decorator(login_required(login_url='/edu/login/'))
    def post(self, request):
        form = ActivateCodeForm(request.POST)
        if form.is_valid():
            code_str = form.cleaned_data['code']

            try:
                access_code = AccessCode.objects.select_related('plan').get(code=code_str)
            except AccessCode.DoesNotExist:
                messages.error(request, "Code invalide. Vérifiez votre code et réessayez.")
                return render(request, self.template_name, {'form': form})

            if access_code.status == 'revoked':
                messages.error(request, "Ce code a été révoqué. Contactez le support.")
                return render(request, self.template_name, {'form': form})

            if access_code.is_expired:
                messages.error(request, "Ce code est expiré.")
                return render(request, self.template_name, {'form': form})

            if access_code.activation_count >= access_code.max_activations:
                # Vérifier si c'est bien cet utilisateur
                if access_code.activated_by == request.user:
                    messages.info(request, "Ce code est déjà activé sur votre compte.")
                    return redirect('edu:dashboard')
                messages.error(
                    request,
                    "Ce code est déjà utilisé sur un autre compte. "
                    "Contactez le support : support@e-shelle.com"
                )
                return render(request, self.template_name, {'form': form})

            # Lier l'appareil
            try:
                bind_device(request.user, access_code, request)
                messages.success(
                    request,
                    f"Accès activé ! Bienvenue sur EduCam Pro — {access_code.plan.name}."
                )
                logger.info('Code %s activé par user %s', code_str, request.user.username)
                return redirect('edu:dashboard')
            except DeviceConflictException as e:
                messages.error(request, str(e))
                return render(request, self.template_name, {'form': form})

        return render(request, self.template_name, {'form': form})


class DeviceBlockedView(View):
    """Page d'erreur quand l'appareil n'est pas autorisé."""
    template_name = 'edu_platform/auth/device_blocked.html'

    def get(self, request):
        return render(request, self.template_name)
