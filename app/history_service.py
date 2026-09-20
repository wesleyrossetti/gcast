from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from collections import deque
from datetime import datetime
from typing import Any

from app.config import HISTORY_FILE, HISTORY_MAX_SIZE
from app.models import ActionType, HistoryEntry

logger = logging.getLogger(__name__)


class HistoryService:
    def __init__(self) -> None:
        self._entries: deque[HistoryEntry] = deque(maxlen=HISTORY_MAX_SIZE)
        self._lock = threading.Lock()
        self._load()

    def log(
        self,
        device_id: str,
        action: ActionType,
        device_name: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> HistoryEntry:
        entry = HistoryEntry(
            id=str(uuid.uuid4()),
            device_id=device_id,
            device_name=device_name,
            action=action,
            details=details or {},
            success=success,
            error=error,
            timestamp=datetime.now(),
        )
        with self._lock:
            self._entries.appendleft(entry)
        self._persist()
        return entry

    def get_history(
        self,
        device_id: str | None = None,
        limit: int = 50,
    ) -> list[HistoryEntry]:
        with self._lock:
            entries = list(self._entries)
        if device_id:
            entries = [e for e in entries if e.device_id == device_id]
        return entries[:limit]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist(self) -> None:
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE) or ".", exist_ok=True)
            with self._lock:
                data = [e.model_dump(mode="json") for e in self._entries]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning("Could not persist history: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for item in reversed(data):
                self._entries.appendleft(HistoryEntry(**item))
            logger.info("Loaded %d history entries", len(self._entries))
        except Exception as exc:
            logger.warning("Could not load history: %s", exc)
