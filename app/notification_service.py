from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime

from app.models import Notification, NotificationType

MAX_NOTIFICATIONS = 200


class NotificationService:
    def __init__(self) -> None:
        self._notifications: deque[Notification] = deque(maxlen=MAX_NOTIFICATIONS)
        self._lock = threading.Lock()

    def add(
        self,
        message: str,
        type: NotificationType = NotificationType.INFO,
        device_id: str | None = None,
    ) -> Notification:
        n = Notification(
            id=str(uuid.uuid4()),
            type=type,
            message=message,
            device_id=device_id,
            read=False,
            timestamp=datetime.now(),
        )
        with self._lock:
            self._notifications.appendleft(n)
        return n

    def get_all(self, unread_only: bool = False) -> list[Notification]:
        with self._lock:
            items = list(self._notifications)
        if unread_only:
            items = [n for n in items if not n.read]
        return items

    def mark_read(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    n.read = True
                    return True
        return False

    def mark_all_read(self) -> None:
        with self._lock:
            for n in self._notifications:
                n.read = True

    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)
