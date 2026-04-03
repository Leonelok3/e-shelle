"""
Endpoints API internes EduCam Pro.
"""
import json
import hashlib
import hmac
import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.conf import settings

from edu_platform.models import PaymentTransaction, AccessCode
from edu_platform.services.payment_service import MobileMoneyService, PaymentError

logger = logging.getLogger('edu_platform')
EDU_CONF = getattr(settings, 'EDU_PLATFORM', {})


class PaymentStatusAPIView(View):
    """
    Polling du statut de paiement (appelé depuis la page d'attente).
    GET /edu/api/payment-status/<tx_id>/
    """
    @method_decorator(login_required(login_url='/edu/login/'))
    def get(self, request, tx_id):
        try:
            transaction_obj = PaymentTransaction.objects.get(
                transaction_id=tx_id,
                user=request.user
            )
            return JsonResponse({
                'status': transaction_obj.status,
                'confirmed': transaction_obj.status == 'confirmed',
                'success_url': f'/edu/payment/success/{tx_id}/' if transaction_obj.status == 'confirmed' else None,
            })
        except PaymentTransaction.DoesNotExist:
            return JsonResponse({'error': 'Transaction introuvable'}, status=404)


class DeviceCheckAPIView(View):
    """
    Vérifie si l'appareil est lié à un code actif.
    POST /edu/api/device-check/
    Body : { "fingerprint": "sha256..." }
    """
    @method_decorator(login_required(login_url='/edu/login/'))
    def post(self, request):
        try:
            data = json.loads(request.body)
            fingerprint = data.get('fingerprint', '')
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Données invalides'}, status=400)

        if not fingerprint:
            return JsonResponse({'error': 'Fingerprint manquant'}, status=400)

        active_code = AccessCode.objects.filter(
            activated_by=request.user,
            status='active',
        ).first()

        if not active_code:
            return JsonResponse({'has_subscription': False, 'device_ok': False})

        from edu_platform.models import DeviceBinding
        binding = DeviceBinding.objects.filter(
            access_code=active_code,
            user=request.user,
            is_primary=True
        ).first()

        if not binding:
            return JsonResponse({'has_subscription': True, 'device_ok': True, 'needs_binding': True})

        device_ok = binding.device_fingerprint == fingerprint
        return JsonResponse({
            'has_subscription': True,
            'device_ok': device_ok,
            'device_label': binding.device_label if device_ok else None,
        })


@method_decorator(csrf_exempt, name='dispatch')
class OrangeMoneyWebhookView(View):
    """
    Webhook Orange Money.
    POST /edu/webhooks/orange-money/
    Sécurisé par signature HMAC-SHA256.
    """
    def post(self, request):
        signature = request.META.get('HTTP_X_ORANGE_SIGNATURE', '')
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error('Webhook Orange Money: payload JSON invalide')
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        service = MobileMoneyService()

        # Vérifier la signature HMAC
        if not service.verify_orange_money_webhook(payload, signature):
            logger.warning('Webhook Orange Money: signature invalide')
            return JsonResponse({'error': 'Invalid signature'}, status=403)

        # Extraire l'ID de commande (notre transaction_id)
        order_id = payload.get('order_id') or payload.get('reference', '')
        status = payload.get('status', '').upper()

        if not order_id:
            return JsonResponse({'error': 'order_id manquant'}, status=400)

        try:
            transaction_obj = PaymentTransaction.objects.get(transaction_id=order_id)
        except PaymentTransaction.DoesNotExist:
            logger.error('Webhook Orange: transaction %s introuvable', order_id)
            return JsonResponse({'error': 'Transaction introuvable'}, status=404)

        # Incrémenter le compteur de webhooks reçus
        transaction_obj.webhook_received_count += 1
        transaction_obj.webhook_data = payload
        transaction_obj.save(update_fields=['webhook_received_count', 'webhook_data'])

        if status in ('SUCCESS', 'SUCCESSFUL', 'COMPLETED'):
            try:
                service.on_payment_confirmed(transaction_obj)
                logger.info('Webhook Orange: paiement confirmé %s', order_id)
            except Exception as e:
                logger.error('Erreur traitement webhook Orange %s: %s', order_id, e)
                return JsonResponse({'error': 'Erreur interne'}, status=500)
        elif status in ('FAILED', 'CANCELLED', 'EXPIRED'):
            if transaction_obj.status not in ('confirmed',):
                transaction_obj.status = 'failed'
                transaction_obj.save(update_fields=['status'])

        return JsonResponse({'status': 'ok'})


@method_decorator(csrf_exempt, name='dispatch')
class MTNMoMoWebhookView(View):
    """
    Callback MTN MoMo.
    POST /edu/webhooks/mtn-momo/
    """
    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        service = MobileMoneyService()

        if not service.verify_mtn_momo_callback(payload):
            logger.warning('Callback MTN MoMo: statut non réussi')
            return JsonResponse({'status': 'not_successful'})

        external_id = payload.get('externalId', '')
        if not external_id:
            return JsonResponse({'error': 'externalId manquant'}, status=400)

        try:
            transaction_obj = PaymentTransaction.objects.get(transaction_id=external_id)
        except PaymentTransaction.DoesNotExist:
            logger.error('Callback MTN: transaction %s introuvable', external_id)
            return JsonResponse({'error': 'Transaction introuvable'}, status=404)

        transaction_obj.webhook_data = payload
        transaction_obj.save(update_fields=['webhook_data'])

        try:
            service.on_payment_confirmed(transaction_obj)
            logger.info('Callback MTN: paiement confirmé %s', external_id)
        except Exception as e:
            logger.error('Erreur traitement callback MTN %s: %s', external_id, e)
            return JsonResponse({'error': 'Erreur interne'}, status=500)

        return JsonResponse({'status': 'ok'})
