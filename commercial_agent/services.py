import json
import urllib.parse
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import CampagneProspection, ProspectBusiness, RelanceProspect, ScriptCommercial


PLAN_PRICES = {
    "pro": 5000,
    "business": 10000,
    "premium": 25000,
}


MODULE_PITCHES = {
    "resto": "recevoir plus de commandes WhatsApp et rendre votre menu visible",
    "gaz": "recevoir des commandes de gaz proches de votre zone",
    "pressing": "gagner des clients qui cherchent collecte et livraison de linge",
    "sante": "etre trouve rapidement par les clients qui cherchent produits sante ou pharmacie",
    "agro": "vendre vos produits agricoles a plus d'acheteurs",
    "services": "recevoir plus de demandes de travaux et prestations",
    "immobilier": "obtenir plus d'appels et visites qualifiees",
    "auto": "recevoir plus de contacts acheteurs pour vos vehicules",
    "jobs": "diffuser vos opportunites a une audience locale",
}


class CommercialAgentService:
    """Cerveau commercial IA pour prioriser, contacter et convertir les prospects."""

    @classmethod
    def score_prospect(cls, prospect: ProspectBusiness) -> int:
        score = 15
        if prospect.contact_whatsapp:
            score += 25
        if prospect.ville:
            score += 10
        if prospect.source == ProspectBusiness.Source.IMPORT:
            score += 10
        if prospect.assigne_a_id:
            score += 5
        if prospect.description or prospect.notes:
            score += 5
        if prospect.statut == ProspectBusiness.Statut.QUALIFIE:
            score += 5
        if prospect.business_profile:
            score += min(prospect.business_profile.views_count // 5, 15)
            score += min(prospect.business_profile.leads_count * 3, 20)
            if prospect.business_profile.plan in {"business", "premium"}:
                score += 25
            elif prospect.business_profile.plan == "pro":
                score += 15
        if prospect.module in {"resto", "gaz", "pressing", "sante", "agro", "services", "immobilier", "auto", "jobs"}:
            score += 10
        if prospect.statut in {ProspectBusiness.Statut.INTERESSE, ProspectBusiness.Statut.NEGOCIATION}:
            score += 20
        return min(score, 100)

    @classmethod
    def recommend_plan(cls, prospect: ProspectBusiness) -> str:
        if prospect.score >= 75:
            return "premium"
        if prospect.score >= 50:
            return "business"
        return "pro"

    @classmethod
    def refresh_prospect(cls, prospect: ProspectBusiness):
        prospect.score = cls.score_prospect(prospect)
        prospect.plan_recommande = cls.recommend_plan(prospect)
        prospect.montant_potentiel_xaf = PLAN_PRICES.get(prospect.plan_recommande, 5000)
        if not prospect.prochain_contact and prospect.statut in {
            ProspectBusiness.Statut.NOUVEAU,
            ProspectBusiness.Statut.QUALIFIE,
            ProspectBusiness.Statut.A_RELANCER,
        }:
            prospect.prochain_contact = timezone.localdate()
        prospect.save(
            update_fields=[
                "score",
                "plan_recommande",
                "montant_potentiel_xaf",
                "prochain_contact",
                "maj_le",
            ]
        )
        return prospect

    @classmethod
    def sync_from_business_profiles(cls, limit=200, assigne_a=None):
        """Transforme les fiches BusinessProfile en prospects commerciaux."""

        try:
            from business.models import BusinessProfile
        except Exception:
            return {"created": 0, "updated": 0}

        qs = BusinessProfile.objects.filter(is_active=True).order_by("-leads_count", "-views_count", "-created_at")[:limit]
        created = 0
        updated = 0
        for business in qs:
            prospect, was_created = ProspectBusiness.objects.get_or_create(
                business_profile=business,
                defaults={
                    "nom": business.name,
                    "module": business.module,
                    "ville": business.city,
                    "quartier": business.district,
                    "telephone": business.phone,
                    "whatsapp": business.whatsapp,
                    "description": business.description,
                    "source": ProspectBusiness.Source.BUSINESS_PROFILE,
                    "assigne_a": assigne_a,
                    "statut": ProspectBusiness.Statut.QUALIFIE,
                },
            )
            if not was_created:
                prospect.nom = business.name
                prospect.module = business.module
                prospect.ville = business.city
                prospect.quartier = business.district
                prospect.telephone = business.phone
                prospect.whatsapp = business.whatsapp
                prospect.description = business.description
                updated += 1
            else:
                created += 1
            cls.refresh_prospect(prospect)
        return {"created": created, "updated": updated}

    @classmethod
    def sync_from_whatsapp_contacts(cls, limit=300, assigne_a=None, module="services", contact_ids=None):
        """Transforme les contacts WhatsApp autorises en prospects commerciaux."""

        try:
            from whatsapp_agent.models import ContactWhatsApp
        except Exception:
            return {"created": 0, "updated": 0, "skipped": 0}

        qs = ContactWhatsApp.objects.filter(consentement_confirme=True)
        if contact_ids:
            qs = qs.filter(id__in=contact_ids)
        qs = qs.order_by("-cree_le")[:limit]
        created = 0
        updated = 0
        skipped = 0
        for contact in qs:
            numero = contact.numero.strip()
            if not numero:
                skipped += 1
                continue
            prospect = ProspectBusiness.objects.filter(Q(whatsapp=numero) | Q(telephone=numero)).first()
            if prospect:
                prospect.nom = prospect.nom or contact.nom or numero
                prospect.ville = prospect.ville or contact.ville
                prospect.telephone = prospect.telephone or numero
                prospect.whatsapp = prospect.whatsapp or numero
                prospect.description = prospect.description or contact.note
                prospect.notes = (prospect.notes or "") + (
                    f"\nImport WhatsApp: {contact.groupe or contact.source}".strip()
                    if contact.groupe or contact.source
                    else ""
                )
                prospect.assigne_a = prospect.assigne_a or assigne_a
                prospect.save(
                    update_fields=[
                        "nom",
                        "ville",
                        "telephone",
                        "whatsapp",
                        "description",
                        "notes",
                        "assigne_a",
                        "maj_le",
                    ]
                )
                updated += 1
            else:
                prospect = ProspectBusiness.objects.create(
                    nom=contact.nom or f"Contact WhatsApp {numero}",
                    module=module or "services",
                    ville=contact.ville,
                    telephone=numero,
                    whatsapp=numero,
                    description=contact.note,
                    source=ProspectBusiness.Source.IMPORT,
                    statut=ProspectBusiness.Statut.QUALIFIE,
                    assigne_a=assigne_a,
                    notes=f"Import WhatsApp autorise. Groupe/source: {contact.groupe or contact.source}",
                )
                created += 1
            cls.refresh_prospect(prospect)
        return {"created": created, "updated": updated, "skipped": skipped}

    @classmethod
    def generate_message(cls, prospect: ProspectBusiness, canal="whatsapp", contexte="") -> str:
        """Genere un message commercial court. Utilise Claude si configure, sinon fallback solide."""

        pitch = MODULE_PITCHES.get(prospect.module, "recevoir plus de clients via E-Shelle")
        plan = prospect.plan_recommande or cls.recommend_plan(prospect)
        prix = PLAN_PRICES.get(plan, 5000)
        fallback = (
            f"Bonjour {prospect.responsable or prospect.nom}, je suis de E-Shelle. "
            f"On peut aider {prospect.nom} a {pitch}. "
            f"Le plan {plan.title()} commence a {prix:,} FCFA/mois. "
            "Voulez-vous une demo rapide sur WhatsApp ?"
        ).replace(",", " ")

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            return fallback

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            prompt = f"""Tu es l'agent commercial IA d'E-Shelle au Cameroun.
Ecris un message {canal} court, professionnel, chaleureux, sans promesse excessive.
Prospect: {prospect.nom}
Module: {prospect.module or "general"}
Ville: {prospect.ville or "non renseignee"}
Besoin: {pitch}
Plan conseille: {plan} ({prix} FCFA/mois)
Contexte: {contexte}
Objectif: obtenir une reponse ou une demo rapide.
Reponds uniquement avec le message."""
            response = client.messages.create(
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=220,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            return fallback

    @classmethod
    def create_relance(cls, prospect, user=None, campagne=None, type_action="whatsapp", message=""):
        if not message:
            message = cls.generate_message(prospect, canal=type_action)
        relance = RelanceProspect.objects.create(
            prospect=prospect,
            campagne=campagne,
            type_action=type_action,
            resultat=RelanceProspect.Resultat.ENVOYE if type_action == "whatsapp" else RelanceProspect.Resultat.A_FAIRE,
            message=message,
            effectue_par=user if getattr(user, "is_authenticated", False) else None,
            prochaine_relance=timezone.localdate() + timedelta(days=2),
        )
        prospect.statut = ProspectBusiness.Statut.CONTACTE if prospect.statut in {
            ProspectBusiness.Statut.NOUVEAU,
            ProspectBusiness.Statut.QUALIFIE,
            ProspectBusiness.Statut.A_RELANCER,
        } else prospect.statut
        prospect.dernier_contact = timezone.now()
        prospect.prochain_contact = relance.prochaine_relance
        prospect.save(update_fields=["statut", "dernier_contact", "prochain_contact", "maj_le"])
        return relance

    @classmethod
    def whatsapp_url(cls, prospect, message):
        number = (prospect.contact_whatsapp or "").replace("+", "").replace(" ", "").replace("-", "")
        if not number:
            return ""
        if not number.startswith("237"):
            number = f"237{number}"
        return f"https://wa.me/{number}?text={urllib.parse.quote(message)}"

    @classmethod
    def create_campaign_from_due(cls, name, user=None, module="", ville="", limit=50):
        qs = ProspectBusiness.objects.filter(Q(whatsapp__gt="") | Q(telephone__gt=""))
        qs = qs.filter(statut__in=[
            ProspectBusiness.Statut.NOUVEAU,
            ProspectBusiness.Statut.QUALIFIE,
            ProspectBusiness.Statut.A_RELANCER,
            ProspectBusiness.Statut.INTERESSE,
        ])
        if module:
            qs = qs.filter(module=module)
        if ville:
            qs = qs.filter(ville__icontains=ville)
        qs = qs.filter(Q(prochain_contact__isnull=True) | Q(prochain_contact__lte=timezone.localdate())).order_by("-score")[:limit]
        campagne = CampagneProspection.objects.create(
            nom=name,
            module_cible=module,
            ville_cible=ville,
            objectif="Convertir les prospects chauds en abonnements E-Shelle.",
            statut=CampagneProspection.Statut.ACTIVE,
            cree_par=user if getattr(user, "is_authenticated", False) else None,
            lance_le=timezone.now(),
        )
        campagne.prospects.set(qs)
        return campagne

    @classmethod
    def create_whatsapp_campaign_from_due(cls, name, user=None, module="", ville="", limit=50):
        """Cree une campagne WhatsApp validee depuis les prospects commerciaux a relancer."""

        from whatsapp_agent.models import Campagne, MessageEnvoi
        from whatsapp_agent.tasks import recalculer_stats_campagne

        qs = ProspectBusiness.objects.filter(Q(whatsapp__gt="") | Q(telephone__gt="")).filter(
            statut__in=[
                ProspectBusiness.Statut.NOUVEAU,
                ProspectBusiness.Statut.QUALIFIE,
                ProspectBusiness.Statut.CONTACTE,
                ProspectBusiness.Statut.A_RELANCER,
                ProspectBusiness.Statut.INTERESSE,
                ProspectBusiness.Statut.NEGOCIATION,
            ]
        )
        if module:
            qs = qs.filter(module=module)
        if ville:
            qs = qs.filter(ville__icontains=ville)
        qs = qs.filter(Q(prochain_contact__isnull=True) | Q(prochain_contact__lte=timezone.localdate())).order_by("-score")[:limit]
        prospects = list(qs)

        campagne = Campagne.objects.create(
            nom=name,
            description=(
                "Campagne commerciale creee depuis l'Agent Commercial IA. "
                "Verifiez l'apercu final avant lancement."
            ),
            message_template="Message commercial personnalise par prospect.",
            statut=Campagne.STATUT_VALIDEE,
            filtre_role="prospects_commerciaux",
            filtre_ville=ville,
            cree_par=user if getattr(user, "is_authenticated", False) else None,
        )
        messages = []
        for prospect in prospects:
            message = cls.generate_message(prospect, canal="whatsapp")
            messages.append(
                MessageEnvoi(
                    campagne=campagne,
                    user=None,
                    commercial_prospect=prospect,
                    destinataire_nom=prospect.nom,
                    numero_whatsapp=prospect.contact_whatsapp,
                    message_final=message,
                )
            )
        MessageEnvoi.objects.bulk_create(messages, batch_size=200)
        recalculer_stats_campagne(campagne)
        return campagne

    @classmethod
    def seed_scripts(cls):
        scripts = [
            ("WhatsApp premier contact", "whatsapp", "", "Bonjour {{nom}}, je suis de E-Shelle. On aide les business locaux a recevoir plus de clients via WhatsApp. Disponible pour une demo rapide ?"),
            ("Relance interet", "whatsapp", "", "Bonjour {{nom}}, je reviens vers vous pour la fiche E-Shelle. On peut vous rendre visible dans votre ville et suivre les contacts clients."),
            ("Pitch appel", "appel", "", "Bonjour, je vous appelle de E-Shelle. L'objectif est simple: vous apporter plus de clients locaux et mesurer les contacts WhatsApp."),
        ]
        for nom, canal, module, contenu in scripts:
            ScriptCommercial.objects.get_or_create(nom=nom, canal=canal, module=module, defaults={"contenu": contenu})
