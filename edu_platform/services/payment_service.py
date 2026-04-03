"""
Service d'intégration paiements Mobile Money.
Providers : Orange Money Cameroun + MTN MoMo.
"""
import hashlib
import hmac
import json
import logging
import uuid
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('edu_platform')

EDU_CONF = getattr(settings, 'EDU_PLATFORM', {})


class PaymentError(Exception):
    """Erreur lors du traitement d'un paiement."""
    pass


class MobileMoneyService:
    """
    Service unifié pour Orange Money et MTN MoMo au Cameroun.
    Chaque méthode lève PaymentError en cas d'échec.
    """

    # ─── ORANGE MONEY ────────────────────────────────────────────────

    def initiate_orange_money_payment(self, transaction_obj) -> dict:
        """
        Initie un paiement Orange Money.
        Retourne le dict de réponse de l'API Orange.

        Flow : POST /orange-money-webpay/cm/v1/webpayment
        """
        api_key = EDU_CONF.get('ORANGE_MONEY_API_KEY', '')
        api_secret = EDU_CONF.get('ORANGE_MONEY_API_SECRET', '')
        merchant_key = EDU_CONF.get('ORANGE_MONEY_MERCHANT_KEY', '')

        if not api_key:
            logger.error('Orange Money API key non configurée')
            raise PaymentError("Configuration Orange Money incomplète.")

        base_url = EDU_CONF.get(
            'ORANGE_MONEY_BASE_URL',
            'https://api.orange.com/orange-money-webpay/cm/v1'
        )

        # Générer le token d'accès OAuth2
        try:
            token_resp = requests.post(
                'https://api.orange.com/oauth/v3/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': api_key,
                    'client_secret': api_secret,
                },
                timeout=15
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get('access_token')
        except requests.RequestException as e:
            logger.error('Erreur token Orange Money: %s', e)
            raise PaymentError(f"Impossible d'obtenir le token Orange Money: {e}")

        # Initier le paiement
        payload = {
            'merchant_key': merchant_key,
            'currency': 'ORA',  # XAF pour Cameroun
            'order_id': str(transaction_obj.transaction_id),
            'amount': int(transaction_obj.amount_xaf),
            'return_url': _build_return_url('orange_money', str(transaction_obj.transaction_id)),
            'cancel_url': _build_cancel_url(),
            'notif_url': _build_webhook_url('orange-money'),
            'lang': 'fr',
            'reference': str(transaction_obj.transaction_id)[:20],
        }

        try:
            resp = requests.post(
                f'{base_url}/webpayment',
                json=payload,
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error('Erreur initiation Orange Money: %s', e)
            raise PaymentError(f"Erreur Orange Money: {e}")

        # Sauvegarder la référence externe
        external_ref = data.get('pay_token') or data.get('notif_token', '')
        if external_ref:
            transaction_obj.external_reference = external_ref
            transaction_obj.status = 'initiated'
            transaction_obj.save(update_fields=['external_reference', 'status'])

        logger.info(
            'Orange Money initié: transaction %s, pay_token %s',
            transaction_obj.transaction_id, external_ref
        )
        return data

    # ─── MTN MOMO ───────────────────────────────────────────────────

    def initiate_mtn_momo_payment(self, transaction_obj) -> dict:
        """
        Initie un paiement MTN Mobile Money (Request To Pay).
        Retourne le dict de réponse de l'API MTN.
        """
        subscription_key = EDU_CONF.get('MTN_MOMO_SUBSCRIPTION_KEY', '')
        api_user = EDU_CONF.get('MTN_MOMO_API_USER', '')
        api_key_mtn = EDU_CONF.get('MTN_MOMO_API_KEY', '')
        environment = EDU_CONF.get('MTN_MOMO_ENVIRONMENT', 'sandbox')

        if not subscription_key:
            raise PaymentError("Configuration MTN MoMo incomplète.")

        base_url = (
            'https://sandbox.momodeveloper.mtn.com'
            if environment == 'sandbox'
            else 'https://proxy.momoapi.mtn.com'
        )

        # Obtenir le token d'accès
        try:
            import base64
            credentials = base64.b64encode(f"{api_user}:{api_key_mtn}".encode()).decode()
            token_resp = requests.post(
                f'{base_url}/collection/token/',
                headers={
                    'Authorization': f'Basic {credentials}',
                    'Ocp-Apim-Subscription-Key': subscription_key,
                },
                timeout=15
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get('access_token')
        except requests.RequestException as e:
            logger.error('Erreur token MTN MoMo: %s', e)
            raise PaymentError(f"Impossible d'obtenir le token MTN MoMo: {e}")

        # Référence unique pour cette requête de paiement
        reference_id = str(uuid.uuid4())
        phone = transaction_obj.phone_number.lstrip('+').lstrip('0')
        if not phone.startswith('237'):
            phone = '237' + phone

        payload = {
            'amount': str(int(transaction_obj.amount_xaf)),
            'currency': 'XAF',
            'externalId': str(transaction_obj.transaction_id),
            'payer': {'partyIdType': 'MSISDN', 'partyId': phone},
            'payerMessage': f'Paiement EduCam Pro — {transaction_obj.plan.name}',
            'payeeNote': f'Transaction {str(transaction_obj.transaction_id)[:8]}',
        }

        callback_url = _build_webhook_url('mtn-momo')

        try:
            resp = requests.post(
                f'{base_url}/collection/v1_0/requesttopay',
                json=payload,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'X-Reference-Id': reference_id,
                    'X-Target-Environment': environment,
                    'X-Callback-Url': callback_url,
                    'Ocp-Apim-Subscription-Key': subscription_key,
                    'Content-Type': 'application/json',
                },
                timeout=15
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error('Erreur initiation MTN MoMo: %s', e)
            raise PaymentError(f"Erreur MTN MoMo: {e}")

        transaction_obj.external_reference = reference_id
        transaction_obj.status = 'initiated'
        transaction_obj.save(update_fields=['external_reference', 'status'])

        logger.info(
            'MTN MoMo initié: transaction %s, reference %s',
            transaction_obj.transaction_id, reference_id
        )
        return {'reference_id': reference_id, 'status': 'pending'}

    # ─── WEBHOOKS ───────────────────────────────────────────────────

    def verify_orange_money_webhook(self, payload: dict, signature: str) -> bool:
        """
        Vérifie la signature HMAC-SHA256 du webhook Orange Money.
        """
        # Lire depuis settings à chaque appel (permet override_settings dans les tests)
        conf = getattr(settings, 'EDU_PLATFORM', {})
        secret = conf.get('WEBHOOK_HMAC_SECRET', '')
        if not secret:
            logger.warning('HMAC secret non configuré — webhook Orange Money non vérifié')
            return False

        expected = hmac.new(
            secret.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature.lower())

    def verify_mtn_momo_callback(self, payload: dict) -> bool:
        """
        Vérifie la validité du callback MTN MoMo.
        MTN utilise une authentification Bearer sur l'URL de callback.
        """
        status = payload.get('status', '').upper()
        return status == 'SUCCESSFUL'

    # ─── POST-PAIEMENT ───────────────────────────────────────────────

    def on_payment_confirmed(self, transaction_obj):
        """
        Appelé quand un paiement est confirmé (par webhook ou polling).

        1. Met transaction.status = 'confirmed'
        2. Appelle generate_access_code(transaction)
        3. Envoie SMS + Email avec le code
        4. Log l'événement
        """
        from edu_platform.services.code_generator import generate_access_code

        if transaction_obj.status == 'confirmed':
            logger.info(
                'Transaction %s déjà confirmée, webhook dupliqué ignoré.',
                transaction_obj.transaction_id
            )
            return

        transaction_obj.status = 'confirmed'
        transaction_obj.confirmed_at = timezone.now()
        transaction_obj.webhook_received_count += 1
        transaction_obj.save(update_fields=['status', 'confirmed_at', 'webhook_received_count'])

        try:
            access_code = generate_access_code(transaction_obj)
            logger.info(
                'Paiement confirmé: transaction=%s, code=%s, user=%s',
                transaction_obj.transaction_id,
                access_code.code,
                transaction_obj.user.username
            )
        except Exception as e:
            logger.error(
                'Erreur génération code après paiement %s: %s',
                transaction_obj.transaction_id, e
            )
            raise


def _build_return_url(provider: str, tx_id: str) -> str:
    from django.urls import reverse
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', 'https://e-shelle.com')
    return f"{base}/edu/payment/return/{provider}/{tx_id}/"


def _build_cancel_url() -> str:
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', 'https://e-shelle.com')
    return f"{base}/edu/plans/"


def _build_webhook_url(provider: str) -> str:
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', 'https://e-shelle.com')
    return f"{base}/edu/webhooks/{provider}/"
