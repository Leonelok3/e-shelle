from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    business_name: Mapped[str] = mapped_column(String(180))
    phone_number_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(180), default="")
    human_phone: Mapped[str] = mapped_column(String(40), default="")
    timezone: Mapped[str] = mapped_column(String(80), default="America/Toronto")
    language_default: Mapped[str] = mapped_column(String(8), default="fr")
    calendly_url: Mapped[str] = mapped_column(String(300), default="")
    business_context: Mapped[str] = mapped_column(Text, default="")
    faq_json: Mapped[str] = mapped_column(Text, default="[]")
    services_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="tenant")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    wa_id: Mapped[str] = mapped_column(String(80), index=True)
    customer_name: Mapped[str] = mapped_column(String(160), default="")
    language: Mapped[str] = mapped_column(String(8), default="fr")
    state: Mapped[str] = mapped_column(String(40), default="open")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(12))
    text: Mapped[str] = mapped_column(Text)
    provider_message_id: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(180), default="")
    email: Mapped[str] = mapped_column(String(180), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    need: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(8), default="fr")
    status: Mapped[str] = mapped_column(String(40), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(180), default="")
    need: Mapped[str] = mapped_column(Text, default="")
    amount_cad: Mapped[int] = mapped_column(Integer, default=0)
    quote_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

