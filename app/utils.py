from __future__ import annotations

from fastapi import Request

from app.cast_service import CastService
from app.history_service import HistoryService
from app.notification_service import NotificationService
from app.scheduler_service import SchedulerService


def get_cast_service(request: Request) -> CastService:
    return request.app.state.cast_service


def get_history_service(request: Request) -> HistoryService:
    return request.app.state.history_service


def get_notif_service(request: Request) -> NotificationService:
    return request.app.state.notif_service


def get_scheduler_service(request: Request) -> SchedulerService:
    return request.app.state.scheduler_service
