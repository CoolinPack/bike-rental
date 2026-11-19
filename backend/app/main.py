import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bot.bot import (
    delete_webhook,
    get_bot,
    get_dispatcher,
    shutdown_bot,
    configure_park_bot,
    feed_park_update,
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

    # Подключаем отдельные Telegram-боты всех парков, у которых сохранён токен.
    if settings.use_webhook and settings.webhook_url:
        from app.database import get_pool
        async with get_pool().acquire() as conn:
            park_bots = await conn.fetch(
                "SELECT id, bot_token FROM parks WHERE bot_token IS NOT NULL AND bot_token <> '' AND is_active = TRUE"
            )
        for park in park_bots:
            try:
                await configure_park_bot(int(park["id"]), park["bot_token"], settings.webhook_url)
                logger.info("Tenant bot webhook configured for park %s", park["id"])
            except Exception:
                logger.exception("Failed to configure Telegram bot for park %s", park["id"])

    # Старый общий бот оставлен для обратной совместимости.
    if not settings.use_webhook:
        try:
            await delete_webhook()
        except Exception:
            logger.exception("Failed to delete legacy webhook")

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


@app.post("/tg/webhook/{park_id}")
async def tg_park_webhook(park_id: int, request: Request):
    """Webhook отдельного Telegram-бота арендатора."""
    from app.database import get_pool
    async with get_pool().acquire() as conn:
        token = await conn.fetchval(
            "SELECT bot_token FROM parks WHERE id = $1 AND is_active = TRUE", park_id
        )
    if not token:
        return {"ok": False, "detail": "Park bot not configured"}
    await feed_park_update(park_id, token, await request.json())
    return {"ok": True}


@app.post("/tg/webhook")
async def tg_webhook_legacy(request: Request):
    """Webhook общего платформенного бота (совместимость со старой конфигурацией)."""
    from aiogram.types import Update
    data = await request.json()
    update = Update.model_validate(data, context={"bot": get_bot()})
    await get_dispatcher().feed_update(get_bot(), update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}