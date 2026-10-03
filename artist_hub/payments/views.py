"""
artist_hub/payments/views.py
Vues de paiement :
- Webhook sécurisé, idempotent et CSRF-exempt
- Polling JSON léger de statut
- Page d'attente / instructions MoMo / OM / RIB
- Page de succès et d'échec
- Simulateur local MockProvider
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import Payment, PaymentStatus
from .providers.factory import get_payment_provider
from .services import (
    handle_payment_success,
    handle_payment_failure,
    verify_and_update_payment,
)
from artist_hub.conf import hub_settings

logger = logging.getLogger("artist_hub.payments")


@csrf_exempt
def webhook_view(request, provider_name=None):
    """
    Point d'entrée du webhook de paiement.
    CSRF exempt, sécurisé, IDEMPOTENT et avec revérification serveur systématique.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Méthode non autorisée. Seul POST est accepté.")

    provider_slug = provider_name or request.GET.get("provider") or hub_settings.ACTIVE_PAYMENT_PROVIDER
    provider = get_payment_provider(provider_slug)

    logger.info("WEBHOOK_RECEIVED: Provider=%s, IP=%s", provider_slug, request.META.get("REMOTE_ADDR"))

    webhook_data = provider.handle_webhook(request)
    reference = webhook_data.get("reference")

    if not reference:
        logger.warning("WEBHOOK_ERROR: Aucune référence trouvée dans le payload du webhook.")
        return JsonResponse({"error": "Référence de transaction manquante"}, status=400)

    payment = Payment.objects.filter(reference=reference).first()
    if not payment:
        logger.error("WEBHOOK_NOT_FOUND: Paiement %s introuvable en base.", reference)
        return JsonResponse({"error": "Paiement introuvable"}, status=404)

    # REVÉRIFICATION CÔTÉ SERVEUR (Ne jamais croire aveuglément au corps brut si le provider supporte verify)
    verification = provider.verify(reference)
    logger.info(
        "WEBHOOK_VERIFY: Ref=%s, is_paid=%s, status=%s",
        reference,
        verification.is_paid,
        verification.status,
    )

    if verification.is_paid:
        handle_payment_success(payment, raw_data=verification.raw_data or webhook_data.get("raw_data"))
    elif verification.status in ("FAILED", "CANCELLED", "EXPIRED"):
        handle_payment_failure(payment, reason=verification.error_message, raw_data=verification.raw_data)

    return JsonResponse(
        {
            "status": "ok",
            "reference": payment.reference,
            "payment_status": payment.status,
        }
    )


def payment_status_api(request, reference):
    """
    API JSON pour polling léger depuis le navigateur du candidat tant que PENDING.
    """
    payment = get_object_or_404(Payment, reference=reference)

    # Si le paiement est toujours en attente et que le provider est mock ou externe,
    # on effectue une vérification d'appoint côté serveur si demandée
    if payment.status == PaymentStatus.PENDING and request.GET.get("check") == "1":
        verify_and_update_payment(payment.reference, provider_name=payment.provider)
        payment.refresh_from_db()

    target_url = ""
    if payment.status == PaymentStatus.SUCCESS:
        target_url = f"/artist-hub/payments/success/{payment.reference}/"
    elif payment.status == PaymentStatus.FAILED:
        target_url = f"/artist-hub/payments/failed/{payment.reference}/"

    return JsonResponse(
        {
            "reference": payment.reference,
            "status": payment.status,
            "is_paid": payment.is_successful,
            "redirect_url": target_url,
        }
    )


class PaymentWaitingView(View):
    """
    Page d'attente et d'instructions de paiement (MoMo, OM, Ecobank).
    Propose un polling JS automatique pour détecter la validation serveur.
    """

    def get(self, request, reference):
        payment = get_object_or_404(Payment, reference=reference)

        # Si déjà payé, rediriger directement vers la page de confirmation
        if payment.status == PaymentStatus.SUCCESS:
            return redirect("artist_hub:payments:success", reference=payment.reference)

        context = {
            "payment": payment,
            "hub_settings": hub_settings,
            "orange_money": hub_settings.ORANGE_MONEY_NUMBER,
            "mtn_momo": hub_settings.MTN_MOMO_NUMBER,
            "ecobank_rib": hub_settings.ECOBANK_RIB,
            "contact_whatsapp": hub_settings.CONTACT_WHATSAPP,
        }
        return render(request, "artist_hub/payments/waiting.html", context)


class PaymentSuccessView(TemplateView):
    """Page de confirmation de paiement réussi avec accès au reçu / fiche candidat."""

    template_name = "artist_hub/payments/success.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reference = self.kwargs.get("reference")
        payment = get_object_or_404(Payment, reference=reference)
        ctx["payment"] = payment
        ctx["candidate"] = getattr(payment, "candidate", None)
        ctx["hub_settings"] = hub_settings
        return ctx


class PaymentFailedView(TemplateView):
    """Page d'échec de transaction permettant de relancer sans ressaisir le formulaire."""

    template_name = "artist_hub/payments/failed.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reference = self.kwargs.get("reference")
        payment = get_object_or_404(Payment, reference=reference)
        ctx["payment"] = payment
        ctx["candidate"] = getattr(payment, "candidate", None)
        ctx["hub_settings"] = hub_settings
        return ctx


class MockPaymentSimulateView(View):
    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings
        from django.http import Http404
        if not settings.DEBUG:
            raise Http404()
        payment = get_object_or_404(Payment, reference=kwargs["reference"])
        if payment.provider != "mock": raise Http404()
        return super().dispatch(request, *args, **kwargs)

    """
    Vue de simulation locale pour le MockProvider (réservé au développement / test).
    Permet de valider ou échouer une transaction en un clic.
    """

    def get(self, request, reference):
        payment = get_object_or_404(Payment, reference=reference)
        return render(
            request,
            "artist_hub/payments/mock_simulate.html",
            {
                "payment": payment,
                "hub_settings": hub_settings,
            },
        )

    def post(self, request, reference):
        payment = get_object_or_404(Payment, reference=reference)
        action = request.POST.get("action")

        if action == "success":
            handle_payment_success(payment, raw_data={"mode": "mock_simulated_by_user"})
            messages.success(request, _("Paiement simulé avec SUCCÈS !"))
            return redirect("artist_hub:payments:success", reference=payment.reference)
        elif action == "fail":
            handle_payment_failure(payment, reason="Simulation d'échec par l'utilisateur")
            messages.error(request, _("Paiement simulé comme ÉCHOUÉ."))
            return redirect("artist_hub:payments:failed", reference=payment.reference)

        return redirect("artist_hub:payments:waiting", reference=payment.reference)
