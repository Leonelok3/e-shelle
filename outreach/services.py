import csv
import io
import logging

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def render_template(text: str, recruiter) -> str:
    sector_labels = dict(recruiter.__class__.SECTOR_CHOICES)
    country_labels = dict(recruiter.__class__.COUNTRY_CHOICES)
    contact_name = recruiter.contact_name or "Madame, Monsieur"
    greeting = f"Bonjour {recruiter.contact_name}," if recruiter.contact_name else "Bonjour,"
    return text.format(
        company_name=recruiter.company_name,
        contact_name=contact_name,
        greeting=greeting,
        sector_label=sector_labels.get(recruiter.sector, recruiter.sector),
        country_label=country_labels.get(recruiter.country, recruiter.country),
        city=recruiter.city or "",
    )


REQUIRED_COLS = {"email", "company_name"}
OPTIONAL_COLS = {
    "contact_name", "job_title", "phone", "website",
    "sector", "country", "city", "tags", "notes", "source",
}

# Aliases : noms de colonnes libres → champ standard
COLUMN_ALIASES = {
    "entreprise": "company_name",
    "société": "company_name",
    "company": "company_name",
    "nom entreprise": "company_name",
    "email / portail rh": "email",
    "email portail rh": "email",
    "portail rh": "email",
    "courriel": "email",
    "mail": "email",
    "e-mail": "email",
    "région / ville": "city",
    "region / ville": "city",
    "région/ville": "city",
    "ville": "city",
    "région": "city",
    "region": "city",
    "localisation": "city",
    "site web": "website",
    "site": "website",
    "url": "website",
    "téléphone": "phone",
    "telephone": "phone",
    "tél": "phone",
    "tel": "phone",
    "secteur": "sector",
    "activité": "sector",
    "activite": "sector",
    "domaine": "sector",
    "contact": "contact_name",
    "nom contact": "contact_name",
    "responsable rh": "contact_name",
    "recruteur": "contact_name",
    "profils recherchés": "tags",
    "profils recherches": "tags",
    "profils": "tags",
    "postes": "tags",
    "notes immigration97": "notes",
    "notes": "notes",
    "remarques": "notes",
    "pays": "country",
    "type visa": "tags",   # on l'ajoute aux tags
}

# Mapping secteur libre → code outreach
SECTOR_NAME_MAP = {
    "construction & btp": "construction",
    "construction btp": "construction",
    "construction": "construction",
    "btp": "construction",
    "ti / tech": "tech",
    "ti/tech": "tech",
    "tech": "tech",
    "it": "tech",
    "technologie": "tech",
    "informatique": "tech",
    "santé": "sante",
    "sante": "sante",
    "médical": "sante",
    "medical": "sante",
    "agriculture": "agriculture",
    "agroalimentaire": "agriculture",
    "agriculture / agroalimentaire": "agriculture",
    "nettoyage & facility": "services",
    "nettoyage": "services",
    "facility": "services",
    "services aux entreprises": "services",
    "services": "services",
    "finance & services": "finance",
    "finance": "finance",
    "comptabilité": "finance",
    "industrie": "industrie",
    "logistique": "logistique",
    "transport": "logistique",
    "transport / logistique": "logistique",
    "hôtellerie": "hotellerie",
    "hotellerie": "hotellerie",
    "restauration": "hotellerie",
    "education": "education",
    "éducation": "education",
    "formation": "education",
    "commerce": "commerce",
    "vente": "commerce",
}


