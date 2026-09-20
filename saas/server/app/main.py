from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.agents  import router as agents_router
from app.api.control import router as control_router
from app.api.devices import router as devices_router
from app.api.history import router as history_router
from app.api.media   import router as media_router
from app.auth.deps   import require_page_auth
from app.auth.router import router as auth_router
from app.config      import LOG_LEVEL
from app.database    import init_db
from app.models.db   import User
from app.ws.router   import router as ws_router
from fastapi         import Depends

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

BASE_DIR  = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Chromecast Manager SaaS",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

for r in (auth_router, agents_router, devices_router, media_router, control_router, history_router, ws_router):
    app.include_router(r)


# ── HTML pages ────────────────────────────────────────────────────────────────

@app.get("/login",    response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html",    {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(require_page_auth)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, user: User = Depends(require_page_auth)):
    return templates.TemplateResponse("agents.html", {"request": request, "user": user})

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, user: User = Depends(require_page_auth)):
    return templates.TemplateResponse("history.html", {"request": request, "user": user})
