#!/usr/bin/env python
"""Preview, then explicitly purge business profiles while retaining protected records."""

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")

KEEP_BUSINESS_ID = 44
KEEP_BUSINESS_NAME = "IMMIGRATION CANADA"
KEEP_BUSINESS_SLUG = "immigration-canada-douala"
KEEP_WABA_ID = "1415282143385478"
KEEP_ADMIN_EMAIL = "leoneldjiala@gmail.com"
CONFIRMATION = "PURGE_ALL_BUSINESS_PROFILES_EXCEPT_44"


def _verified_backup(backup_path):
    backup_path = backup_path.expanduser().resolve()
    manifest_path = backup_path.with_name(
        f"{backup_path.stem}.manifest.json"
    )
    if not backup_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("La sauvegarde ou son manifeste est introuvable.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("backup_file") != backup_path.name:
        raise RuntimeError("Le manifeste ne correspond pas au fichier de sauvegarde.")
    digest = hashlib.sha256()
    with backup_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != manifest.get("sha256"):
        raise RuntimeError("Le checksum de la sauvegarde ne correspond pas.")
    if backup_path.stat().st_size != manifest.get("backup_size_bytes"):
        raise RuntimeError("La taille de la sauvegarde ne correspond pas au manifeste.")
    return backup_path, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", help="Effectuer réellement la suppression.")
    parser.add_argument("--confirm", default="", help="Phrase exacte de confirmation requise avec --execute.")
    args = parser.parse_args()

    backup_path, manifest = _verified_backup(args.backup)

    import django

    django.setup()

    from django.apps import apps
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.db.models.deletion import Collector

    BusinessProfile = apps.get_model("business", "BusinessProfile")
    BusinessWhatsAppConnection = apps.get_model(
        "whatsapp_commerce",
        "BusinessWhatsAppConnection",
    )
    User = get_user_model()

    current_profile_ids = set(
        BusinessProfile.objects.values_list("pk", flat=True)
    )
    saved_profile_ids = {
        row.get("pk")
        for row in manifest.get("business_profiles", [])
        if isinstance(row, dict)
    }
    if current_profile_ids != saved_profile_ids:
        raise RuntimeError(
            "La sauvegarde ne contient pas exactement les fiches actuellement en base. "
            "Refaites une sauvegarde avant l’aperçu ou la suppression."
        )

    target = BusinessProfile.objects.filter(pk=KEEP_BUSINESS_ID).first()
    if (
        target is None
        or target.name.strip().upper() != KEEP_BUSINESS_NAME
        or target.public_slug != KEEP_BUSINESS_SLUG
    ):
        raise RuntimeError("La fiche Business 44 ne correspond pas à la cible attendue.")
    connection = BusinessWhatsAppConnection.objects.filter(business_id=KEEP_BUSINESS_ID).first()
    if connection is None or connection.waba_id != KEEP_WABA_ID:
        raise RuntimeError("La fiche 44 n’a pas le WABA dédié attendu en base.")

    admin = User.objects.filter(email__iexact=KEEP_ADMIN_EMAIL).first()
    if admin is None or not (admin.is_staff or admin.is_superuser):
        raise RuntimeError("Le compte administrateur à préserver est absent ou sans privilèges.")

    profiles = BusinessProfile.objects.exclude(pk=KEEP_BUSINESS_ID).order_by("pk")
    collector = Collector(using="default")
    collector.collect(profiles)
    cascade_counts = {
        model._meta.label: len(objects)
        for model, objects in collector.data.items()
        if objects
    }

    print(f"Sauvegarde vérifiée : {backup_path}")
    print(f"Checksum SHA-256 : {manifest['sha256']}")
    print(f"Fiches à supprimer : {profiles.count()}")
    for profile in profiles.only("pk", "name"):
        print(f"  - {profile.pk}: {profile.name}")
    print("Enregistrements supprimés par cascade :")
    for model_label, count in sorted(cascade_counts.items()):
        print(f"  - {model_label}: {count}")
    print(f"Fiche préservée : {target.pk} {target.name} / WABA {connection.waba_id}")
    print(f"Compte admin préservé : {admin.email}")

    if not args.execute:
        print("Aucune suppression effectuée (aperçu seulement).")
        return
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"Confirmation explicite requise : --confirm {CONFIRMATION}"
        )

    with transaction.atomic():
        protected_profile = BusinessProfile.objects.get(pk=KEEP_BUSINESS_ID)
        if protected_profile.public_slug != KEEP_BUSINESS_SLUG:
            raise RuntimeError("La fiche à préserver a changé pendant la vérification.")
        if not BusinessWhatsAppConnection.objects.filter(
            business_id=KEEP_BUSINESS_ID,
            waba_id=KEEP_WABA_ID,
        ).exists():
            raise RuntimeError("Le WABA de la fiche à préserver a changé.")
        protected_admin = User.objects.get(pk=admin.pk)
        if not (protected_admin.is_staff or protected_admin.is_superuser):
            raise RuntimeError("Le compte admin à préserver a perdu ses privilèges.")
        BusinessProfile.objects.exclude(pk=KEEP_BUSINESS_ID).delete()

    if not BusinessProfile.objects.filter(pk=KEEP_BUSINESS_ID).exists():
        raise RuntimeError("La fiche 44 n’est plus présente après la suppression.")
    if not User.objects.filter(pk=admin.pk).exists():
        raise RuntimeError("Le compte admin n’est plus présent après la suppression.")
    print("Suppression terminée. La fiche 44 et le compte admin sont présents.")


if __name__ == "__main__":
    main()
