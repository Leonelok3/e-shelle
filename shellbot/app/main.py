import csv
import io
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from .bot import ShellBot
from .config import get_settings
from .database import get_db, init_db
from .models import Conversation, Lead, Message, Quote, Tenant
from .tenant_loader import sync_tenants_from_file


app = FastAPI(title="ShellBot", version="0.1.0")


@app.on_event("startup")
def startup():
    init_db()
    from .database import SessionLocal

    db = SessionLocal()
    try:
        sync_tenants_from_file(db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).order_by(Tenant.business_name).all()
    conversations = db.query(Conversation).order_by(Conversation.updated_at.desc()).limit(40).all()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(20).all()
    quotes = db.query(Quote).order_by(Quote.created_at.desc()).limit(20).all()
    return _dashboard_html(tenants, conversations, leads, quotes)


@app.get("/health")
def health():
    return {"status": "ok", "product": "ShellBot"}


@app.get("/webhooks/meta")
def verify_webhook(request: Request):
    settings = get_settings()
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == settings.meta_verify_token:
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Invalid verify token")


@app.post("/webhooks/meta")
async def receive_webhook(payload: dict[str, Any], db: Session = Depends(get_db)):
    events = _extract_messages(payload)
    bot = ShellBot(db)
    replies = []
    for event in events:
        tenant = db.query(Tenant).filter(Tenant.phone_number_id == event["phone_number_id"]).first()
        if not tenant or not tenant.is_active:
            continue
        reply = bot.handle_message(
            tenant=tenant,
            wa_id=event["from"],
            text=event["text"],
            customer_name=event.get("customer_name", ""),
        )
        replies.append({"to": event["from"], "reply": reply})
    return {"received": len(events), "replies": replies}


@app.post("/demo/{tenant_slug}/message")
async def demo_message(tenant_slug: str, body: dict[str, str], db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    reply = ShellBot(db).handle_message(
        tenant=tenant,
        wa_id=body.get("from", "+15145550123"),
        text=body.get("text", ""),
        customer_name=body.get("name", "Demo Client"),
    )
    return {"reply": reply}


@app.get("/exports/leads.csv")
def export_leads(db: Session = Depends(get_db)):
    rows = db.query(Lead).order_by(Lead.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["tenant_id", "name", "email", "phone", "need", "language", "status", "created_at"])
    for row in rows:
        writer.writerow([row.tenant_id, row.name, row.email, row.phone, row.need, row.language, row.status, row.created_at])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=leads.csv"})


@app.get("/exports/quotes.csv")
def export_quotes(db: Session = Depends(get_db)):
    rows = db.query(Quote).order_by(Quote.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["tenant_id", "customer_name", "need", "amount_cad", "status", "created_at"])
    for row in rows:
        writer.writerow([row.tenant_id, row.customer_name, row.need, row.amount_cad, row.status, row.created_at])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=quotes.csv"})


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    events = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from", "")
                events.append(
                    {
                        "phone_number_id": phone_number_id,
                        "from": sender,
                        "customer_name": contacts.get(sender, ""),
                        "text": message.get("text", {}).get("body", ""),
                    }
                )
    return events


def _dashboard_html(tenants, conversations, leads, quotes):
    tenant_rows = "".join(f"<tr><td>{t.business_name}</td><td>{t.slug}</td><td>{t.phone_number_id}</td><td>{'OK' if t.is_active else 'OFF'}</td></tr>" for t in tenants)
    conv_rows = "".join(f"<tr><td>{c.wa_id}</td><td>{c.customer_name}</td><td>{c.language}</td><td>{c.state}</td><td>{c.updated_at}</td></tr>" for c in conversations)
    lead_rows = "".join(f"<tr><td>{l.name}</td><td>{l.phone}</td><td>{l.email}</td><td>{l.need[:90]}</td><td>{l.created_at}</td></tr>" for l in leads)
    quote_rows = "".join(f"<tr><td>{q.customer_name}</td><td>{q.amount_cad}$</td><td>{q.need[:90]}</td><td>{q.created_at}</td></tr>" for q in quotes)
    return f"""
    <!doctype html><html lang="fr"><head><meta charset="utf-8"><title>ShellBot Dashboard</title>
    <style>
    body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f6f7fb;color:#111827}}
    header{{background:#101828;color:white;padding:18px 28px}} main{{padding:24px;max-width:1200px;margin:auto}}
    section{{margin:0 0 24px}} h2{{font-size:18px}} table{{width:100%;border-collapse:collapse;background:white;border:1px solid #e5e7eb}}
    th,td{{text-align:left;padding:10px;border-bottom:1px solid #eef0f4;font-size:14px;vertical-align:top}} th{{background:#f9fafb}}
    a{{color:#0f766e}} .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}
    @media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
    </style></head><body><header><h1>ShellBot</h1><p>Assistant WhatsApp IA pour PME canadiennes</p></header><main>
    <section><h2>Tenants</h2><table><tr><th>Business</th><th>Slug</th><th>Phone ID Meta</th><th>Status</th></tr>{tenant_rows}</table></section>
    <div class="grid">
    <section><h2>Conversations</h2><table><tr><th>WhatsApp</th><th>Nom</th><th>Langue</th><th>Etat</th><th>MAJ</th></tr>{conv_rows}</table></section>
    <section><h2>Prospects</h2><p><a href="/exports/leads.csv">Exporter CSV</a></p><table><tr><th>Nom</th><th>Tel</th><th>Email</th><th>Besoin</th><th>Date</th></tr>{lead_rows}</table></section>
    </div>
    <section><h2>Devis</h2><p><a href="/exports/quotes.csv">Exporter CSV</a></p><table><tr><th>Client</th><th>Montant</th><th>Besoin</th><th>Date</th></tr>{quote_rows}</table></section>
    </main></body></html>
    """

