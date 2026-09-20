from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.service import generate_agent_token
from app.database import get_db
from app.models.db import Agent, User
from app.models.schemas import AgentCreate, AgentCreated, AgentOut
from app.ws.manager import manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.org_id == user.org_id))
    agents = result.scalars().all()
    out = []
    for a in agents:
        d = AgentOut.model_validate(a)
        d.is_online = manager.is_online(a.id)
        out.append(d)
    return out


@router.post("", response_model=AgentCreated)
async def create_agent(
    req: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = generate_agent_token()
    agent = Agent(
        name=req.name,
        token_hash=Agent.hash_token(token),
        org_id=user.org_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    out = AgentCreated(**AgentOut.model_validate(agent).model_dump(), token=token)
    return out


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == user.org_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agente não encontrado")
    await db.delete(agent)
    await db.commit()
    return {"status": "ok"}
