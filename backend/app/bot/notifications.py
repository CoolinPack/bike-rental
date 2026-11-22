import logging

from aiogram.exceptions import TelegramAPIError

from app.bot.bot import get_bot, get_park_bot

logger = logging.getLogger(__name__)


async def _send(
    chat_id: int, text: str, park_id: int | None = None, bot_token: str | None = None
) -> bool:
    try:
        bot = get_park_bot(park_id, bot_token) if park_id and bot_token else get_bot()
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramAPIError as e:
        logger.warning("Failed to send TG message to %s: %s", chat_id, e)
        return False


async def notify_owner_new_request(
    owner_telegram_id: int,
    park_name: str,
    booking_id: int,
    client_name: str | None,
    client_phone: str | None,
    client_username: str | None,
    bike_model: str,
    plate_number: str,
    start_date,
    end_date,
    total_price,
    deposit_comment: str | None,
    park_id: int | None = None,
    bot_token: str | None = None,
) -> None:
    username = f"@{client_username}" if client_username else "—"
    text = (
        f"🔔 <b>Новая заявка #{booking_id}</b>\n"
        f"Парк: <b>{park_name}</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
        f"📅 {start_date} → {end_date}\n"
        f"💰 Итого: <b>{total_price} VND</b>\n\n"
        f"👤 {client_name or '—'}\n"
        f"📞 {client_phone or '—'}\n"
        f"💬 {username}\n"
        f"📝 Залог: {deposit_comment or '—'}\n\n"
        f"Открой Mini App → Заявки, чтобы принять или отклонить."
    )
    await _send(owner_telegram_id, text, park_id, bot_token)


async def notify_client_accepted(
    client_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    start_date,
    end_date,
    total_price,
    park_id: int | None = None,
    bot_token: str | None = None,
) -> None:
    text = (
        f"✅ <b>Заявка #{booking_id} принята</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
        f"📅 {start_date} → {end_date}\n"
        f"💰 Итого: <b>{total_price} VND</b>\n\n"
        f"Хорошей поездки! Не забудь вернуть байк вовремя."
    )
    await _send(client_telegram_id, text, park_id, bot_token)


async def notify_client_rejected(
    client_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    reason: str | None,
    park_id: int | None = None,
    bot_token: str | None = None,
) -> None:
    text = (
        f"❌ <b>Заявка #{booking_id} отклонена</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
    )
    if reason:
        text += f"\nПричина: {reason}\n"
    text += "\nТы можешь выбрать другой байк или другие даты."
    await _send(client_telegram_id, text, park_id, bot_token)


async def notify_reminder(
    client_telegram_id: int,
    owner_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    end_date,
    days_left: int,
    client_name: str | None = None,
    park_id: int | None = None,
    bot_token: str | None = None,
) -> bool:
    when = "через 3 дня" if days_left == 3 else "завтра"
    owner_link = f"tg://user?id={owner_telegram_id}"
    client_text = (
        f"⏰ <b>Напоминание об окончании аренды</b>\n\n"
        f"Добрый день! Байк <b>{bike_model} ({plate_number})</b> "
        f"необходимо вернуть {when}, дата окончания — <b>{end_date}</b>.\n\n"
        f"Если хотите продлить аренду, свяжитесь с владельцем парка: "
        f'<a href="{owner_link}">написать владельцу</a>.'
    )
    owner_text = (
        f"⏰ <b>Окончание аренды {when}</b>\n\n"
        f"Байк: <b>{bike_model} ({plate_number})</b>\n"
        f"Клиент: <b>{client_name or '—'}</b> (ID {client_telegram_id})\n"
        f"Дата окончания: <b>{end_date}</b>\n"
        f"Заявка #{booking_id}."
    )
    client_sent = await _send(client_telegram_id, client_text, park_id, bot_token)
    owner_sent = await _send(owner_telegram_id, owner_text, park_id, bot_token)
    return bool(client_sent and owner_sent)
