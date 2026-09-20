from __future__ import annotations
import os

SERVER_WS_URL      = os.getenv("SERVER_WS_URL",   "ws://localhost:8002/ws/agent")
AGENT_TOKEN        = os.getenv("AGENT_TOKEN",      "")
DISCOVERY_TIMEOUT  = int(os.getenv("DISCOVERY_TIMEOUT",  10))
STATUS_INTERVAL    = int(os.getenv("STATUS_INTERVAL",     5))
RECONNECT_DELAY    = int(os.getenv("RECONNECT_DELAY",     5))
LOG_LEVEL          = os.getenv("LOG_LEVEL",        "INFO")
