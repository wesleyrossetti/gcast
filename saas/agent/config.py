from __future__ import annotations
import os

SERVER_WS_URL      = os.getenv("SERVER_WS_URL",   "ws://localhost:8002/ws/agent")
AGENT_TOKEN        = os.getenv("AGENT_TOKEN",      "")
# IPs ou sub-redes (CIDR) separados por vírgula — ex: "10.25.25.138,10.0.0.0/24".
# Útil quando mDNS/multicast não funciona na rede onde o agente roda (ex: WSL2,
# Docker Desktop, VPNs, redes segmentadas).
KNOWN_HOSTS_RAW    = os.getenv("KNOWN_HOSTS",      "")
KNOWN_HOSTS        = [h.strip() for h in KNOWN_HOSTS_RAW.split(",") if h.strip()]
DISCOVERY_TIMEOUT  = int(os.getenv("DISCOVERY_TIMEOUT",  10))
STATUS_INTERVAL    = int(os.getenv("STATUS_INTERVAL",     5))
RECONNECT_DELAY    = int(os.getenv("RECONNECT_DELAY",     5))
LOG_LEVEL          = os.getenv("LOG_LEVEL",        "INFO")
