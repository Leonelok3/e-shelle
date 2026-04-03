"""
Service de notifications : envoi du code d'accès par SMS et Email.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger('edu_platform')

EDU_CONF = getattr(settings, 'EDU_PLATFORM', {})


def send_access_code_notification(access_code, user):
    """
    Envoie le code d'accès à l'utilisateur via Email et/ou SMS.

    Args:
        access_code: Instance AccessCode généré.
        user: Instance User Django.
    """
    if EDU_CONF.get('SEND_CODE_BY_EMAIL', True):
        _send_code_email(access_code, user)

    if EDU_CONF.get('SEND_CODE_BY_SMS', True):
        _send_code_sms(access_code, user)


def _send_code_email(access_code, user):
    """Envoie le code par email."""
    try:
        subject = f"Votre code d'accès EduCam Pro — {access_code.code}"
        context = {
            'user': user,
            'access_code': access_code,
            'site_name': EDU_CONF.get('SITE_NAME', 'EduCam Pro'),
            'activate_url': f"{getattr(settings, 'SITE_URL', 'https://e-shelle.com')}/edu/activate/",
        }
        html_message = render_to_string('edu_platform/emails/access_code.html', context)
        plain_message = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            f"Votre code d'accès EduCam Pro est :\n\n"
            f"  {access_code.code}\n\n"
            f"Plan : {access_code.plan.name}\n"
            f"Ce code ne peut être activé que sur UN seul appareil.\n\n"
            f"Activez votre compte sur : {context['activate_url']}\n\n"
            f"L'équipe EduCam Pro"
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@e-shelle.com'),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info('Email code envoyé à %s', user.email)
    except Exception as e:
        logger.error('Erreur envoi email à %s: %s', user.email, e)


def _send_code_sms(access_code, user):
    """
    Envoie le code par SMS via le provider configuré (Twilio ou Orange SMS).
    """
    provider = EDU_CONF.get('SMS_PROVIDER', 'twilio')
    try:
        phone = _get_user_phone(user)
        if not phone:
            logger.warning('Numéro de téléphone manquant pour SMS à user %s', user.username)
            return

        message = (
            f"EduCam Pro - Votre code d'acces: {access_code.code}\n"
            f"Plan: {access_code.plan.name}\n"
            f"Activez sur: e-shelle.com/edu/activate/"
        )

        if provider == 'twilio':
            _send_sms_twilio(phone, message)
        elif provider == 'orange_sms':
            _send_sms_orange(phone, message)
        else:
            logger.warning('Provider SMS inconnu: %s', provider)
    except Exception as e:
        logger.error('Erreur envoi SMS pour user %s: %s', user.username, e)


def _get_user_phone(user) -> str:
    """Récupère le numéro de téléphone depuis le profil EduProfile."""
    try:
        return user.edu_profile.phone_number
    except Exception:
        return ''


def _send_sms_twilio(phone: str, message: str):
    """Envoi SMS via Twilio."""
    try:
        from twilio.rest import Client
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone
        )
        logger.info('SMS Twilio envoyé à %s', phone)
    except ImportError:
        logger.error('Twilio non installé. pip install twilio')
    except Exception as e:
        logger.error('Erreur SMS Twilio vers %s: %s', phone, e)


def _send_sms_orange(phone: str, message: str):
    """Envoi SMS via Orange SMS API."""
    import requests
    api_key = getattr(settings, 'ORANGE_SMS_API_KEY', '')
    if not api_key:
        logger.error('ORANGE_SMS_API_KEY non configurée')
        return
    try:
        resp = requests.post(
            'https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B237/requests',
            json={
                'outboundSMSMessageRequest': {
                    'address': f'tel:{phone}',
                    'senderAddress': 'tel:+237',
                    'outboundSMSTextMessage': {'message': message}
                }
            },
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            timeout=10
        )
        resp.raise_for_status()
        logger.info('SMS Orange envoyé à %s', phone)
    except Exception as e:
        logger.error('Erreur SMS Orange vers %s: %s', phone, e)
