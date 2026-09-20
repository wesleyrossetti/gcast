from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import (
    create_access_token,
    hash_password,
    slugify,
    verify_password,
)
from app.database import get_db
from app.models.db import Invite, LoginAudit, Organization, User
from app.models.schemas import (
    AcceptInviteRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    org = Organization(name=req.org_name, slug=slugify(req.org_name))
    db.add(org)
    await db.flush()  # get org.id

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        org_id=org.id,
        role="owner",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.org_id)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not user:
        db.add(LoginAudit(
            email_attempted=req.email, success=False, reason="e-mail não encontrado",
            ip_address=ip, user_agent=ua,
        ))
        await db.commit()
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(req.password, user.password_hash):
        db.add(LoginAudit(
            org_id=user.org_id, user_id=user.id, email_attempted=req.email,
            success=False, reason="senha incorreta", ip_address=ip, user_agent=ua,
        ))
        await db.commit()
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    db.add(LoginAudit(
        org_id=user.org_id, user_id=user.id, email_attempted=req.email,
        success=True, reason="ok", ip_address=ip, user_agent=ua,
    ))
    await db.commit()

    token = create_access_token(user.id, user.org_id)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return TokenResponse(access_token=token)


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(req: AcceptInviteRequest, response: Response, db: AsyncSession = Depends(get_db)):
    token_hash = Invite.hash_token(req.token)
    result = await db.execute(select(Invite).where(Invite.token_hash == token_hash))
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Convite já foi utilizado")
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:  # SQLite não preserva tzinfo como o Postgres
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Convite expirado")

    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Já existe uma conta com esse e-mail")

    user = User(
        email=invite.email,
        password_hash=hash_password(req.password),
        name=req.name,
        org_id=invite.org_id,
        role=invite.role,
    )
    db.add(user)
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.org_id)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "ok"}
