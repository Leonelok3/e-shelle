from django.db import IntegrityError
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse, resolve # <-- CORRECTION APPLIQUÉE ICI
from django.views.decorators.http import require_POST

# ============================================================
# Utilitaires
# ============================================================

def _safe_next_url(request, fallback_name="cv_generator:cv_list"):
    """
    Retourne l'URL de redirection post-login:
      1) ?next= si présent et résolvable
      2) sinon le fallback (tableau de bord CV)
    Sécurisé pour éviter les redirections externes.
    """
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt:
        try:
            # Safety: on n'autorise que des urls internes Django résolvables
            resolve(nxt)
            return nxt
        except Exception:
            pass
    return reverse(fallback_name)

def send_activation_email(request, user):
    """
    Envoi de l'email d’activation de compte.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activate_url = request.build_absolute_uri(
        reverse('authentification:activate_account', kwargs={'uidb64': uid, 'token': token})
    )

    subject = "Confirmez votre adresse email"
    message = render_to_string('account/email/email_confirmation_message.html', {
        'user': user,
        'activate_url': activate_url,
    })

    email = EmailMessage(subject, message, to=[user.email])
    email.content_subtype = "html"
    email.send()

# ============================================================
# Vues
# ============================================================

def register(request):
    """
    Inscription + envoi de mail d’activation.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, '❌ Les mots de passe ne correspondent pas.')
            return render(request, 'authentification/register.html', {'prefill': {'username': username, 'email': email}})

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Ce nom d’utilisateur est déjà utilisé.')
            return render(request, 'authentification/register.html', {'prefill': {'username': username, 'email': email}})

        if User.objects.filter(email=email).exists():
            messages.error(request, '❌ Cet email est déjà utilisé.')
            return render(request, 'authentification/register.html', {'prefill': {'username': username, 'email': email}})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = False
            user.save()

            send_activation_email(request, user)
            messages.success(request, '📩 Un email de confirmation vous a été envoyé.')
            return redirect('authentification:email_sent')

        except IntegrityError:
            messages.error(request, '❌ Ce nom d’utilisateur ou cet email existe déjà.')
            return render(request, 'authentification/register.html', {'prefill': {'username': username, 'email': email}})

    return render(request, 'authentification/register.html')


def activate_account(request, uidb64, token):
    """
    Activation via lien email.
    """
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, '✅ Votre compte a été activé avec succès ! Vous pouvez maintenant vous connecter.')
        return redirect('authentification:login')
    return HttpResponse('❌ Lien invalide ou expiré.')


def home(request):
    """
    Page d’accueil du module d’authentification.
    """
    return render(request, 'authentification/index.html')


def login(request):
    """
    Connexion:
      - Respecte ?next=
      - Sinon redirige vers le tableau de bord CV
      - Messages clairs en cas d’erreur
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                auth_login(request, user)
                messages.success(request, f'Bienvenue {user.username} 👋')
                return redirect(_safe_next_url(request))
            else:
                messages.warning(request, '⚠️ Votre compte n’est pas encore activé. Vérifiez votre email.')
                # On repasse le next pour ne pas le perdre
                return render(request, 'authentification/login.html', {'username': username, 'next': request.POST.get('next')})
        else:
            messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect.')
            return render(request, 'authentification/login.html', {'username': username, 'next': request.POST.get('next')})

    # GET
    return render(request, 'authentification/login.html', {'next': request.GET.get('next')})


def logout(request):
    """
    Déconnexion puis retour à l’accueil du site.
    """
    auth_logout(request)
    messages.success(request, 'Déconnexion réussie 👋')
    return redirect('home')


def email_sent(request):
    """
    Page de confirmation après envoi de l’email d’activation.
    """
    return render(request, 'authentification/email_sent.html')


@require_POST
def resend_activation_email(request):
    """
    Renvoi de l'email d'activation si le compte n'est pas actif.
    """
    email = request.POST.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
        if not user.is_active:
            send_activation_email(request, user)
            messages.success(request, '📩 Un nouvel email de confirmation vous a été envoyé.')
        else:
            messages.info(request, '✅ Ce compte est déjà activé.')
    except User.DoesNotExist:
        messages.error(request, '❌ Aucun compte associé à cet email.')
    return redirect('authentification:login')