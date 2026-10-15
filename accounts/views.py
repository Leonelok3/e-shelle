from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .forms import LoginForm
from .models import (
    Role, CustomUser, UserProfile, EmailVerification,
    AppPlan, AppSubscription, PaymentHistory, GlobalAccessCode,
    AppKey, APP_ICONS, APP_COLORS,
)
from core.whatsapp import payment_request_url
from core.branding import public_text, request_brand


APP_LABELS_EN = {
    "AdGen — Publicités IA": "AdGen — AI Ads", "E-Shelle Resto": "E-Shelle Restaurant",
    "E-Shelle Love": "E-Shelle Love", "Njangi Digital": "Njangi Digital",
    "EduCam Pro": "EduCam Pro", "E-Shelle Allemand (Ausbildung & Goethe)": "E-Shelle German (Vocational Training & Goethe)",
    "Préparation Français (TEF/TCF)": "French Preparation (TEF/TCF)", "Formations": "Courses",
    "Boutique": "Digital Store", "E-Shelle Agro": "E-Shelle Agriculture", "E-Shelle Gaz": "E-Shelle Gas",
    "Auto": "Automotive", "Auto-école": "Driving School", "Toutes les applications": "All applications",
}


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class AppLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    """Redirige l'utilisateur vers son dashboard selon son rôle."""
    return redirect("dashboard:index")


