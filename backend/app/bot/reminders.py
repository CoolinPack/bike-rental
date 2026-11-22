import asyncio
import logging

from app.bot.notifications import notify_reminder
from app.database import get_pool
from app.services import bookings as bookings_service

logger = logging.getLogger(__name__)

# Frequent polling is safe because reminder timestamps are set after processing.
REMINDER_INTERVAL_SECONDS = 300


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
        # Automatically switch a bike to "rented" on the actual pickup date.
        await conn.execute(
            """
            UPDATE bikes b SET status='rented'
            WHERE b.status='available'
              AND EXISTS (
                SELECT 1 FROM bookings bk
                WHERE bk.bike_id=b.id AND bk.park_id=b.park_id
                  AND bk.status='active'
                  AND bk.start_date <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  AND bk.end_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
              )
            """
        )
        due = await bookings_service.bookings_due_reminders(conn)
        for booking in due:
            days_left = int(booking["days_left"])
            claimed = await bookings_service.claim_reminder(
                conn, booking["id"], days_left
            )
            if not claimed:
                continue
            try:
                sent = await notify_reminder(
                    client_telegram_id=booking["client_telegram_id"],
                    owner_telegram_id=booking["owner_telegram_id"],
                    booking_id=booking["id"],
                    bike_model=booking["model"],
                    plate_number=booking["plate_number"],
                    end_date=booking["end_date"],
                    days_left=days_left,
                    client_name=booking.get("client_name"),
                    park_id=booking["park_id"],
                    bot_token=booking.get("bot_token"),
                )
                if not sent:
                    raise RuntimeError("Telegram did not accept one or more reminder messages")
                logger.info(
                    "Sent %s-day rental reminder for booking %s",
                    days_left, booking["id"],
                )
            except Exception:
                await bookings_service.release_reminder_claim(
                    conn, booking["id"], days_left
                )
                logger.exception(
                    "Failed to send reminder for booking %s", booking["id"]
                )
