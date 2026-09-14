from urllib.parse import urljoin
from urllib.request import urlopen
from django.core.management.base import BaseCommand, CommandError
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from rencontres.models import PlanPremiumRencontre


class Command(BaseCommand):
    help = 'Contrôle les migrations Love, les offres et les URL statiques versionnées.'

    def add_arguments(self, parser):
        parser.add_argument('--origin', default='https://e-shelle.com')
        parser.add_argument('--offline', action='store_true')

    def handle(self, *args, **options):
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes('rencontres')
        if executor.migration_plan(targets):
            raise CommandError('Migrations rencontres non appliquées.')
        plans = list(PlanPremiumRencontre.objects.all())
        if {p.nom for p in plans} != {'silver', 'gold', 'platinum'}:
            raise CommandError('Les trois pass Love ne sont pas tous présents.')
        for p in plans:
            if p.prix_xaf_mensuel <= 0 or p.duree_jours <= 0:
                raise CommandError(f'Prix ou durée invalide : {p.nom}')
            self.stdout.write(f'{p.get_nom_display()} : {p.prix_xaf_mensuel} XAF, {p.duree_jours} jours')
        if not options['offline']:
            for name in ['rencontres/css/rencontre.css', 'rencontres/css/love-refresh.css',
                         'rencontres/js/discovery.js', 'rencontres/js/messaging.js']:
                url = urljoin(options['origin'], staticfiles_storage.url(name))
                try:
                    with urlopen(url, timeout=20) as response:
                        mime = response.headers.get_content_type()
                        if response.status != 200 or mime == 'text/html':
                            raise CommandError(f'Fichier statique incorrect : {url}')
                    self.stdout.write(f'HTTP 200 : {url}')
                except OSError as exc:
                    raise CommandError(f'Fichier inaccessible : {url}') from exc
        self.stdout.write(self.style.SUCCESS('Contrôles Love réussis.'))