def _envoyer_code_verification(user, code, request=None):
    """Envoie l'email de vérification avec le code à 6 chiffres."""
    brand = request_brand(request)
    is_english = bool(request and request.LANGUAGE_CODE == "en")
    sujet = f"[{brand}] Your verification code: {code}" if is_english else f"[{brand}] Votre code de vérification : {code}"
    corps_txt = (
        f"Hello {user.first_name or user.username},\n\nYour {brand} verification code is:\n\n  {code}\n\nThis code is valid for 15 minutes.\nIf you did not create an account, ignore this email.\n\n— The {brand} team"
        if is_english else
        f"Bonjour {user.first_name or user.username},\n\n"
        f"Votre code de vérification {brand} est :\n\n"
        f"  {code}\n\n"
        f"Ce code est valable 15 minutes.\n"
        f"Si vous n'avez pas créé de compte, ignorez cet email.\n\n"
        f"— L'équipe {brand}"
    )
    corps_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:2rem;
                background:#0d0d0d;color:#fff;border-radius:12px;">
      <div style="text-align:center;margin-bottom:2rem;">
        <span style="font-size:2rem;font-weight:900;letter-spacing:-1px;">
          <span style="color:#4CAF50">{brand}</span>
        </span>
      </div>
      <h2 style="text-align:center;font-size:1.2rem;margin-bottom:.5rem;">
        {"Verify your email address" if is_english else "Vérifiez votre adresse email"}
      </h2>
      <p style="color:#aaa;text-align:center;font-size:.9rem;margin-bottom:2rem;">
        Bonjour <strong style="color:#fff">{user.first_name or user.username}</strong>,<br>
        {"enter this code in the app to activate your account:" if is_english else "entrez ce code dans l'application pour activer votre compte :"}
      </p>
      <div style="background:#1a1a1a;border:2px solid #4CAF50;border-radius:12px;
                  padding:2rem;text-align:center;margin-bottom:2rem;">
        <span style="font-size:2.5rem;font-weight:900;letter-spacing:.5rem;
                     font-family:monospace;color:#4CAF50">{code}</span>
        <p style="color:#888;font-size:.8rem;margin:.75rem 0 0;">{"Valid for 15 minutes" if is_english else "Valable 15 minutes"}</p>
      </div>
      <p style="color:#666;font-size:.78rem;text-align:center;">
        {'If you did not create an account on' if is_english else "Si vous n'avez pas créé de compte sur"} {brand}, {'ignore this email.' if is_english else "ignorez cet email."}
      </p>
    </div>
    """
    import logging
    from email.utils import parseaddr, formataddr
    sender = settings.DEFAULT_FROM_EMAIL
    if brand == "Immigration97":
        sender = getattr(settings, "IMMIGRATION97_DEFAULT_FROM_EMAIL", "") or formataddr((brand, parseaddr(sender)[1]))
    try:
        send_mail(
            subject=sujet,
            message=corps_txt,
            html_message=corps_html,
            from_email=sender,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logging.getLogger(__name__).exception("Échec d'envoi du code de vérification")



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
            messages.error(request, "No code was found. Please register again." if request.LANGUAGE_CODE == "en" else "Aucun code trouvé. Veuillez vous réinscrire.")
            return redirect("accounts:register")

        if verif.is_verified:
            messages.info(request, "This account is already verified. Please sign in." if request.LANGUAGE_CODE == "en" else "Compte déjà vérifié. Connectez-vous.")
            return redirect("accounts:login")

        if verif.est_expire:
            messages.error(request, "⏰ Code expired. Select “Send a new code”." if request.LANGUAGE_CODE == "en" else "⏰ Code expiré. Cliquez sur « Renvoyer le code ».")
        elif verif.tentatives >= 5:
            messages.error(request, "Too many attempts. Select “Send a new code”." if request.LANGUAGE_CODE == "en" else "Trop de tentatives. Cliquez sur « Renvoyer le code ».")
        elif code_saisi != verif.code:
            verif.tentatives += 1
            verif.save(update_fields=["tentatives"])
            restantes = 5 - verif.tentatives
            messages.error(request, f"❌ Incorrect code. {restantes} attempt(s) remaining." if request.LANGUAGE_CODE == "en" else f"❌ Code incorrect. {restantes} tentative(s) restante(s).")
        else:
            # ✅ Code correct — activer le compte
            verif.is_verified = True
            verif.save(update_fields=["is_verified"])
            user.is_active = True
            user.save(update_fields=["is_active"])

            del request.session["verif_user_id"]
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"🎉 Welcome {user.first_name or user.username}! Your account is active." if request.LANGUAGE_CODE == "en" else f"🎉 Bienvenue {user.first_name or user.username} ! Votre compte est activé.")
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
    _envoyer_code_verification(user, verif.code, request=request)
    messages.success(request, f"✅ A new code was sent to {user.email}. Check your inbox." if request.LANGUAGE_CODE == "en" else f"✅ Nouveau code envoyé à {user.email}. Vérifiez votre boîte mail.")
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

    if getattr(request, "is_immigration97", False):
        all_subs = all_subs.filter(plan__app_key="prep")

    # Abonnements actifs par app_key
    active_subs = {}
    for sub in all_subs:
        key = sub.plan.app_key
        if key not in active_subs and sub.is_active:
            active_subs[key] = sub

    # Historique paiements — total dépensé AVANT le slice
    payments_qs = PaymentHistory.objects.filter(user=user).select_related("subscription__plan")
    if getattr(request, "is_immigration97", False):
        payments_qs = payments_qs.filter(subscription__plan__app_key="prep")
    total_spent = sum(
        payments_qs.filter(status="success").values_list("amount_xaf", flat=True)
    )
    payments = payments_qs[:10]

    # Apps disponibles avec leur état
    apps_info = []
    for key, label in AppKey.choices:
        if getattr(request, "is_immigration97", False) and key != "prep":
            continue
        sub = active_subs.get(key)
        
        # Déterminer l'URL d'ouverture
        url = f"/{key}/"
        if key == "allemand":
            url = "/allemand/"
        elif key == "prep":
            url = "/prep/"
        elif key == "adgen":
            url = "/pub/"
        elif key == "rencontres":
            url = "/rencontres/"
        elif key == "autoecole":
            url = "/auto-ecole/"

        apps_info.append({
            "key":    key,
            "label":  APP_LABELS_EN.get(label, label) if request.LANGUAGE_CODE == "en" else label,
            "icon":   APP_ICONS.get(key, "📦"),
            "color":  APP_COLORS.get(key, "#6B7280"),
            "sub":    sub,
            "active": sub is not None,
            "url":    url,
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

        messages.success(request, "Profile updated." if request.LANGUAGE_CODE == "en" else "Profil mis à jour.")
        return redirect("accounts:mon_compte")

    context = {
        "profile":     profile,
        "active_subs": active_subs,
        "all_subs":    all_subs[:20],
        "payments":    payments,
        "apps_info":   apps_info,
        "stats":       stats,
    }
    for sub in context["all_subs"]:
        sub.plan.public_name = (sub.plan.name_en or sub.plan.name) if request.LANGUAGE_CODE == "en" else sub.plan.name
        sub.plan.public_app_label = APP_LABELS_EN.get(sub.plan.get_app_key_display(), sub.plan.get_app_key_display()) if request.LANGUAGE_CODE == "en" else sub.plan.get_app_key_display()
    for sub in active_subs.values():
        sub.plan.public_name = (sub.plan.name_en or sub.plan.name) if request.LANGUAGE_CODE == "en" else sub.plan.name
        sub.plan.public_app_label = APP_LABELS_EN.get(sub.plan.get_app_key_display(), sub.plan.get_app_key_display()) if request.LANGUAGE_CODE == "en" else sub.plan.get_app_key_display()
    for payment in payments:
        if payment.subscription:
            plan = payment.subscription.plan
            plan.public_name = (plan.name_en or plan.name) if request.LANGUAGE_CODE == "en" else plan.name
        payment.public_method = {
            "orange_money": "Orange Money", "mtn_momo": "MTN Mobile Money", "stripe": "Bank card",
            "cinetpay": "CinetPay", "manual": "Manual (admin)", "free": "Free",
        }.get(payment.method, payment.get_method_display()) if request.LANGUAGE_CODE == "en" else payment.get_method_display()
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
    if getattr(request, "is_immigration97", False):
        app_key = "prep"
    if app_key == "allemand":
        return redirect("germany_opportunities:premium_pricing")

    # Filtrer les plans (exclure 'allemand' car il a sa propre page de pricing custom)
    plans_qs = AppPlan.objects.filter(is_active=True).exclude(app_key="allemand").order_by("app_key", "order")
    if app_key and app_key in dict(AppKey.choices):
        plans_qs = plans_qs.filter(app_key=app_key)
        if app_key == "adgen":
            plans_qs = plans_qs.filter(is_free=False).exclude(level__in=["free", "trial"])
        app_label = dict(AppKey.choices).get(app_key, app_key)
        app_icon  = APP_ICONS.get(app_key, "📦")
        app_color = APP_COLORS.get(app_key, "#6B7280")
    else:
        app_key   = None
        app_label = "Toutes les applications"
        app_icon  = "🚀"
        app_color = "#6C3FE8"

    if request.LANGUAGE_CODE == "en":
        app_label = APP_LABELS_EN.get(app_label, app_label)

    app_url = f"/{app_key}/" if app_key else "/"
    if app_key == "adgen":
        app_url = "/pub/"
    elif app_key == "prep":
        app_url = "/prep/"
    elif app_key == "autoecole":
        app_url = "/auto-ecole/"

    # Plan actuel de l'utilisateur pour cette app
    current_sub = None
    if app_key and request.user.is_authenticated:
        current_sub = AppSubscription.get_active_for_user(request.user, app_key)
        if app_key == "adgen" and current_sub and (current_sub.plan.is_free or current_sub.status != "active"):
            current_sub = None

    # Grouper les plans par app si vue globale
    plans_by_app = {}
    for plan in plans_qs:
        plan.public_name = public_text((plan.name_en or plan.name) if request.LANGUAGE_CODE == "en" else plan.name, request_brand(request))
        plan.public_description = public_text((plan.description_en or plan.description) if request.LANGUAGE_CODE == "en" else plan.description, request_brand(request))
        features = (plan.features_en or plan.features) if request.LANGUAGE_CODE == "en" else plan.features
        plan.public_features = [public_text(feature, request_brand(request)) for feature in (features or [])]
        plan.whatsapp_payment_url = payment_request_url(
            brand=getattr(request, "site_brand", "E-Shelle"),
            service=f"{plan.get_app_key_display()} - {plan.name}",
            amount=plan.price_xaf_formatted,
            user=request.user,
            details=(f"{plan.name_en or plan.name} plan for {plan.duration_days} days" if request.LANGUAGE_CODE == "en" else f"Plan {plan.get_level_display()} pour {plan.duration_days} jours"),
        )
        if (
            getattr(request, "is_immigration97", False)
            and plan.app_key == "prep"
            and not plan.is_free
            and plan.price_xaf > 0
        ):
            plan.campay_payment_url = reverse(
                "payments:campay_immigration_plan",
                kwargs={"plan_id": plan.pk},
            )
        k = plan.app_key
        if k not in plans_by_app:
            plans_by_app[k] = {
                "label": APP_LABELS_EN.get(plan.get_app_key_display(), plan.get_app_key_display()) if request.LANGUAGE_CODE == "en" else plan.get_app_key_display(),
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
        "next":        request.GET.get("next", ""),
        "app_url":     app_url,
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
                (f"Your {sub.plan.name_en or sub.plan.name} subscription was cancelled. Access remains available until {sub.expires_at.strftime('%d/%m/%Y') if sub.expires_at else 'the end of the term'}." if request.LANGUAGE_CODE == "en" else f"Votre abonnement {sub.plan.name} a été annulé. Vous conservez l'accès jusqu'au {sub.expires_at.strftime('%d/%m/%Y') if sub.expires_at else 'terme'}." )
            )
        else:
            messages.warning(request, "This subscription is not active." if request.LANGUAGE_CODE == "en" else "Cet abonnement n'est pas actif.")

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
            messages.error(request, "Invalid code. Check it and try again." if request.LANGUAGE_CODE == "en" else "Code invalide. Vérifiez et réessayez.")
            return render(request, "accounts/activer_code.html", {"code_input": raw})

        ok, msg = code_obj.activate(request.user)
        if ok:
            messages.success(request, "Access code activated successfully. Your apps are now available." if request.LANGUAGE_CODE == "en" else f"Code activé avec succès ! {msg}")
            activated = code_obj
        else:
            messages.error(request, ("This access code has been disabled." if msg == "Ce code a été désactivé." else "This access code has already been used." if msg == "Ce code a déjà été utilisé." else msg) if request.LANGUAGE_CODE == "en" else msg)

    code_input = request.GET.get("code", "").strip().upper()
    return render(request, "accounts/activer_code.html", {"activated": activated, "code_input": code_input})
