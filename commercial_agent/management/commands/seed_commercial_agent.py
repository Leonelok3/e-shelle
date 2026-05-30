from django.core.management.base import BaseCommand

from commercial_agent.models import ProspectBusiness
from commercial_agent.services import CommercialAgentService


class Command(BaseCommand):
    help = "Cree des prospects demo pour l'Agent Commercial IA E-Shelle."

    DATA = [
        {
            "nom": "Maquis Le Bon Ndole",
            "module": "resto",
            "ville": "Douala",
            "quartier": "Bonamoussadi",
            "whatsapp": "+237690100001",
            "responsable": "Madame Aline",
            "description": "Restaurant populaire avec commandes WhatsApp non structurees.",
        },
        {
            "nom": "Depot Gaz Kotto Express",
            "module": "gaz",
            "ville": "Douala",
            "quartier": "Kotto",
            "whatsapp": "+237690100002",
            "responsable": "Brice",
            "description": "Depot de gaz avec demande locale forte le soir.",
        },
        {
            "nom": "Pressing Clean City",
            "module": "pressing",
            "ville": "Yaounde",
            "quartier": "Bastos",
            "whatsapp": "+237690100003",
            "responsable": "Carine",
            "description": "Pressing qui veut collecte et livraison pour bureaux.",
        },
        {
            "nom": "Agro Plantain Ouest",
            "module": "agro",
            "ville": "Bafoussam",
            "quartier": "Marche A",
            "whatsapp": "+237690100004",
            "responsable": "David",
            "description": "Vendeur plantain et macabo qui cherche acheteurs Douala.",
        },
        {
            "nom": "Pharma Nuit Plus",
            "module": "sante",
            "ville": "Douala",
            "quartier": "Akwa",
            "whatsapp": "+237690100005",
            "responsable": "Estelle",
            "description": "Pharmacie qui veut etre visible sur les recherches locales.",
        },
    ]

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for row in self.DATA:
            prospect, was_created = ProspectBusiness.objects.get_or_create(
                nom=row["nom"],
                defaults={
                    **row,
                    "source": ProspectBusiness.Source.DEMO,
                    "statut": ProspectBusiness.Statut.QUALIFIE,
                    "priorite": ProspectBusiness.Priorite.HAUTE,
                },
            )
            if not was_created:
                for key, value in row.items():
                    setattr(prospect, key, value)
                prospect.statut = ProspectBusiness.Statut.QUALIFIE
                updated += 1
            else:
                created += 1
            prospect.save()
            CommercialAgentService.refresh_prospect(prospect)

        CommercialAgentService.seed_scripts()
        self.stdout.write(self.style.SUCCESS(f"Agent commercial demo pret: {created} crees, {updated} mis a jour."))
