"""
Django Management Command: source_restaurants
Recherche et extrait des restaurants et prestataires de menus à Douala ou autres villes,
les qualifie et les enregistre dans ProspectBusiness pour la prospection E-Shelle.
"""

from django.core.management.base import BaseCommand
from commercial_agent import sourcing_service
from commercial_agent.models import ProspectBusiness


class Command(BaseCommand):
    help = "Recherche et importe des restaurants (Douala) dans la base de prospection commerciale."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ville",
            type=str,
            default="Douala",
            help="Ville cible (ex: Douala, Yaoundé)",
        )
        parser.add_argument(
            "--quartier",
            type=str,
            default="",
            help="Quartier cible (ex: Akwa, Bonapriso, Bonamoussadi, Makepe)",
        )
        parser.add_argument(
            "--mode",
            type=str,
            default="verified",
            choices=["verified", "auto", "text"],
            help="Mode de sourcing: verified (base vérifiée), auto (web/osm), text (texte fourni)",
        )
        parser.add_argument(
            "--keyword",
            type=str,
            default="",
            help="Mot-clé spécifique (ex: braisé, burger, traiteur)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Nombre maximal de restaurants à extraire",
        )
        parser.add_argument(
            "--save",
            action="store_true",
            help="Enregistre directement les leads trouvés dans ProspectBusiness",
        )
        parser.add_argument(
            "--create-draft-resto",
            action="store_true",
            help="Pré-crée également les fiches Restaurant dans E-Shelle Resto",
        )

    def handle(self, *args, **options):
        ville = options["ville"]
        quartier = options["quartier"]
        mode = options["mode"]
        keyword = options["keyword"]
        limit = options["limit"]
        should_save = options["save"]
        create_draft = options["create_draft_resto"]

        self.stdout.write(self.style.NOTICE(
            f"=== Lancement du Sourcing Prestataires [{ville} - {quartier or 'Tous quartiers'}] ==="
        ))

        if mode == "auto":
            leads = sourcing_service.search_web_restaurants(ville=ville, quartier=quartier, keyword=keyword, limit=limit)
        else:
            leads = sourcing_service.get_verified_douala_restaurants()
            if quartier:
                leads = [l for l in leads if quartier.lower() in (l.get("quartier") or "").lower()]
            if keyword:
                k = keyword.lower()
                leads = [l for l in leads if k in (l.get("nom") or "").lower() or k in (l.get("description") or "").lower()]
            leads = leads[:limit]

        self.stdout.write(self.style.SUCCESS(f"Trouvé {len(leads)} établissement(s) éligible(s) :\n"))

        created_count = 0
        updated_count = 0
        draft_resto_count = 0

        for idx, lead in enumerate(leads, 1):
            nom = lead.get("nom")
            tel = lead.get("formatted_phone") or lead.get("telephone")
            q = lead.get("quartier")
            op = lead.get("operateur")
            
            self.stdout.write(f"  {idx}. {nom} | {tel} ({op}) | Quartier: {q}")
            self.stdout.write(f"     Spécialités: {', '.join(lead.get('specialites', []))}")
            
            wa_link = sourcing_service.build_whatsapp_invite_url(lead["telephone"], nom, quartier=q)
            self.stdout.write(f"     Lien WhatsApp: {wa_link[:80]}...")

            if should_save:
                prospect, created = sourcing_service.save_lead_as_prospect(lead)
                if created:
                    created_count += 1
                else:
                    updated_count += 1

                if create_draft:
                    try:
                        resto = sourcing_service.create_resto_draft(prospect)
                        draft_resto_count += 1
                        self.stdout.write(self.style.SUCCESS(f"     -> Fiche resto pré-créée : /resto/{resto.slug}/"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"     -> Erreur fiche resto : {e}"))

            self.stdout.write("")

        if should_save:
            self.stdout.write(self.style.SUCCESS(
                f"\n=== Bilan Sauvegarde : {created_count} prospect(s) créé(s), {updated_count} mis à jour"
                + (f", {draft_resto_count} fiche(s) resto créée(s)" if create_draft else "")
                + " ==="
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "\nAstuce : Ajoutez le drapeau --save pour enregistrer automatiquement dans ProspectBusiness."
            ))
