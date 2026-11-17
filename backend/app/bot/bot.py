import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dispatcher: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher()
        _register_handlers(_dispatcher)
    return _dispatcher


def _register_handlers(dp: Dispatcher) -> None:
    from aiogram.filters import CommandStart
    from aiogram.types import Message

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        # Deep link: /start park_5 — обрабатываем на фронте; бот лишь приветствует
        text = (
            "Привет! Открой приложение, чтобы посмотреть байки и забронировать.\n\n"
            "Если открыл из парка — ты сразу попадёшь в каталог этого парка."
        )
        await message.answer(text)


async def shutdown_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


async def setup_webhook(webhook_url: str) -> None:
    bot = get_bot()
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


async def delete_webhook() -> None:
    bot = get_bot()
    await bot.delete_webhook(drop_pending_updates=True)