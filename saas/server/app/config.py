from __future__ import annotations
import os

DATABASE_URL   = os.getenv("DATABASE_URL",   "sqlite+aiosqlite:///./data/saas.db")
SECRET_KEY     = os.getenv("SECRET_KEY",     "CHANGE-ME-IN-PRODUCTION-use-openssl-rand")
ALGORITHM      = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
API_PORT       = int(os.getenv("API_PORT",   8002))
LOG_LEVEL      = os.getenv("LOG_LEVEL",      "INFO")

# URL pública do servidor, usada pra montar links de convite (ex: nos e-mails).
# Sem isso configurado, o backend não tem como saber seu próprio domínio.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# SMTP (envio de e-mail de convite) — todos opcionais. Sem SMTP_HOST, o envio
# cai num fallback que só loga o link do convite (útil antes de haver um
# provedor de e-mail real configurado).
SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", "no-reply@gcast.local")
