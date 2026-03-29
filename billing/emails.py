"""
billing/emails.py — Emails transactionnels Immigration97
"""
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "Immigration97 <contact@immigration97.com>")


def send_welcome_subscription(user, plan, subscription):
    """
    Email de bienvenue envoyé après activation d'un abonnement.
    """
    try:
        context = {
            "user": user,
            "plan": plan,
            "subscription": subscription,
            "site_url": "https://immigration97.com",
        }

        subject = f"✅ Bienvenue ! Ton abonnement {plan.name} est actif"
        text_body = render_to_string("billing/emails/welcome_subscription.txt", context)
        html_body = render_to_string("billing/emails/welcome_subscription.html", context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=True)
        logger.info("Email bienvenue envoyé à %s — plan %s", user.email, plan.name)

    except Exception as exc:
        logger.exception("Erreur envoi email bienvenue user=%s: %s", user.id, exc)
