import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bot.bot import (
    delete_webhook,
    get_bot,
    get_dispatcher,
    setup_webhook,
    shutdown_bot,
)
from app.bot.reminders import reminder_worker
from app.config import settings
from app.database import close_pool, init_pool
from app.routers import auth as auth_router
from app.routers import client as client_router
from app.routers import owner as owner_router
from app.routers import super_admin as super_admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()

    # Бот
    if settings.use_webhook and settings.webhook_url:
        await setup_webhook(settings.webhook_url)
        logger.info("Webhook set to %s", settings.webhook_url)
    else:
        try:
            await delete_webhook()
        except Exception:
            logger.exception("Failed to delete webhook (ok if none existed)")

    # Фоновые напоминания
    reminder_task = asyncio.create_task(reminder_worker())

    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await shutdown_bot()
        await close_pool()


app = FastAPI(title="Bike Rental API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(super_admin_router.router)
app.include_router(owner_router.router)
app.include_router(client_router.router)

uploads_path = Path(settings.upload_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    """Вебхук Telegram. Используется только при USE_WEBHOOK=true."""
    data = await request.json()
    update = Update.model_validate(data, context={"bot": get_bot()})
    await get_dispatcher().feed_update(get_bot(), update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}