from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .forms import LoginForm
from .models import (
    Role, CustomUser, UserProfile, EmailVerification,
    AppPlan, AppSubscription, PaymentHistory, GlobalAccessCode,
    AppKey, APP_ICONS, APP_COLORS,
)


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class AppLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    """Redirige l'utilisateur vers son dashboard selon son rôle."""
    return redirect("dashboard:index")


def _envoyer_code_verification(user, code):
    """Envoie l'email de vérification avec le code à 6 chiffres."""
    sujet = f"[E-Shelle] Votre code de vérification : {code}"
    corps_txt = (
        f"Bonjour {user.first_name or user.username},\n\n"
        f"Votre code de vérification E-Shelle est :\n\n"
        f"  {code}\n\n"
        f"Ce code est valable 15 minutes.\n"
        f"Si vous n'avez pas créé de compte, ignorez cet email.\n\n"
        f"— L'équipe E-Shelle"
    )
    corps_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:2rem;
                background:#0d0d0d;color:#fff;border-radius:12px;">
      <div style="text-align:center;margin-bottom:2rem;">
        <span style="font-size:2rem;font-weight:900;letter-spacing:-1px;">
          <span style="color:#4CAF50">E</span>
          <span style="color:#F5C518">-Shelle</span>
        </span>
      </div>
      <h2 style="text-align:center;font-size:1.2rem;margin-bottom:.5rem;">
        Vérifiez votre adresse email
      </h2>
      <p style="color:#aaa;text-align:center;font-size:.9rem;margin-bottom:2rem;">
        Bonjour <strong style="color:#fff">{user.first_name or user.username}</strong>,<br>
        entrez ce code dans l'application pour activer votre compte :
      </p>
      <div style="background:#1a1a1a;border:2px solid #4CAF50;border-radius:12px;
                  padding:2rem;text-align:center;margin-bottom:2rem;">
        <span style="font-size:2.5rem;font-weight:900;letter-spacing:.5rem;
                     font-family:monospace;color:#4CAF50">{code}</span>
        <p style="color:#888;font-size:.8rem;margin:.75rem 0 0;">Valable 15 minutes</p>
      </div>
      <p style="color:#666;font-size:.78rem;text-align:center;">
        Si vous n'avez pas créé de compte sur E-Shelle, ignorez cet email.
      </p>
    </div>
    """
    import traceback
    try:
        send_mail(
            subject=sujet,
            message=corps_txt,
            html_message=corps_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        with open('/var/www/eshelle/email_debug.log', 'a') as f:
            f.write(f"OK: {user.email} | BACKEND={settings.EMAIL_BACKEND} | USER={settings.EMAIL_HOST_USER}\n")
    except Exception as e:
        with open('/var/www/eshelle/email_debug.log', 'a') as f:
            f.write(f"ERROR: {user.email} | {e}\n{traceback.format_exc()}\n")


def register(request):
    """Inscription — crée le compte inactif et envoie un code de vérification."""
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        username   = request.POST.get("username", "").strip()
        email      = request.POST.get("email", "").strip()
        password1  = request.POST.get("password1", "")
        password2  = request.POST.get("password2", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name  = request.POST.get("last_name", "").strip()
        role       = request.POST.get("role", Role.STUDENT)

        # Validations
        if not username or not email or not password1:
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
        elif password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
        elif len(password1) < 8:
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
        elif CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
        else:
            # Créer le compte ACTIF directement
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                role=role if role in dict(Role.choices) else Role.STUDENT,
                is_active=True,
            )
            UserProfile.objects.get_or_create(user=user)
            try:
                from billing.views_affiliate import bind_referral_if_any
                bind_referral_if_any(request, user)
            except Exception:
                pass
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Bienvenue {user.first_name or user.username} ! Votre compte a été créé.")
            selected_plan = request.GET.get("plan") or request.POST.get("plan")
            if selected_plan:
                request.session["business_selected_plan"] = selected_plan
                return redirect(f"/business/onboarding/?plan={selected_plan}")
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("dashboard:index")

    plan = request.GET.get("plan", "free")
    return render(request, "accounts/register.html", {"plan": plan, "roles": Role.choices})


def verify_email(request):
    """Page de saisie du code de vérification."""
    user_id = request.session.get("verif_user_id")
    if not user_id:
        return redirect("accounts:register")

    user = get_object_or_404(CustomUser, pk=user_id, is_active=False)

    if request.method == "POST":
        code_saisi = "".join([
            request.POST.get(f"d{i}", "") for i in range(1, 7)
        ]).strip()

        try:
            verif = EmailVerification.objects.get(user=user)
        except EmailVerification.DoesNotExist:
            messages.error(request, "Aucun code trouvé. Veuillez vous réinscrire.")
            return redirect("accounts:register")

        if verif.is_verified:
            messages.info(request, "Compte déjà vérifié. Connectez-vous.")
            return redirect("accounts:login")

        if verif.est_expire:
            messages.error(request, "⏰ Code expiré. Cliquez sur « Renvoyer le code ».")
        elif verif.tentatives >= 5:
            messages.error(request, "Trop de tentatives. Cliquez sur « Renvoyer le code ».")
        elif code_saisi != verif.code:
            verif.tentatives += 1
            verif.save(update_fields=["tentatives"])
            restantes = 5 - verif.tentatives
            messages.error(request, f"❌ Code incorrect. {restantes} tentative(s) restante(s).")
        else:
            # ✅ Code correct — activer le compte
            verif.is_verified = True
            verif.save(update_fields=["is_verified"])
            user.is_active = True
            user.save(update_fields=["is_active"])

            del request.session["verif_user_id"]
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"🎉 Bienvenue {user.first_name or user.username} ! Votre compte est activé.")
            return redirect("dashboard:index")

    # Masquer une partie de l'email pour affichage
    em = user.email
    parts = em.split("@")
    email_masque = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else em

    return render(request, "accounts/verify_email.html", {
        "user": user,
        "email_masque": email_masque,
    })


def resend_code(request):
    """Renvoyer un nouveau code de vérification."""
    user_id = request.session.get("verif_user_id")
    if not user_id:
        return redirect("accounts:register")

    user = get_object_or_404(CustomUser, pk=user_id, is_active=False)
    verif = EmailVerification.generer(user)
    _envoyer_code_verification(user, verif.code)
    messages.success(request, f"✅ Nouveau code envoyé à {user.email}. Vérifiez votre boîte mail.")
    return redirect("accounts:verify_email")


@login_required
def profil(request):
    """Page de profil utilisateur."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name  = request.POST.get("last_name",  user.last_name)
        user.email      = request.POST.get("email",      user.email)
        user.save(update_fields=["first_name", "last_name", "email"])

        profile.bio       = request.POST.get("bio",       profile.bio)
        profile.telephone = request.POST.get("telephone", profile.telephone)
        profile.ville     = request.POST.get("ville",     profile.ville)
        profile.pays      = request.POST.get("pays",      profile.pays)
        profile.site_web  = request.POST.get("site_web",  profile.site_web)
        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]
        profile.save()

        messages.success(request, "Profil mis à jour avec succès.")
        return redirect("accounts:profil")

    return render(request, "accounts/profil.html", {"profile": profile})


