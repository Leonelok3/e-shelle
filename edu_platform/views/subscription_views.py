"""
Vues d'abonnement : plans, paiement, retour paiement, statut.
"""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from edu_platform.models import SubscriptionPlan, PaymentTransaction, AccessCode
from edu_platform.forms.subscription_forms import PaymentInitForm
from edu_platform.services.payment_service import MobileMoneyService, PaymentError

logger = logging.getLogger('edu_platform')


class EduLoginRequiredMixin(LoginRequiredMixin):
    login_url = '/edu/login/'


class PlansView(View):
    """Présentation des forfaits d'abonnement."""
    template_name = 'edu_platform/subscription/plans.html'

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_xaf')
        context = {
            'plans': plans,
            'quarterly_plan': plans.filter(plan_type='quarterly').first(),
            'annual_plan': plans.filter(plan_type='annual').first(),
        }
        return render(request, self.template_name, context)


class PaymentView(EduLoginRequiredMixin, View):
    """Formulaire de paiement Mobile Money."""
    template_name = 'edu_platform/subscription/payment.html'

    def get(self, request, plan_id):
        plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
        form = PaymentInitForm(initial={'plan_id': plan_id})
        # Pré-remplir le numéro depuis le profil
        try:
            form.fields['phone_number'].initial = request.user.edu_profile.phone_number
        except Exception:
            pass
        return render(request, self.template_name, {'plan': plan, 'form': form})

    def post(self, request, plan_id):
        plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
        form = PaymentInitForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            # Créer la transaction
            transaction_obj = PaymentTransaction.objects.create(
                user=request.user,
                plan=plan,
                provider=cd['provider'],
                phone_number=cd['phone_number'],
                amount_xaf=plan.price_xaf,
                status='pending',
            )

            service = MobileMoneyService()
            try:
                if cd['provider'] == 'orange_money':
                    resp = service.initiate_orange_money_payment(transaction_obj)
                    # Orange Money redirige vers une page de paiement externe
                    pay_url = resp.get('payment_url') or resp.get('notif_url', '')
                    if pay_url:
                        return redirect(pay_url)
                else:
                    resp = service.initiate_mtn_momo_payment(transaction_obj)

                messages.info(
                    request,
                    f"Paiement initié ! Veuillez confirmer sur votre téléphone ({cd['phone_number']})."
                )
                return redirect('edu:payment_pending', tx_id=str(transaction_obj.transaction_id))

            except PaymentError as e:
                transaction_obj.status = 'failed'
                transaction_obj.save(update_fields=['status'])
                messages.error(request, f"Erreur de paiement : {e}")
                logger.error('Erreur paiement user %s: %s', request.user.username, e)

        return render(request, self.template_name, {'plan': plan, 'form': form})


class PaymentPendingView(EduLoginRequiredMixin, View):
    """Page d'attente de confirmation du paiement."""
    template_name = 'edu_platform/subscription/payment_pending.html'

    def get(self, request, tx_id):
        transaction_obj = get_object_or_404(
            PaymentTransaction,
            transaction_id=tx_id,
            user=request.user
        )
        context = {
            'transaction': transaction_obj,
            'poll_url': f'/edu/api/payment-status/{tx_id}/',
        }
        return render(request, self.template_name, context)


class PaymentSuccessView(EduLoginRequiredMixin, View):
    """Page de succès après paiement confirmé."""
    template_name = 'edu_platform/subscription/success.html'

    def get(self, request, tx_id):
        transaction_obj = get_object_or_404(
            PaymentTransaction,
            transaction_id=tx_id,
            user=request.user,
            status='confirmed'
        )
        # Récupérer le code généré
        try:
            access_code = transaction_obj.access_code
        except Exception:
            access_code = None

        context = {
            'transaction': transaction_obj,
            'access_code': access_code,
            'plan': transaction_obj.plan,
        }
        return render(request, self.template_name, context)


class SubscriptionStatusView(EduLoginRequiredMixin, View):
    """Statut de l'abonnement actuel."""
    template_name = 'edu_platform/subscription/status.html'

    def get(self, request):
        active_code = AccessCode.objects.filter(
            activated_by=request.user,
            status='active',
        ).select_related('plan').first()

        transactions = PaymentTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]

        context = {
            'active_code': active_code,
            'transactions': transactions,
            'days_left': self._days_left(active_code),
        }
        return render(request, self.template_name, context)

    def _days_left(self, code):
        if code and code.expires_at:
            delta = code.expires_at - timezone.now()
            return max(0, delta.days)
        return 0


class RenewSubscriptionView(EduLoginRequiredMixin, View):
    """Page de renouvellement d'abonnement."""
    template_name = 'edu_platform/subscription/renew.html'

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return render(request, self.template_name, {'plans': plans})


class PaymentReturnView(EduLoginRequiredMixin, View):
    """Retour depuis le portail de paiement Orange Money."""
    def get(self, request, provider, tx_id):
        try:
            transaction_obj = PaymentTransaction.objects.get(
                transaction_id=tx_id,
                user=request.user
            )
            if transaction_obj.status == 'confirmed':
                return redirect('edu:payment_success', tx_id=tx_id)
            return redirect('edu:payment_pending', tx_id=tx_id)
        except PaymentTransaction.DoesNotExist:
            messages.error(request, "Transaction introuvable.")
            return redirect('edu:plans')
