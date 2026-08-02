from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View


class OwnerSignUpView(View):
    """
    Enforces a single global account policy.
    Redirects unauthenticated users to the global E-Shelle registration page.
    Directly upgrades authenticated client users to vendor/partner status.
    """
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Redirect to global E-Shelle register URL with next parameter back to here
            register_url = reverse("accounts:register")
            next_url = reverse("salonhub_accounts:signup_owner")
            return redirect(f"{register_url}?next={next_url}")

        if request.user.is_owner:
            messages.info(request, "Vous êtes déjà enregistré(e) en tant que prestataire.")
            return redirect("salonhub_dashboard:home")

        # Upgrade existing user to VENDOR/partner role
        user = request.user
        user.role = "VENDOR"
        user.save(update_fields=["role"])
        messages.success(
            request,
            "Félicitations ! Votre compte E-Shelle a été mis à niveau en compte partenaire. "
            "Bienvenue dans votre espace pro."
        )
        return redirect("salonhub_dashboard:home")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)
