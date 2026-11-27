from decimal import Decimal, ROUND_HALF_UP

from django import template
from django.utils.translation import gettext as _

register = template.Library()

XAF_PER_EURO = Decimal("655.957")
PLAN_PRICES = {"free": 0, "pro": 5000, "business": 15000, "premium": 30000}


@register.filter
def home_eur(xaf):
    if xaf == 0:
        return "0\u00a0€"
    euros = (Decimal(xaf) / XAF_PER_EURO).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    amount = f"{euros:,.2f}".translate(str.maketrans({",": "\u202f", ".": ","}))
    return f"≈\u00a0{amount}\u00a0€"


@register.filter
def home_xaf(xaf):
    amount = f"{xaf:,}".replace(",", "\u202f")
    return f"{amount}\u00a0F\u00a0CFA"


@register.simple_tag
def home_prices():
    return PLAN_PRICES


@register.simple_tag
def home_faq():
    def price(plan):
        xaf = PLAN_PRICES[plan]
        return f"{home_eur(xaf)} ({home_xaf(xaf)})"

    return (
        (
            "Qu’est-ce qu’E-Shelle ?",
            _("E-Shelle aide les restaurants à publier un menu en ligne avec leurs prix, "
              "à créer un site sur devis ou à utiliser un agent IA WhatsApp selon leur formule."),
        ),
        (
            "Combien coûte une fiche E-Shelle ?",
            f"La fiche gratuite coûte {price('free')} et reste visible 14 jours. "
            "Pour 30 jours et par fiche, "
            f"Présence Pro coûte {price('pro')}, Croissance Business {price('business')} "
            f"et Premium {price('premium')}. Les frais de messagerie facturés par Meta sont en plus.",
        ),
        (
            "Puis-je arrêter après 30 jours ?",
            "Les formules payantes sont activées pour 30 jours. Vérifie les conditions de "
            "renouvellement affichées au moment de l’activation.",
        ),
        (
            "Qui crée ma fiche restaurant ?",
            "Tu peux la créer toi-même depuis ton compte. Si tu veux de l’aide, écris à "
            "E-Shelle sur WhatsApp pour connaître les options et leurs tarifs.",
        ),
        (
            "Dans quelle devise est-ce que je paie ?",
            "Les forfaits sont facturés en F CFA. L’équivalent en euros est indicatif. "
            "Les moyens disponibles s’affichent lors de l’activation. Tu conviens du "
            "paiement et de la livraison directement avec tes clients.",
        ),
        (
            _("Est-ce que ça marche dans mon pays ?"),
            _("Tu peux créer et gérer une fiche en ligne à distance. Avant de choisir une "
              "formule payante, vérifie les moyens de paiement disponibles. La connexion "
              "WhatsApp Business dépend aussi de ton pays, de ton numéro et des règles Meta."),
        ),
        (
            _("Comment connecter mon numéro WhatsApp Business ?"),
            _("Avec Business ou Premium, lance la connexion depuis ton compte E-Shelle. "
              "Prépare ton numéro et tes accès Meta. Notre équipe peut t’aider à suivre les étapes."),
        ),
        (
            _("Puis-je avoir un site restaurant sur mesure ?"),
            _("Oui, tu peux demander un devis. On définit ensemble le contenu, les "
              "fonctionnalités et les conditions d’hébergement selon ton projet."),
        ),
        (
            _("L’agent IA remplace-t-il mon personnel ?"),
            _("L’agent répond aux questions courantes à partir de ta fiche et de ton menu. "
              "Ton équipe garde la main sur les décisions et les demandes qui exigent une validation."),
        ),
        (
            "Comment fonctionne WhatsApp sur ma fiche ?",
            "Le client touche le bouton WhatsApp et t’écrit directement. L’agent et les "
            "relances dépendent de la formule, de la configuration, des droits, des "
            "validations Meta et du consentement requis. Pour la prospection sur WhatsApp, "
            "recueille le consentement quand il est requis et respecte les règles locales, "
            "dont le RGPD lorsqu’il s’applique. Meta facture les frais de messagerie.",
        ),
        (
            "Puis-je gérer mon restaurant en Afrique depuis l’étranger ?",
            "Oui. Tu peux créer et gérer ta fiche depuis Paris, Bruxelles, Londres ou "
            "Montréal et consulter les vues et les clics dans ton tableau de bord.",
        ),
        (
            "Comment publier mon restaurant sur Google Maps ?",
            "E-Shelle peut t’accompagner pour préparer ta fiche Google Business. "
            "La publication et l’affichage sur Maps dépendent de ton éligibilité "
            "et des validations de Google.",
        ),
    )