def import_contacts_from_csv(file_obj, encoding="utf-8") -> dict:
    from .models import RecruiterContact

    created = updated = skipped = 0
    errors = []
    try:
        text = file_obj.read().decode(encoding, errors="replace")
    except Exception as e:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": [str(e)]}

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Fichier vide ou sans en-têtes"]}

    fieldnames_lower = {f.strip().lower() for f in reader.fieldnames}
    missing = REQUIRED_COLS - fieldnames_lower
    if missing:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": [f"Colonnes manquantes : {missing}"]}

    for i, row in enumerate(reader, start=2):
        row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        email = row_lower.get("email", "").strip().lower()
        if not email or "@" not in email:
            errors.append(f"Ligne {i} : email invalide ({email!r})")
            skipped += 1
            continue
        company = row_lower.get("company_name", "").strip()
        if not company:
            errors.append(f"Ligne {i} : company_name vide")
            skipped += 1
            continue
        defaults = {"company_name": company}
        for col in OPTIONAL_COLS - {"company_name"}:
            val = row_lower.get(col, "").strip()
            if val:
                defaults[col] = val
        try:
            _, was_created = RecruiterContact.objects.update_or_create(email=email, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as e:
            errors.append(f"Ligne {i} ({email}) : {e}")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


def _find_header_row(rows: list) -> int:
    """
    Détecte la ligne d'en-têtes en cherchant la première ligne qui contient
    des mots-clés reconnus (email, entreprise, company...).
    Retourne l'index (0-based) de cette ligne, ou 0 par défaut.
    """
    keywords = {"email", "entreprise", "company", "company_name", "société", "courriel"}
    for i, row in enumerate(rows[:10]):
        cells = {str(c).strip().lower() for c in row if c}
        if cells & keywords:
            return i
    return 0


def _normalize_col(raw: str) -> str:
    """Normalise un nom de colonne brut via COLUMN_ALIASES."""
    key = raw.strip().lower()
    return COLUMN_ALIASES.get(key, key)


def _normalize_sector(raw: str) -> str:
    """Convertit un libellé secteur libre en code outreach."""
    key = raw.strip().lower()
    if key in SECTOR_NAME_MAP:
        return SECTOR_NAME_MAP[key]
    # Recherche partielle
    for k, code in SECTOR_NAME_MAP.items():
        if k in key or key in k:
            return code
    return "autre"


def import_contacts_from_excel(file_obj, default_country="BE") -> dict:
    """
    Import Excel intelligent :
    - Détecte automatiquement la ligne d'en-têtes (ignore titres/sous-titres)
    - Mappe les colonnes libres (Entreprise, Email/Portail RH, Région/Ville…)
    - Normalise les secteurs (Construction & BTP → construction)
    - default_country : code pays par défaut si pas de colonne pays (BE pour Belgique)
    """
    try:
        import openpyxl
    except ImportError:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["openpyxl non installé"]}

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception as e:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": [f"Erreur lecture Excel : {e}"]}

    if not rows:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Fichier Excel vide"]}

    header_idx = _find_header_row(rows)
    raw_headers = [str(h).strip() if h else "" for h in rows[header_idx]]
    # Normaliser les noms de colonnes
    headers = [_normalize_col(h) for h in raw_headers]

    from .models import RecruiterContact
    created = updated = skipped = 0
    errors = []

    for row_num, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells):
            continue  # ligne vide

        data = dict(zip(headers, cells))

        # Email
        email = data.get("email", "").strip().lower()
        if not email or "@" not in email:
            # Chercher dans toutes les colonnes un email valide
            for v in cells:
                if "@" in str(v) and "." in str(v):
                    email = str(v).strip().lower()
                    break
        if not email or "@" not in email:
            skipped += 1
            errors.append(f"Ligne {row_num} : pas d'email valide")
            continue

        # Entreprise
        company = data.get("company_name", "").strip()
        if not company:
            skipped += 1
            errors.append(f"Ligne {row_num} : nom entreprise vide")
            continue

        # Secteur
        sector_raw = data.get("sector", "")
        sector = _normalize_sector(sector_raw) if sector_raw else "autre"

        # Pays
        country = data.get("country", "").strip().upper()
        if not country or len(country) > 3:
            country = default_country

        # Tags : fusionner "tags" + "type visa" si présent
        tags_parts = [t for t in [data.get("tags", ""), data.get("type_visa", "")] if t]
        tags = " | ".join(tags_parts)[:300]

        defaults = {
            "company_name": company,
            "contact_name": data.get("contact_name", "")[:150],
            "job_title": data.get("job_title", "")[:120],
            "phone": data.get("phone", "")[:40],
            "website": data.get("website", "")[:300],
            "city": data.get("city", "")[:120],
            "notes": data.get("notes", ""),
            "sector": sector,
            "country": country,
            "tags": tags,
            "source": "csv_import",
        }
        # Nettoyer les champs trop longs
        for k, v in defaults.items():
            if isinstance(v, str):
                defaults[k] = v.strip()

        try:
            _, was_created = RecruiterContact.objects.update_or_create(
                email=email, defaults=defaults
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as e:
            errors.append(f"Ligne {row_num} ({email}) : {e}")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


def export_contacts_to_csv(queryset) -> str:
    cols = [
        "id", "company_name", "contact_name", "job_title", "email",
        "phone", "website", "sector", "country", "city",
        "status", "source", "tags", "notes",
        "last_contacted_at", "created_at",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for c in queryset:
        writer.writerow({
            "id": c.id, "company_name": c.company_name, "contact_name": c.contact_name,
            "job_title": c.job_title, "email": c.email, "phone": c.phone,
            "website": c.website, "sector": c.sector, "country": c.country,
            "city": c.city, "status": c.status, "source": c.source,
            "tags": c.tags, "notes": c.notes,
            "last_contacted_at": c.last_contacted_at.strftime("%Y-%m-%d %H:%M") if c.last_contacted_at else "",
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return output.getvalue()


def send_single_email(recruiter, template, campaign=None) -> bool:
    from .models import OutreachLog
    try:
        subject = render_template(template.subject, recruiter)
        body_text = render_template(template.body_text, recruiter)
        body_html = render_template(template.body_html, recruiter)
    except Exception as e:
        logger.warning("Template render error for %s: %s", recruiter.email, e)
        subject, body_text, body_html = template.subject, template.body_text, template.body_html

    log = OutreachLog(campaign=campaign, recruiter=recruiter) if campaign else None
    try:
        msg = EmailMultiAlternatives(
            subject=subject, body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL, to=[recruiter.email],
        )
        msg.attach_alternative(body_html, "text/html")
        msg.send(fail_silently=False)
        recruiter.last_contacted_at = timezone.now()
        if recruiter.status == "new":
            recruiter.status = "contacted"
        recruiter.save(update_fields=["last_contacted_at", "status", "updated_at"])
        if log:
            log.save()
        return True
    except Exception as e:
        logger.error("Email send failed to %s: %s", recruiter.email, e)
        if log:
            log.bounced = True
            log.error = str(e)[:400]
            log.save()
        return False


def send_campaign(campaign, dry_run=False) -> dict:
    from .models import RecruiterContact, OutreachLog

    qs = RecruiterContact.objects.exclude(status="bounce")
    sectors = campaign.get_filter_sectors_list()
    if sectors:
        qs = qs.filter(sector__in=sectors)
    countries = campaign.get_filter_countries_list()
    if countries:
        qs = qs.filter(country__in=countries)
    statuses = campaign.get_filter_status_list()
    if statuses:
        qs = qs.filter(status__in=statuses)

    already_sent = set(OutreachLog.objects.filter(campaign=campaign).values_list("recruiter_id", flat=True))
    qs = qs.exclude(id__in=already_sent)

    total = qs.count()
    if not dry_run:
        campaign.total_recipients = total
        campaign.status = "sending"
        campaign.save(update_fields=["total_recipients", "status"])

    sent = failed = 0
    for recruiter in qs.iterator():
        if dry_run:
            sent += 1
            continue
        ok = send_single_email(recruiter, campaign.template, campaign=campaign)
        if ok:
            sent += 1
            campaign.sent_count += 1
        else:
            failed += 1

    if not dry_run:
        campaign.status = "sent"
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=["sent_count", "status", "sent_at"])

    return {"total": total, "sent": sent, "failed": failed}
