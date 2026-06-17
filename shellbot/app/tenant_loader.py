import json
from pathlib import Path

from sqlalchemy.orm import Session

from .config import get_settings
from .models import Tenant


def sync_tenants_from_file(db: Session) -> int:
    settings = get_settings()
    path = Path(settings.tenants_file)
    if not path.exists():
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for item in data:
        tenant = db.query(Tenant).filter(Tenant.slug == item["slug"]).first()
        payload = {
            "business_name": item.get("business_name", item["slug"]),
            "phone_number_id": item.get("phone_number_id", ""),
            "owner_email": item.get("owner_email", ""),
            "human_phone": item.get("human_phone", ""),
            "timezone": item.get("timezone", "America/Toronto"),
            "language_default": item.get("language_default", "fr"),
            "calendly_url": item.get("calendly_url", ""),
            "business_context": item.get("business_context", ""),
            "faq_json": json.dumps(item.get("faq", []), ensure_ascii=True),
            "services_json": json.dumps(item.get("services", []), ensure_ascii=True),
        }
        if tenant:
            for key, value in payload.items():
                setattr(tenant, key, value)
        else:
            tenant = Tenant(slug=item["slug"], **payload)
            db.add(tenant)
        count += 1
    db.commit()
    return count

