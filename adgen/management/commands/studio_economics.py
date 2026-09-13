"""Reproducible planning estimates, not provider invoices or guaranteed profit."""
from decimal import Decimal
from django.core.management.base import BaseCommand
from adgen.studio_plans import STUDIO_PLANS


class Command(BaseCommand):
    help = "Estime la marge des offres Studio à pleine consommation, après enveloppes de communication et gestion."

    def add_arguments(self, parser):
        parser.add_argument("--text-cost-xaf", type=Decimal, default=Decimal("10"))
        parser.add_argument("--render-cost-xaf", type=Decimal, default=Decimal("20"))
        parser.add_argument("--music-cost-xaf", type=Decimal, default=Decimal("5"))
        parser.add_argument("--usd-xaf", type=Decimal, default=Decimal("600"))

    def handle(self, *args, **options):
        self.stdout.write("HYPOTHESES : paiement 5 %, communication 25 %, gestion 20 %, réserve technique 20 %. Hors impôts ; aucune facture réelle lue.")
        for plan in STUDIO_PLANS.values():
            cost = (plan["text"] * options["text_cost_xaf"] + plan["video"] * options["render_cost_xaf"]
                    + plan["music"] * options["music_cost_xaf"]
                    + Decimal(plan["voice"]) / 1000000 * 30 * options["usd_xaf"])
            technical = cost * Decimal("1.2")
            available = Decimal(plan["price"]) * Decimal("0.5") - technical
            self.stdout.write(f"{plan['name']} : prix {plan['price']} XAF | technique + réserve {technical:.0f} | solde prévisionnel {available:.0f} ({available / plan['price'] * 100:.1f} %)")
