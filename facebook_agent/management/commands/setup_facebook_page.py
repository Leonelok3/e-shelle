"""
Commande Django pour configurer la page Facebook de l'agent IA.

Usage :
  python manage.py setup_facebook_page \
      --page-id 123456789 \
      --page-name "E-Shelle Officiel" \
      --token "EAAxxxx..." \
      [--app-id "12345" --app-secret "abcdef"]

  python manage.py setup_facebook_page --verify   # Vérifier le token actuel
  python manage.py setup_facebook_page --test-post # Publier un post de test
"""

import sys
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Configurer ou vérifier la page Facebook pour l'agent IA E-Shelle"

    def add_arguments(self, parser):
        parser.add_argument("--page-id",    type=str, help="ID de la page Facebook")
        parser.add_argument("--page-name",  type=str, help="Nom de la page Facebook")
        parser.add_argument("--token",      type=str, help="Token d'accès de la page (Page Access Token)")
        parser.add_argument("--app-id",     type=str, default="", help="App ID Meta (optionnel)")
        parser.add_argument("--app-secret", type=str, default="", help="App Secret Meta (optionnel)")
        parser.add_argument("--verify",     action="store_true", help="Vérifier le token de la config active")
        parser.add_argument("--test-post",  action="store_true", help="Publier un post de test")
        parser.add_argument("--status",     action="store_true", help="Afficher la config actuelle")

    def handle(self, *args, **options):
        from facebook_agent.models import FacebookPageConfig
        from facebook_agent.facebook_api import FacebookAPIClient, FacebookAPIError

        # ── Status ──────────────────────────────────────────────────
        if options["status"]:
            configs = FacebookPageConfig.objects.all()
            if not configs.exists():
                self.stdout.write(self.style.WARNING("Aucune configuration trouvée."))
                return
            for cfg in configs:
                status = self.style.SUCCESS("✓ Valide") if cfg.is_token_valid() else self.style.ERROR("✗ Expiré")
                self.stdout.write(f"\n  Page     : {cfg.page_name}")
                self.stdout.write(f"  Page ID  : {cfg.page_id}")
                self.stdout.write(f"  Active   : {'Oui' if cfg.is_active else 'Non'}")
                self.stdout.write(f"  Token    : {status}")
                self.stdout.write(f"  App ID   : {cfg.app_id or '(non défini)'}")
                self.stdout.write(f"  Créée le : {cfg.created_at.strftime('%d/%m/%Y')}")
            return

        # ── Verify ──────────────────────────────────────────────────
        if options["verify"]:
            config = FacebookPageConfig.objects.filter(is_active=True).first()
            if not config:
                raise CommandError("Aucune configuration active. Crée-en une avec --page-id, --page-name, --token")

            self.stdout.write(f"\nVérification du token pour '{config.page_name}'...")
            client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
            info = client.verify_token()

            if info.get("is_valid"):
                self.stdout.write(self.style.SUCCESS(f"✓ Token VALIDE"))
                exp = info.get("expires_at")
                self.stdout.write(f"  Expire : {'Permanent (Long-lived)' if not exp else exp}")
                scopes = info.get("scopes", [])
                if scopes:
                    self.stdout.write(f"  Permissions : {', '.join(scopes)}")

                # Vérifier les permissions requises
                required = {"pages_manage_posts", "pages_read_engagement", "pages_manage_engagement"}
                missing = required - set(scopes)
                if missing:
                    self.stdout.write(self.style.WARNING(
                        f"\n⚠ Permissions manquantes : {', '.join(missing)}"
                        f"\n  Ajoute-les dans l'app Meta Developer puis regenere le token."
                    ))
            else:
                self.stdout.write(self.style.ERROR("✗ Token INVALIDE ou expiré !"))
                self.stdout.write("  → Génère un nouveau Page Access Token sur developers.facebook.com")
            return

        # ── Test post ────────────────────────────────────────────────
        if options["test_post"]:
            config = FacebookPageConfig.objects.filter(is_active=True).first()
            if not config:
                raise CommandError("Aucune configuration active.")

            self.stdout.write(f"\nPublication d'un post de test sur '{config.page_name}'...")
            client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
            try:
                result = client.publish_text_post(
                    "🤖 Test de publication automatique — E-Shelle Agent IA Facebook.\n"
                    "Si tu vois ce message, l'intégration fonctionne parfaitement ! ✅\n"
                    "#EShelle #Test #IA"
                )
                post_id = result.get("id", "")
                self.stdout.write(self.style.SUCCESS(f"✓ Post publié avec succès !"))
                self.stdout.write(f"  ID Facebook : {post_id}")
                self.stdout.write(f"  URL : https://www.facebook.com/{post_id}")
            except FacebookAPIError as e:
                raise CommandError(f"Erreur Facebook API : {e} (code: {e.code})")
            return

        # ── Créer / Mettre à jour la config ──────────────────────────
        page_id   = options.get("page_id")
        page_name = options.get("page_name")
        token     = options.get("token")

        if not all([page_id, page_name, token]):
            self.stdout.write(self.style.ERROR(
                "\nUsage complet :\n"
                "  python manage.py setup_facebook_page \\\n"
                "      --page-id ID_DE_LA_PAGE \\\n"
                "      --page-name \"Nom de la Page\" \\\n"
                "      --token \"EAAxxxxxxx...\"\n\n"
                "Autres options :\n"
                "  --verify     : Vérifier le token actuel\n"
                "  --test-post  : Publier un post de test\n"
                "  --status     : Voir la configuration actuelle\n"
            ))
            return

        config, created = FacebookPageConfig.objects.update_or_create(
            page_id=page_id,
            defaults={
                "page_name": page_name,
                "page_access_token": token,
                "app_id": options.get("app_id") or "",
                "app_secret": options.get("app_secret") or "",
                "is_active": True,
                "last_token_refresh": timezone.now(),
            },
        )

        action = "créée" if created else "mise à jour"
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Configuration {action} avec succès !"
        ))
        self.stdout.write(f"  Page    : {config.page_name}")
        self.stdout.write(f"  Page ID : {config.page_id}")
        self.stdout.write(f"  Active  : Oui")

        # Vérification automatique du token si App ID + Secret fournis
        if config.app_id and config.app_secret:
            self.stdout.write("\nVérification automatique du token...")
            client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
            info = client.verify_token()
            if info.get("is_valid"):
                self.stdout.write(self.style.SUCCESS("  ✓ Token valide"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠ Token non vérifié (peut être un token permanent)"))
        else:
            self.stdout.write(self.style.WARNING(
                "\n  Info : App ID et App Secret non fournis → vérification du token ignorée.\n"
                "  Pour vérifier, relance avec : --verify"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\n  Dashboard : http://localhost:8000/facebook-agent/\n"
            f"  Test post : python manage.py setup_facebook_page --test-post\n"
        ))
