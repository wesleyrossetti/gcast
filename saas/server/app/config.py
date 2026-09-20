from __future__ import annotations
import os

DATABASE_URL   = os.getenv("DATABASE_URL",   "sqlite+aiosqlite:///./data/saas.db")
SECRET_KEY     = os.getenv("SECRET_KEY",     "CHANGE-ME-IN-PRODUCTION-use-openssl-rand")
ALGORITHM      = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
API_PORT       = int(os.getenv("API_PORT",   8002))
LOG_LEVEL      = os.getenv("LOG_LEVEL",      "INFO")
