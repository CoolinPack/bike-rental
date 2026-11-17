import logging

from aiogram.exceptions import TelegramAPIError

from app.bot.bot import get_bot

logger = logging.getLogger(__name__)


async def _send(chat_id: int, text: str) -> None:
    try:
        await get_bot().send_message(chat_id=chat_id, text=text)
    except TelegramAPIError as e:
        logger.warning("Failed to send TG message to %s: %s", chat_id, e)


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
) -> None:
    username = f"@{client_username}" if client_username else "—"
    text = (
        f"🔔 <b>Новая заявка #{booking_id}</b>\n"
        f"Парк: <b>{park_name}</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
        f"📅 {start_date} → {end_date}\n"
        f"💰 Итого: <b>{total_price} $</b>\n\n"
        f"👤 {client_name or '—'}\n"
        f"📞 {client_phone or '—'}\n"
        f"💬 {username}\n"
        f"📝 Залог: {deposit_comment or '—'}\n\n"
        f"Открой Mini App → Заявки, чтобы принять или отклонить."
    )
    await _send(owner_telegram_id, text)


async def notify_client_accepted(
    client_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    start_date,
    end_date,
    total_price,
) -> None:
    text = (
        f"✅ <b>Заявка #{booking_id} принята</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
        f"📅 {start_date} → {end_date}\n"
        f"💰 Итого: <b>{total_price} $</b>\n\n"
        f"Хорошей поездки! Не забудь вернуть байк вовремя."
    )
    await _send(client_telegram_id, text)


async def notify_client_rejected(
    client_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    reason: str | None,
) -> None:
    text = (
        f"❌ <b>Заявка #{booking_id} отклонена</b>\n\n"
        f"🏍 {bike_model} ({plate_number})\n"
    )
    if reason:
        text += f"\nПричина: {reason}\n"
    text += "\nТы можешь выбрать другой байк или другие даты."
    await _send(client_telegram_id, text)


async def notify_reminder(
    client_telegram_id: int,
    owner_telegram_id: int,
    booking_id: int,
    bike_model: str,
    plate_number: str,
    end_date,
) -> None:
    client_text = (
        f"⏰ <b>Напоминание</b>\n\n"
        f"Завтра ({end_date}) заканчивается аренда байка "
        f"{bike_model} ({plate_number}).\n"
        f"Заявка #{booking_id}. Не забудь вернуть байк вовремя."
    )
    owner_text = (
        f"⏰ <b>Напоминание владельцу</b>\n\n"
        f"Завтра ({end_date}) заканчивается аренда байка "
        f"{bike_model} ({plate_number}).\n"
        f"Заявка #{booking_id}. Клиент уведомлён."
    )
    await _send(client_telegram_id, client_text)
    await _send(owner_telegram_id, owner_text)