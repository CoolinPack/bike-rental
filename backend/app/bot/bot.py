import logging
from urllib.parse import urlencode

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    WebAppInfo,
)

from app.config import settings

logger = logging.getLogger(__name__)
_DEFAULT_BOT: Bot | None = None
_dispatcher: Dispatcher | None = None
_park_bots: dict[int, Bot] = {}
_bot_park_ids: dict[int, int] = {}


def _new_bot(token: str) -> Bot:
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def get_bot() -> Bot:
    """Основной бот платформы (для совместимости со старым кодом)."""
    global _DEFAULT_BOT
    if _DEFAULT_BOT is None:
        _DEFAULT_BOT = _new_bot(settings.bot_token)
    return _DEFAULT_BOT


def get_park_bot(park_id: int, token: str) -> Bot:
    """Возвращает отдельный экземпляр Telegram-бота конкретного парка."""
    current = _park_bots.get(park_id)
    if current is not None:
        # При смене токена заменяем экземпляр.
        if current.token == token:
            return current
    _park_bots[park_id] = _new_bot(token)
    return _park_bots[park_id]


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher()
        _register_handlers(_dispatcher)
    return _dispatcher


def _webapp_url(park_id: int) -> str:
    base = settings.webapp_url.rstrip("/")
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode({'startapp': f'park_{park_id}'})}"


def _register_handlers(dp: Dispatcher) -> None:
    from aiogram.filters import CommandStart
    from aiogram.types import Message

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        # /start park_123 и обычный /start обрабатываются одним ботом парка.
        park_id = _bot_park_ids.get(message.bot.id, 0)
        url = _webapp_url(park_id) if park_id else settings.webapp_url
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=url))
        ]])
        await message.answer(
            "Привет! Открой приложение, чтобы посмотреть байки и забронировать.",
            reply_markup=keyboard,
        )


async def configure_park_bot(park_id: int, token: str, webhook_url: str | None = None) -> dict:
    """Проверяет токен и включает Web App-кнопки для бота парка."""
    bot = _new_bot(token)
    try:
        me = await bot.get_me()
        # В меню Telegram Web App URL должен быть публичным HTTPS URL.
        app_url = _webapp_url(park_id)
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Открыть приложение", web_app=WebAppInfo(url=app_url))
        )
        if webhook_url:
            await bot.set_webhook(
                url=f"{webhook_url.rstrip('/')}/{park_id}",
                drop_pending_updates=True,
                allowed_updates=["message"],
            )
        old = _park_bots.pop(park_id, None)
        if old is not None:
            await old.session.close()
        _park_bots[park_id] = bot
        _bot_park_ids[me.id] = park_id
        return {"id": me.id, "username": me.username}
    except Exception:
        await bot.session.close()
        raise


async def remove_park_bot(park_id: int) -> None:
    bot = _park_bots.pop(park_id, None)
    if bot is not None:
        _bot_park_ids.pop(bot.id, None)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        finally:
            await bot.session.close()


async def feed_park_update(park_id: int, token: str, update_data: dict) -> None:
    bot = get_park_bot(park_id, token)
    _bot_park_ids[bot.id] = park_id
    # Dispatcher использует один набор обработчиков, а bot остаётся tenant-specific.
    update = __import__("aiogram.types", fromlist=["Update"]).Update.model_validate(
        update_data, context={"bot": bot}
    )
    await get_dispatcher().feed_update(bot, update)


async def setup_webhook(webhook_url: str) -> None:
    bot = get_bot()
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


async def delete_webhook() -> None:
    await get_bot().delete_webhook(drop_pending_updates=True)


async def shutdown_bot() -> None:
    global _DEFAULT_BOT
    if _DEFAULT_BOT is not None:
        await _DEFAULT_BOT.session.close()
        _DEFAULT_BOT = None
    for bot in list(_park_bots.values()):
        await bot.session.close()
    _park_bots.clear()
