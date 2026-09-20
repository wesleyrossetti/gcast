from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    # datetime "aware" (com tzinfo=UTC) — sem isso, o front-end interpreta o
    # horário como se já fosse local e some com a conversão de fuso.
    return datetime.now(timezone.utc)


# ── Organization ──────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id         = Column(String, primary_key=True, default=_uuid)
    name       = Column(String, nullable=False)
    slug       = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    users   = relationship("User",   back_populates="org",   lazy="select")
    agents  = relationship("Agent",  back_populates="org",   lazy="select")
    devices = relationship("Device", back_populates="org",   lazy="select")


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=_uuid)
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name          = Column(String)
    org_id        = Column(String, ForeignKey("organizations.id"), nullable=False)
    role          = Column(String, default="owner")   # owner | admin | member
    created_at    = Column(DateTime(timezone=True), default=_now)

    org = relationship("Organization", back_populates="users")


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id         = Column(String, primary_key=True, default=_uuid)
    name       = Column(String, nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    org_id     = Column(String, ForeignKey("organizations.id"), nullable=False)
    last_seen  = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)

    org     = relationship("Organization", back_populates="agents")
    # delete-orphan: ao apagar um agente, os devices associados vão junto (sem
    # isso, o SQLAlchemy tenta só desassociar via agent_id=NULL, o que quebra
    # porque a coluna é NOT NULL). Devices reaparecem sozinhos quando um agente
    # volta a reportar aquele device_uuid.
    devices = relationship("Device", back_populates="agent", lazy="select", cascade="all, delete-orphan")

    @staticmethod
    def hash_token(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()


# ── Device ────────────────────────────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id           = Column(String, primary_key=True, default=_uuid)
    device_uuid  = Column(String, nullable=False)   # from pychromecast
    friendly_name = Column(String)
    host         = Column(String)
    port         = Column(Integer)
    model_name   = Column(String)
    agent_id     = Column(String, ForeignKey("agents.id"), nullable=False)
    org_id       = Column(String, ForeignKey("organizations.id"), nullable=False)
    status_json  = Column(Text)                     # latest status snapshot
    updated_at   = Column(DateTime(timezone=True), default=_now)

    org   = relationship("Organization", back_populates="devices")
    agent = relationship("Agent", back_populates="devices")


# ── History ───────────────────────────────────────────────────────────────────

class HistoryEntry(Base):
    __tablename__ = "history_entries"

    id          = Column(String, primary_key=True, default=_uuid)
    org_id      = Column(String, ForeignKey("organizations.id"), nullable=False)
    device_uuid = Column(String)
    device_name = Column(String)
    action      = Column(String, nullable=False)
    details_json = Column(Text, default="{}")
    success     = Column(Boolean, default=True)
    error       = Column(String)
    timestamp   = Column(DateTime(timezone=True), default=_now)


# ── Invite ────────────────────────────────────────────────────────────────────

class Invite(Base):
    __tablename__ = "invites"

    id          = Column(String, primary_key=True, default=_uuid)
    org_id      = Column(String, ForeignKey("organizations.id"), nullable=False)
    email       = Column(String, nullable=False)
    role        = Column(String, default="member")   # owner | admin | member
    token_hash  = Column(String, unique=True, nullable=False)
    invited_by  = Column(String, ForeignKey("users.id"))
    accepted_at = Column(DateTime(timezone=True))
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), default=_now)

    org = relationship("Organization")

    @staticmethod
    def hash_token(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()


# ── Login audit ───────────────────────────────────────────────────────────────

class LoginAudit(Base):
    __tablename__ = "login_audit"

    id              = Column(String, primary_key=True, default=_uuid)
    # org_id/user_id ficam nulos quando o e-mail tentado não corresponde a
    # nenhum usuário — não tem organização pra associar a tentativa.
    org_id          = Column(String, ForeignKey("organizations.id"))
    user_id         = Column(String, ForeignKey("users.id"))
    email_attempted = Column(String, nullable=False)
    success         = Column(Boolean, nullable=False)
    reason          = Column(String)   # "ok" | "senha incorreta" | "e-mail não encontrado"
    ip_address      = Column(String)
    user_agent      = Column(String)
    created_at      = Column(DateTime(timezone=True), default=_now)


# ── Agent status events (histórico de online/offline) ──────────────────────────

class AgentStatusEvent(Base):
    __tablename__ = "agent_status_events"

    id         = Column(String, primary_key=True, default=_uuid)
    agent_id   = Column(String, ForeignKey("agents.id"), nullable=False)
    org_id     = Column(String, ForeignKey("organizations.id"), nullable=False)
    status     = Column(String, nullable=False)   # "online" | "offline"
    created_at = Column(DateTime(timezone=True), default=_now)


# ── Schedule ──────────────────────────────────────────────────────────────────

class Schedule(Base):
    __tablename__ = "schedules"

    id           = Column(String, primary_key=True, default=_uuid)
    org_id       = Column(String, ForeignKey("organizations.id"), nullable=False)
    device_uuid  = Column(String, nullable=False)
    action       = Column(String, nullable=False)
    run_at       = Column(DateTime(timezone=True), nullable=False)
    recurrence   = Column(String, default="once")   # once | daily | weekly
    details_json = Column(Text, default="{}")
    enabled      = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), default=_now)
    last_run     = Column(DateTime(timezone=True))
