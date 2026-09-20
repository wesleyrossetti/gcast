import os

API_PORT = int(os.getenv("API_PORT", 8001))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DISCOVERY_TIMEOUT = int(os.getenv("DISCOVERY_TIMEOUT", 10))
HISTORY_MAX_SIZE = int(os.getenv("HISTORY_MAX_SIZE", 1000))
HISTORY_FILE = os.getenv("HISTORY_FILE", "data/history.json")
SCHEDULE_FILE = os.getenv("SCHEDULE_FILE", "data/schedules.json")
KNOWN_HOSTS_FILE = os.getenv("KNOWN_HOSTS_FILE", "data/known_hosts.json")
STATUS_POLL_INTERVAL = int(os.getenv("STATUS_POLL_INTERVAL", 5))
