from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.config import SCHEDULE_FILE
from app.models import ActionType, RecurrenceType, ScheduleEntry, ScheduleRequest

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
        self._entries: dict[str, ScheduleEntry] = {}
        self._action_callback: Any = None
        self._load()

    def start(self, action_callback: Any) -> None:
        self._action_callback = action_callback
        self._scheduler.start()
        for entry in self._entries.values():
            if entry.enabled:
                self._register_job(entry)
        logger.info("SchedulerService started with %d jobs", len(self._entries))

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, req: ScheduleRequest) -> ScheduleEntry:
        entry = ScheduleEntry(
            id=str(uuid.uuid4()),
            device_id=req.device_id,
            action=req.action,
            run_at=req.run_at,
            recurrence=req.recurrence,
            details=req.details,
            enabled=True,
            created_at=datetime.now(),
        )
        self._entries[entry.id] = entry
        if self._action_callback:
            self._register_job(entry)
        self._persist()
        return entry

    def list_schedules(self) -> list[ScheduleEntry]:
        return list(self._entries.values())

    def delete(self, schedule_id: str) -> bool:
        if schedule_id not in self._entries:
            return False
        try:
            self._scheduler.remove_job(schedule_id)
        except Exception:
            pass
        del self._entries[schedule_id]
        self._persist()
        return True

    # ── Job registration ──────────────────────────────────────────────────────

    def _register_job(self, entry: ScheduleEntry) -> None:
        try:
            if entry.recurrence == RecurrenceType.ONCE:
                trigger = DateTrigger(run_date=entry.run_at)
            elif entry.recurrence == RecurrenceType.DAILY:
                trigger = CronTrigger(
                    hour=entry.run_at.hour,
                    minute=entry.run_at.minute,
                )
            else:  # WEEKLY
                trigger = CronTrigger(
                    day_of_week=entry.run_at.strftime("%a").lower()[:3],
                    hour=entry.run_at.hour,
                    minute=entry.run_at.minute,
                )

            self._scheduler.add_job(
                self._run_action,
                trigger=trigger,
                id=entry.id,
                args=[entry],
                replace_existing=True,
                misfire_grace_time=60,
            )
        except Exception as exc:
            logger.error("Could not register job %s: %s", entry.id, exc)

    def _run_action(self, entry: ScheduleEntry) -> None:
        logger.info(
            "Running scheduled action %s on device %s",
            entry.action,
            entry.device_id,
        )
        entry.last_run = datetime.now()
        if self._action_callback:
            self._action_callback(entry)
        if entry.recurrence == RecurrenceType.ONCE:
            entry.enabled = False
        self._persist()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist(self) -> None:
        try:
            os.makedirs(os.path.dirname(SCHEDULE_FILE) or ".", exist_ok=True)
            data = [e.model_dump(mode="json") for e in self._entries.values()]
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning("Could not persist schedules: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(SCHEDULE_FILE):
            return
        try:
            with open(SCHEDULE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                entry = ScheduleEntry(**item)
                self._entries[entry.id] = entry
            logger.info("Loaded %d schedules", len(self._entries))
        except Exception as exc:
            logger.warning("Could not load schedules: %s", exc)
