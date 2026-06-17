from datetime import datetime

from sqlalchemy.orm import Session

from .models import Conversation, Lead, Message, Quote, Tenant
from .services.ai import generate_ai_reply
from .services.emailer import notify_human
from .services.meta_whatsapp import MetaWhatsAppClient
from .services.onboarding import apply_onboarding_update, onboarding_reply
from .services.quote import estimate_quote
from .utils import detect_language


QUOTE_WORDS = {"devis", "quote", "estimate", "prix", "tarif"}
APPOINTMENT_WORDS = {"rendez-vous", "rdv", "appointment", "meeting", "calendly"}
HUMAN_WORDS = {"humain", "human", "agent", "personne", "representative"}
LEAD_WORDS = {"email", "courriel", "contact", "prospect", "telephone", "phone"}


class ShellBot:
    def __init__(self, db: Session):
        self.db = db
        self.meta = MetaWhatsAppClient()

    def handle_message(self, tenant: Tenant, wa_id: str, text: str, customer_name: str = "") -> str:
        conversation = self._conversation(tenant, wa_id, customer_name, text)
        self.db.add(Message(conversation_id=conversation.id, direction="in", text=text))

        reply = self._build_reply(tenant, conversation, text)
        self.db.add(Message(conversation_id=conversation.id, direction="out", text=reply))
        conversation.updated_at = datetime.utcnow()
        self.db.commit()
        self.meta.send_text(tenant.phone_number_id, wa_id, reply)
        return reply

    def _conversation(self, tenant: Tenant, wa_id: str, customer_name: str, text: str) -> Conversation:
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.tenant_id == tenant.id, Conversation.wa_id == wa_id)
            .first()
        )
        language = detect_language(text, tenant.language_default)
        if conversation:
            conversation.language = language or conversation.language
            if customer_name and not conversation.customer_name:
                conversation.customer_name = customer_name
            self.db.commit()
            return conversation

        conversation = Conversation(
            tenant_id=tenant.id,
            wa_id=wa_id,
            customer_name=customer_name,
            language=language,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def _build_reply(self, tenant: Tenant, conversation: Conversation, text: str) -> str:
        language = conversation.language or tenant.language_default
        lower = (text or "").lower()

        onboarding = onboarding_reply(text, language)
        if onboarding:
            return onboarding

        onboarding_update = apply_onboarding_update(self.db, tenant, text, language)
        if onboarding_update:
            return onboarding_update

        if any(word in lower for word in HUMAN_WORDS):
            conversation.needs_human = True
            self.db.commit()
            notify_human(
                tenant.owner_email,
                f"ShellBot fallback - {tenant.business_name}",
                f"Client: {conversation.customer_name or conversation.wa_id}\nMessage: {text}",
            )
            return (
                "Je transfere a un humain. Quelqu'un vous repondra bientot."
                if language == "fr"
                else "I am transferring you to a human. Someone will reply soon."
            )

        if any(word in lower for word in QUOTE_WORDS):
            amount, quote_text = estimate_quote(tenant, text, language)
            quote = Quote(
                tenant_id=tenant.id,
                conversation_id=conversation.id,
                customer_name=conversation.customer_name,
                need=text,
                amount_cad=amount,
                quote_text=quote_text,
            )
            self.db.add(quote)
            return quote_text

        if any(word in lower for word in APPOINTMENT_WORDS):
            if tenant.calendly_url:
                return (
                    f"Vous pouvez prendre rendez-vous ici: {tenant.calendly_url}"
                    if language == "fr"
                    else f"You can book an appointment here: {tenant.calendly_url}"
                )
            return (
                "Proposez deux creneaux, et nous confirmerons le rendez-vous."
                if language == "fr"
                else "Send two preferred time slots, and we will confirm the appointment."
            )

        if any(word in lower for word in LEAD_WORDS):
            lead = Lead(
                tenant_id=tenant.id,
                conversation_id=conversation.id,
                name=conversation.customer_name,
                phone=conversation.wa_id,
                need=text,
                language=language,
            )
            self.db.add(lead)
            return (
                "Merci. J'ai note votre demande. Pouvez-vous ajouter votre email et votre nom complet ?"
                if language == "fr"
                else "Thanks. I saved your request. Could you add your email and full name?"
            )

        history = [m.text for m in conversation.messages[-8:]] if conversation.messages else []
        return generate_ai_reply(tenant, history, text, language)
