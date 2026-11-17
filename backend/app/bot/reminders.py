import asyncio
import logging

from app.bot.notifications import notify_reminder
from app.database import get_pool
from app.services import bookings as bookings_service

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 30  # раз в час


async def reminder_worker() -> None:
    while True:
        try:
            await _process_reminders()
        except Exception:
            logger.exception("Reminder worker iteration failed")
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)


async def _process_reminders() -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        due = await bookings_service.bookings_due_tomorrow(conn)
        for booking in due:
            await notify_reminder(
                client_telegram_id=booking["client_telegram_id"],
                owner_telegram_id=booking["owner_telegram_id"],
                booking_id=booking["id"],
                bike_model=booking["model"],
                plate_number=booking["plate_number"],
                end_date=booking["end_date"],
            )
            await bookings_service.mark_reminder_sent(conn, booking["id"])
            logger.info("Sent reminder for booking %s", booking["id"])