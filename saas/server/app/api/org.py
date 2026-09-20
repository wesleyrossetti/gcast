from __future__ import annotations

import logging
import secrets
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_org_admin
from app.config import PUBLIC_BASE_URL
from app.database import get_db
from app.email import send_invite_email
from app.models.db import (
    Agent,
    AgentStatusEvent,
    HistoryEntry,
    Invite,
    LoginAudit,
    Organization,
    User,
)
from app.models.schemas import (
    InviteCreate,
    InviteOut,
    LoginAuditOut,
    OrgOut,
    OrgUpdate,
    UserOut,
    UserRoleUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/org", tags=["org"])


# ── Organization ──────────────────────────────────────────────────────────────

@router.get("", response_model=OrgOut)
async def get_org(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one()
    return org


@router.patch("", response_model=OrgOut)
async def update_org(
    req: OrgUpdate,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one()
    org.name = req.name
    await db.commit()
    await db.refresh(org)
    return org


# ── Users ─────────────────────────────────────────────────────────────────────

async def _count_owners(db: AsyncSession, org_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(User.org_id == org_id, User.role == "owner")
    )
    return result.scalar_one()


@router.get("/users", response_model=list[UserOut])
async def list_users(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.org_id == user.org_id))
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user_role(
    user_id: str,
    req: UserRoleUpdate,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(400, "Você não pode alterar seu próprio papel")

    result = await db.execute(select(User).where(User.id == user_id, User.org_id == user.org_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Usuário não encontrado")

    if target.role == "owner" and req.role != "owner" and await _count_owners(db, user.org_id) <= 1:
        raise HTTPException(400, "A organização precisa de pelo menos um owner")

    target.role = req.role
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(400, "Você não pode remover a si mesmo")

    result = await db.execute(select(User).where(User.id == user_id, User.org_id == user.org_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Usuário não encontrado")

    if target.role == "owner" and await _count_owners(db, user.org_id) <= 1:
        raise HTTPException(400, "A organização precisa de pelo menos um owner")

    await db.delete(target)
    await db.commit()
    return {"status": "ok"}


# ── Invites ───────────────────────────────────────────────────────────────────

@router.get("/invites", response_model=list[InviteOut])
async def list_invites(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invite).where(
            Invite.org_id == user.org_id,
            Invite.accepted_at.is_(None),
            Invite.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalars().all()


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    req: InviteCreate,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    existing_user = await db.execute(select(User).where(User.email == req.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(400, "Já existe um usuário com esse e-mail")

    existing_invite = await db.execute(
        select(Invite).where(
            Invite.org_id == user.org_id,
            Invite.email == req.email,
            Invite.accepted_at.is_(None),
            Invite.expires_at > datetime.now(timezone.utc),
        )
    )
    if existing_invite.scalar_one_or_none():
        raise HTTPException(400, "Já existe um convite pendente para esse e-mail")

    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one()

    raw_token = secrets.token_urlsafe(32)
    invite = Invite(
        org_id=user.org_id,
        email=req.email,
        role=req.role,
        token_hash=Invite.hash_token(raw_token),
        invited_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    base = PUBLIC_BASE_URL or ""
    invite_link = f"{base}/accept-invite?token={raw_token}"
    send_invite_email(req.email, org.name, req.role, invite_link)

    return invite


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: str,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invite).where(Invite.id == invite_id, Invite.org_id == user.org_id)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, "Convite não encontrado")
    await db.delete(invite)
    await db.commit()
    return {"status": "ok"}


# ── Auditoria de acesso ───────────────────────────────────────────────────────

@router.get("/audit", response_model=list[LoginAuditOut])
async def list_audit(
    limit: int = 100,
    user: User = Depends(require_org_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginAudit)
        .where(LoginAudit.org_id == user.org_id)
        .order_by(LoginAudit.created_at.desc())
        .limit(min(limit, 500))
    )
    return result.scalars().all()


# ── Estatísticas agregadas (gráficos) ───────────────────────────────────────────

def _accumulate_seconds(bucket: dict[date, float], start: datetime, end: datetime) -> None:
    """Distribui o intervalo [start, end) entre os dias que ele cobre."""
    cur = start
    while cur < end:
        day = cur.date()
        day_end = datetime.combine(day, time.max, tzinfo=cur.tzinfo)
        chunk_end = min(end, day_end)
        bucket[day] += (chunk_end - cur).total_seconds()
        cur = chunk_end + timedelta(microseconds=1)


@router.get("/stats")
async def get_stats(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=min(days, 365))

    logins_result = await db.execute(
        select(func.date(LoginAudit.created_at), func.count())
        .where(LoginAudit.org_id == user.org_id, LoginAudit.success.is_(True), LoginAudit.created_at >= since)
        .group_by(func.date(LoginAudit.created_at))
        .order_by(func.date(LoginAudit.created_at))
    )
    logins_by_day = [{"date": str(d), "count": c} for d, c in logins_result.all()]

    actions_result = await db.execute(
        select(func.date(HistoryEntry.timestamp), func.count())
        .where(HistoryEntry.org_id == user.org_id, HistoryEntry.timestamp >= since)
        .group_by(func.date(HistoryEntry.timestamp))
        .order_by(func.date(HistoryEntry.timestamp))
    )
    actions_by_day = [{"date": str(d), "count": c} for d, c in actions_result.all()]

    top_devices_result = await db.execute(
        select(HistoryEntry.device_name, func.count())
        .where(HistoryEntry.org_id == user.org_id, HistoryEntry.timestamp >= since, HistoryEntry.device_name.is_not(None))
        .group_by(HistoryEntry.device_name)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_devices = [{"device_name": n, "count": c} for n, c in top_devices_result.all()]

    events_result = await db.execute(
        select(AgentStatusEvent, Agent.name)
        .join(Agent, Agent.id == AgentStatusEvent.agent_id)
        .where(AgentStatusEvent.org_id == user.org_id, AgentStatusEvent.created_at >= since)
        .order_by(AgentStatusEvent.agent_id, AgentStatusEvent.created_at)
    )
    by_agent: dict[str, list] = defaultdict(list)
    names: dict[str, str] = {}
    for ev, name in events_result.all():
        by_agent[ev.agent_id].append(ev)
        names[ev.agent_id] = name

    now = datetime.now(timezone.utc)
    agent_uptime_by_day = []
    for agent_id, events in by_agent.items():
        day_seconds: dict[date, float] = defaultdict(float)
        prev_time = events[0].created_at
        prev_status = "offline"
        for ev in events:
            if prev_status == "online":
                _accumulate_seconds(day_seconds, prev_time, ev.created_at)
            prev_time = ev.created_at
            prev_status = ev.status
        if prev_status == "online":
            _accumulate_seconds(day_seconds, prev_time, now)
        for day, seconds in sorted(day_seconds.items()):
            agent_uptime_by_day.append({
                "date": str(day),
                "agent_name": names[agent_id],
                "online_pct": round(min(seconds / 86400, 1.0), 2),
            })

    return {
        "logins_by_day": logins_by_day,
        "actions_by_day": actions_by_day,
        "top_devices": top_devices,
        "agent_uptime_by_day": agent_uptime_by_day,
    }
