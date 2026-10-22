import csv
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import BusinessCatalogItem


REQUIRED_COLUMNS = {"sku", "nom", "prix_detail", "prix_gros", "stock", "categorie"}
MAX_CSV_BYTES = 5 * 1024 * 1024


class CatalogImportError(ValueError):
    pass


def _parse_xaf(value, *, row_number, column, allow_zero=True):
    try:
        amount = Decimal(str(value).strip().replace(" ", "").replace(",", ""))
    except (InvalidOperation, ValueError):
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être un montant XAF valide.")
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être positif.")
    if amount != amount.to_integral_value():
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être un montant entier en XAF.")
    return int(amount)


def _parse_stock(value, *, row_number):
    try:
        stock = int(str(value).strip())
    except (TypeError, ValueError):
        raise CatalogImportError(f"Ligne {row_number}: stock doit être un entier positif ou nul.")
    if stock < 0:
        raise CatalogImportError(f"Ligne {row_number}: stock doit être un entier positif ou nul.")
    return stock


def parse_catalog_csv(upload):
    if getattr(upload, "size", 0) > MAX_CSV_BYTES:
        raise CatalogImportError("Le fichier CSV dépasse la limite de 5 Mo.")
    try:
        raw_content = upload.read()
        if isinstance(raw_content, bytes):
            text = raw_content.decode("utf-8-sig")
        elif isinstance(raw_content, str):
            text = raw_content.lstrip("\ufeff")
        else:
            raise CatalogImportError("Le catalogue doit être un fichier CSV encodé en UTF-8.")
    except UnicodeDecodeError:
        raise CatalogImportError("Le catalogue doit être un fichier CSV encodé en UTF-8.")
    if not text.strip():
        raise CatalogImportError("Le fichier CSV est vide.")

    reader = csv.DictReader(text.splitlines())
    headers = {str(header or "").strip().casefold() for header in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise CatalogImportError(
            "Colonnes CSV manquantes : " + ", ".join(sorted(missing)) + "."
        )

    normalized_rows = []
    seen_skus = set()
    for row_number, row in enumerate(reader, start=2):
        values = {
            str(key or "").strip().casefold(): str(value or "").strip()
            for key, value in row.items()
        }
        sku = values["sku"]
        title = values["nom"]
        category = values["categorie"]
        if not sku or not title or not category:
            raise CatalogImportError(
                f"Ligne {row_number}: sku, nom et categorie ne peuvent pas être vides."
            )
        if len(sku) > 80 or len(title) > 140 or len(category) > 120:
            raise CatalogImportError(f"Ligne {row_number}: sku, nom ou categorie dépasse la longueur autorisée.")
        sku_key = sku.casefold()
        if sku_key in seen_skus:
            raise CatalogImportError(f"Ligne {row_number}: SKU dupliqué dans le fichier ({sku}).")
        seen_skus.add(sku_key)
        normalized_rows.append(
            {
                "sku": sku,
                "title": title,
                "category": category,
                "detail_price": _parse_xaf(values["prix_detail"], row_number=row_number, column="prix_detail"),
                "wholesale_price": _parse_xaf(values["prix_gros"], row_number=row_number, column="prix_gros"),
                "stock": _parse_stock(values["stock"], row_number=row_number),
            }
        )
    if not normalized_rows:
        raise CatalogImportError("Le fichier CSV ne contient aucune ligne produit.")
    return normalized_rows


@transaction.atomic
def import_catalog_rows(business, rows):
    created = 0
    updated = 0
    for row in rows:
        item, was_created = BusinessCatalogItem.objects.update_or_create(
            business=business,
            sku=row["sku"],
            defaults={
                "title": row["title"],
                "category": row["category"],
                "item_type": BusinessCatalogItem.ItemType.PRODUCT,
                "price_label": f'{row["detail_price"]} FCFA',
                "prix_gros_xaf": row["wholesale_price"],
                "stock_quantity": row["stock"],
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated, "total": len(rows)}


def import_catalog_csv(business, upload):
    return import_catalog_rows(business, parse_catalog_csv(upload))
