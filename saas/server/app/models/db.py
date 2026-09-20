from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ── Organization ──────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id         = Column(String, primary_key=True, default=_uuid)
    name       = Column(String, nullable=False)
    slug       = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=_now)

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
    created_at    = Column(DateTime, default=_now)

    org = relationship("Organization", back_populates="users")


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id         = Column(String, primary_key=True, default=_uuid)
    name       = Column(String, nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    org_id     = Column(String, ForeignKey("organizations.id"), nullable=False)
    last_seen  = Column(DateTime)
    created_at = Column(DateTime, default=_now)

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
    updated_at   = Column(DateTime, default=_now)

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
    timestamp   = Column(DateTime, default=_now)


# ── Schedule ──────────────────────────────────────────────────────────────────

class Schedule(Base):
    __tablename__ = "schedules"

    id           = Column(String, primary_key=True, default=_uuid)
    org_id       = Column(String, ForeignKey("organizations.id"), nullable=False)
    device_uuid  = Column(String, nullable=False)
    action       = Column(String, nullable=False)
    run_at       = Column(DateTime, nullable=False)
    recurrence   = Column(String, default="once")   # once | daily | weekly
    details_json = Column(Text, default="{}")
    enabled      = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=_now)
    last_run     = Column(DateTime)
