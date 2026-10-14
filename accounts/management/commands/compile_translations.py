import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
import polib


class Command(BaseCommand):
    help = "Compile all .po translation files into .mo using polib (no GNU gettext binary needed)"

    def handle(self, *args, **options):
        locale_paths = getattr(settings, "LOCALE_PATHS", [])
        if not locale_paths:
            locale_paths = [settings.BASE_DIR / "locale"]

        total_compiled = 0

        for l_path in locale_paths:
            l_path = Path(l_path)
            if not l_path.exists():
                self.stdout.write(self.style.WARNING(f"Locale path not found: {l_path}"))
                continue

            for root, dirs, files in os.walk(l_path):
                for f in files:
                    if f.endswith(".po"):
                        po_path = Path(root) / f
                        mo_path = po_path.with_suffix(".mo")
                        try:
                            po = polib.pofile(str(po_path))
                            po.save_as_mofile(str(mo_path))
                            self.stdout.write(
                                self.style.SUCCESS(f"Compiled {po_path.relative_to(settings.BASE_DIR)} -> {mo_path.name}")
                            )
                            total_compiled += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error compiling {po_path}: {e}")
                            )

        self.stdout.write(self.style.SUCCESS(f"Done. Successfully compiled {total_compiled} catalog(s)."))
