from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Promote an existing user to staff/superuser for production admin access."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username or email to promote.")

    def handle(self, *args, **options):
        identifier = options["username"].strip()
        User = get_user_model()
        user = (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
        )
        if not user:
            raise CommandError(f"Utilisateur introuvable: {identifier}")

        user.is_staff = True
        user.is_superuser = True
        if hasattr(user, "role"):
            user.role = "SUPERADMIN"
        user.save(update_fields=["is_staff", "is_superuser", "role"] if hasattr(user, "role") else ["is_staff", "is_superuser"])
        self.stdout.write(
            self.style.SUCCESS(
                f"OK admin: {user.username} staff={user.is_staff} superuser={user.is_superuser} role={getattr(user, 'role', '-')}"
            )
        )