# ─────────────────────────────────────────────────────────────────
#  MON COMPTE — Dashboard unifié
# ─────────────────────────────────────────────────────────────────

@login_required
def mon_compte(request):
    """
    Dashboard unifié : profil, tous les abonnements actifs,
    historique des paiements, et liens vers chaque application.
    """
    user    = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # Tous les abonnements (actifs + expirés)
    all_subs = (
        AppSubscription.objects
        .filter(user=user)
        .select_related("plan")
        .order_by("-started_at")
    )

    # Abonnements actifs par app_key
    active_subs = {}
    for sub in all_subs:
        key = sub.plan.app_key
        if key not in active_subs and sub.is_active:
            active_subs[key] = sub

    # Historique paiements — total dépensé AVANT le slice
    payments_qs = PaymentHistory.objects.filter(user=user).select_related("subscription__plan")
    total_spent = sum(
        payments_qs.filter(status="success").values_list("amount_xaf", flat=True)
    )
    payments = payments_qs[:10]

    # Apps disponibles avec leur état
    apps_info = []
    for key, label in AppKey.choices:
        sub = active_subs.get(key)
        apps_info.append({
            "key":    key,
            "label":  label,
            "icon":   APP_ICONS.get(key, "📦"),
            "color":  APP_COLORS.get(key, "#6B7280"),
            "sub":    sub,
            "active": sub is not None,
        })

    # Stats rapides
    stats = {
        "total_subs":  len(active_subs),
        "paid_subs":   sum(1 for s in active_subs.values() if s.plan.price_xaf > 0),
        "total_spent": total_spent,
    }

    # Édition profil (POST)
    if request.method == "POST" and "save_profile" in request.POST:
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name  = request.POST.get("last_name",  user.last_name).strip()
        user.email      = request.POST.get("email",      user.email).strip()
        user.save(update_fields=["first_name", "last_name", "email"])

        profile.bio       = request.POST.get("bio",       profile.bio)
        profile.telephone = request.POST.get("telephone", profile.telephone)
        profile.ville     = request.POST.get("ville",     profile.ville)
        profile.pays      = request.POST.get("pays",      profile.pays)
        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]
        profile.save()

        messages.success(request, "Profil mis à jour.")
        return redirect("accounts:mon_compte")

    context = {
        "profile":     profile,
        "active_subs": active_subs,
        "all_subs":    all_subs[:20],
        "payments":    payments,
        "apps_info":   apps_info,
        "stats":       stats,
    }
    return render(request, "accounts/mon_compte.html", context)


