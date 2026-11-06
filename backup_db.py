#!/usr/bin/env python
"""Create a private, full Django database fixture and a checksum manifest."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")

import django

django.setup()

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth import get_user_model


def _private_file(path):
    if os.name != "nt":
        os.chmod(path, 0o600)


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(
        os.environ.get(
            "ESHELLE_BACKUP_DIR",
            str(Path.home() / "e-shelle-backups"),
        )
    ).expanduser()
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(backup_dir, 0o700)

    backup_path = backup_dir / f"e-shelle-db-{timestamp}.json"
    manifest_path = backup_dir / f"e-shelle-db-{timestamp}.manifest.json"
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{backup_path.name}.",
        suffix=".tmp",
        dir=backup_dir,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    _private_file(temporary_path)

    try:
        with temporary_path.open("w", encoding="utf-8") as destination:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                "--indent",
                "2",
                stdout=destination,
            )
        if temporary_path.stat().st_size == 0:
            raise RuntimeError("Django produced an empty database backup.")

        temporary_path.replace(backup_path)
        _private_file(backup_path)
        profiles = list(
            apps.get_model("business", "BusinessProfile")
            .objects.order_by("pk")
            .values("pk", "name", "owner_id", "public_slug")
        )
        user_model = get_user_model()
        manifest = {
            "created_at": timestamp,
            "database_engine": settings.DATABASES["default"]["ENGINE"],
            "backup_file": backup_path.name,
            "backup_size_bytes": backup_path.stat().st_size,
            "sha256": _sha256(backup_path),
            "business_profile_count": len(profiles),
            "business_profiles": profiles,
            "user_count": user_model.objects.count(),
        }
        manifest_fd = os.open(
            manifest_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as destination:
            json.dump(manifest, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
        _private_file(manifest_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    print(f"Base sauvegardée : {backup_path}")
    print(f"Manifeste/checksum : {manifest_path}")
    print(f"Fiches Business sauvegardées : {len(profiles)}")
    print(f"Taille : {backup_path.stat().st_size} octets")
    print(f"SHA-256 : {manifest['sha256']}")
    for profile in profiles:
        print(
            "Fiche",
            profile["pk"],
            "|",
            profile["name"],
            "| propriétaire",
            profile["owner_id"],
        )


if __name__ == "__main__":
    main()