# ─────────────────────────────────────────────────────────────────
#  UPGRADE — Page des plans pour une application
# ─────────────────────────────────────────────────────────────────

@login_required
def upgrade(request):
    """
    Affiche les plans disponibles pour une app donnée (?app=adgen).
    Si aucun app_key fourni, affiche toutes les apps.
    """
    app_key = request.GET.get("app", "").strip()

    # Filtrer les plans
    plans_qs = AppPlan.objects.filter(is_active=True).order_by("app_key", "order")
    if app_key and app_key in dict(AppKey.choices):
        plans_qs = plans_qs.filter(app_key=app_key)
        app_label = dict(AppKey.choices).get(app_key, app_key)
        app_icon  = APP_ICONS.get(app_key, "📦")
        app_color = APP_COLORS.get(app_key, "#6B7280")
    else:
        app_key   = None
        app_label = "Toutes les applications"
        app_icon  = "🚀"
        app_color = "#6C3FE8"

    # Plan actuel de l'utilisateur pour cette app
    current_sub = None
    if app_key and request.user.is_authenticated:
        current_sub = AppSubscription.get_active_for_user(request.user, app_key)

    # Grouper les plans par app si vue globale
    plans_by_app = {}
    for plan in plans_qs:
        k = plan.app_key
        if k not in plans_by_app:
            plans_by_app[k] = {
                "label": plan.get_app_key_display(),
                "icon":  plan.app_icon,
                "color": plan.app_color,
                "plans": [],
            }
        plans_by_app[k]["plans"].append(plan)

    context = {
        "app_key":     app_key,
        "app_label":   app_label,
        "app_icon":    app_icon,
        "app_color":   app_color,
        "plans":       list(plans_qs),
        "plans_by_app": plans_by_app,
        "current_sub": current_sub,
    }
    return render(request, "accounts/upgrade.html", context)


# ─────────────────────────────────────────────────────────────────
#  ANNULATION D'ABONNEMENT
# ─────────────────────────────────────────────────────────────────

@login_required
def cancel_subscription(request, pk):
    """Annule un abonnement appartenant à l'utilisateur connecté."""
    sub = get_object_or_404(AppSubscription, pk=pk, user=request.user)

    if request.method == "POST":
        if sub.is_active:
            sub.status = "cancelled"
            sub.auto_renew = False
            sub.save(update_fields=["status", "auto_renew"])
            messages.success(
                request,
                f"Votre abonnement {sub.plan.name} a été annulé. "
                f"Vous conservez l'accès jusqu'au {sub.expires_at.strftime('%d/%m/%Y') if sub.expires_at else 'terme'}."
            )
        else:
            messages.warning(request, "Cet abonnement n'est pas actif.")

    return redirect("accounts:mon_compte")


# ─────────────────────────────────────────────────────────────────
#  ACTIVATION CODE D'ACCÈS
# ─────────────────────────────────────────────────────────────────

@login_required
def activer_code(request):
    """
    Page d'activation d'un code d'accès reçu de l'admin E-Shelle.
    Le client saisit son code → ses abonnements sont créés automatiquement.
    """
    activated = None

    if request.method == "POST":
        raw = request.POST.get("code", "").strip().upper().replace(" ", "-")

        try:
            code_obj = GlobalAccessCode.objects.get(code=raw)
        except GlobalAccessCode.DoesNotExist:
            messages.error(request, "Code invalide. Vérifiez et réessayez.")
            return render(request, "accounts/activer_code.html", {"code_input": raw})

        ok, msg = code_obj.activate(request.user)
        if ok:
            messages.success(request, f"Code activé avec succès ! {msg}")
            activated = code_obj
        else:
            messages.error(request, msg)

    return render(request, "accounts/activer_code.html", {"activated": activated})
