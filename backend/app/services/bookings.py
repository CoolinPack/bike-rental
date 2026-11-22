from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg

from app.models.schemas import BookingRequestCreate


class BookingConflictError(ValueError):
    """Raised when another request/rental already holds the selected dates."""


def daily_rate_for_days(bike: dict, days: int):
    """Return the configured per-day rate for the selected duration band."""
    if days >= 30:
        tier = bike.get("price_30_days")
    elif days >= 14:
        tier = bike.get("price_14_days")
    elif days >= 7:
        tier = bike.get("price_7_days")
    elif days >= 3:
        tier = bike.get("price_3_days")
    else:
        tier = None
    return tier if tier is not None else bike["daily_price"]


async def _get_bike_in_park(
    conn: asyncpg.Connection, bike_id: int, park_id: int
) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM bikes WHERE id = $1 AND park_id = $2", bike_id, park_id
    )
    return dict(row) if row else None


async def has_overlap(
    conn: asyncpg.Connection,
    bike_id: int,
    start_date: date,
    end_date: date,
    exclude_booking_id: int | None = None,
) -> bool:
    """
    Пересечение по датам с бронью в статусе pending или active.
    Заявка блокирует даты даже до подтверждения — иначе два клиента
    могут подать заявку на одни даты и обе окажутся в очереди.
    """
    args: list = [bike_id, start_date, end_date]
    extra = ""
    if exclude_booking_id is not None:
        extra = " AND id <> $4"
        args.append(exclude_booking_id)

    row = await conn.fetchval(
        f"""
        SELECT 1 FROM bookings
        WHERE bike_id = $1
          AND status IN ('pending', 'active')
          AND NOT (end_date < $2 OR start_date > $3)
          {extra}
        LIMIT 1
        """,
        *args,
    )
    return bool(row)


async def create_request(
    conn: asyncpg.Connection,
    park_id: int,
    client_telegram_id: int,
    client_username: str | None,
    data: BookingRequestCreate,
) -> int:
    if data.end_date < data.start_date:
        raise ValueError("end_date must be >= start_date")
    vietnam_today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    if data.start_date < vietnam_today:
        raise ValueError("start_date cannot be in the past")

    async with conn.transaction():
        # Serialize booking attempts for the same bike so simultaneous requests
        # cannot both pass the overlap check.
        await conn.execute("SELECT pg_advisory_xact_lock($1)", data.bike_id)
        bike = await _get_bike_in_park(conn, data.bike_id, park_id)
        if not bike:
            raise PermissionError("Bike not found in this park")
        if bike["status"] == "maintenance":
            raise ValueError("Bike is under maintenance")

        if await has_overlap(conn, data.bike_id, data.start_date, data.end_date):
            raise BookingConflictError("Байк уже забронирован на выбранные даты. Выберите другой период.")

        days = (data.end_date - data.start_date).days + 1
        applied_daily_price = daily_rate_for_days(bike, days)
        total = applied_daily_price * days

        booking_id = await conn.fetchval(
            """
            INSERT INTO bookings (
                park_id, client_telegram_id, bike_id,
                start_date, end_date, total_price, original_total_price, status,
                client_name, client_phone, client_username, deposit_comment
            ) VALUES ($1,$2,$3,$4,$5,$6,$6,'pending',$7,$8,$9,$10)
            RETURNING id
            """,
            park_id,
            client_telegram_id,
            data.bike_id,
            data.start_date,
            data.end_date,
            total,
            data.client_name,
            data.client_phone,
            client_username,
            data.deposit_comment,
        )

    # Уведомление владельцу (best-effort: ошибка бота не роняет создание заявки)
    try:
        from app.bot.notifications import notify_owner_new_request
        import logging

        park = await conn.fetchrow(
            "SELECT name, owner_telegram_id, bot_token FROM parks WHERE id = $1", park_id
        )
        if park:
            await notify_owner_new_request(
                owner_telegram_id=park["owner_telegram_id"],
                park_name=park["name"],
                booking_id=int(booking_id),
                client_name=data.client_name,
                client_phone=data.client_phone,
                client_username=client_username,
                bike_model=bike["model"],
                plate_number=bike["plate_number"],
                start_date=data.start_date,
                end_date=data.end_date,
                total_price=total,
                deposit_comment=data.deposit_comment,
                park_id=park_id,
                bot_token=park["bot_token"],
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify owner")

    return int(booking_id)


async def list_client_bookings(
    conn: asyncpg.Connection, park_id: int, client_telegram_id: int
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT bk.*, b.plate_number, b.model, b.photos
        FROM bookings bk
        JOIN bikes b ON b.id = bk.bike_id
        WHERE bk.park_id = $1 AND bk.client_telegram_id = $2
        ORDER BY bk.created_at DESC
        """,
        park_id, client_telegram_id,
    )
    return [dict(r) for r in rows]


async def get_client_booking(
    conn: asyncpg.Connection,
    park_id: int,
    client_telegram_id: int,
    booking_id: int,
) -> dict:
    row = await conn.fetchrow(
        """
        SELECT bk.*, b.plate_number, b.model, b.photos
        FROM bookings bk
        JOIN bikes b ON b.id = bk.bike_id
        WHERE bk.id = $1 AND bk.park_id = $2 AND bk.client_telegram_id = $3
        """,
        booking_id, park_id, client_telegram_id,
    )
    if not row:
        raise PermissionError("Booking not found")
    return dict(row)


async def cancel_booking(
    conn: asyncpg.Connection,
    park_id: int,
    client_telegram_id: int,
    booking_id: int,
) -> None:
    row = await conn.fetchrow(
        """
        SELECT * FROM bookings
        WHERE id = $1 AND park_id = $2 AND client_telegram_id = $3
        """,
        booking_id, park_id, client_telegram_id,
    )
    if not row:
        raise PermissionError("Booking not found")
    if row["status"] not in ("pending", "active"):
        raise ValueError(f"Booking is {row['status']}, cannot cancel")

    was_active = row["status"] == "active"
    await conn.execute(
        "UPDATE bookings SET status = 'cancelled' WHERE id = $1", booking_id
    )
    if was_active:
        if not await has_overlap(
            conn, row["bike_id"], row["start_date"], row["end_date"],
            exclude_booking_id=booking_id,
        ):
            await conn.execute(
                "UPDATE bikes SET status = 'available' "
                "WHERE id = $1 AND park_id = $2 AND status = 'rented'",
                row["bike_id"], park_id,
            )


async def complete_booking(
    conn: asyncpg.Connection,
    park_id: int,
    client_telegram_id: int,
    booking_id: int,
) -> None:
    row = await conn.fetchrow(
        """
        SELECT * FROM bookings
        WHERE id = $1 AND park_id = $2 AND client_telegram_id = $3
        """,
        booking_id, park_id, client_telegram_id,
    )
    if not row:
        raise PermissionError("Booking not found")
    if row["status"] != "active":
        raise ValueError(f"Booking is {row['status']}, cannot complete")

    await conn.execute(
        "UPDATE bookings SET status = 'completed' WHERE id = $1", booking_id
    )
    if not await has_overlap(
        conn, row["bike_id"], row["start_date"], row["end_date"],
        exclude_booking_id=booking_id,
    ):
        await conn.execute(
            "UPDATE bikes SET status = 'available' "
            "WHERE id = $1 AND park_id = $2 AND status = 'rented'",
            row["bike_id"], park_id,
        )


# ============ OWNER: заявки ============

async def list_owner_requests(
    conn: asyncpg.Connection, park_id: int, status_filter: str | None = None
) -> list[dict]:
    if status_filter:
        rows = await conn.fetch(
            """
            SELECT bk.*, b.plate_number, b.model, b.photos
            FROM bookings bk
            JOIN bikes b ON b.id = bk.bike_id
            WHERE bk.park_id = $1 AND bk.status = $2
            ORDER BY bk.created_at DESC
            """,
            park_id, status_filter,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT bk.*, b.plate_number, b.model, b.photos
            FROM bookings bk
            JOIN bikes b ON b.id = bk.bike_id
            WHERE bk.park_id = $1
            ORDER BY bk.created_at DESC
            """,
            park_id,
        )
    return [dict(r) for r in rows]


async def accept_request(
    conn: asyncpg.Connection, park_id: int, booking_id: int
) -> dict:
    async with conn.transaction():
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1 AND park_id = $2",
            booking_id, park_id,
        )
        if not row:
            raise PermissionError("Request not found")

        # Use the same per-bike lock as new booking requests.
        await conn.execute("SELECT pg_advisory_xact_lock($1)", row["bike_id"])
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1 AND park_id = $2 FOR UPDATE",
            booking_id, park_id,
        )
        if not row:
            raise PermissionError("Request not found")
        if row["status"] != "pending":
            raise ValueError(f"Booking is {row['status']}, cannot accept")

        if await has_overlap(
            conn, row["bike_id"], row["start_date"], row["end_date"],
            exclude_booking_id=booking_id,
        ):
            raise BookingConflictError(
                "Байк уже забронирован на эти даты другой заявкой."
            )

        await conn.execute(
            "UPDATE bookings SET status = 'active', accepted_at = NOW() "
            "WHERE id = $1",
            booking_id,
        )
        # A future reservation blocks dates but is physically rented only
        # when its pickup date arrives.
        await conn.execute(
            """
            UPDATE bikes SET status = CASE
              WHEN $3 <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
              THEN 'rented' ELSE status END
            WHERE id = $1 AND park_id = $2
            """,
            row["bike_id"], park_id, row["start_date"],
        )

    # Notify the client after the transaction commits.
    try:
        from app.bot.notifications import notify_client_accepted
        bike = await conn.fetchrow(
            "SELECT model, plate_number FROM bikes WHERE id = $1", row["bike_id"]
        )
        park = await conn.fetchrow("SELECT bot_token FROM parks WHERE id=$1", park_id)
        if bike:
            await notify_client_accepted(
                client_telegram_id=row["client_telegram_id"],
                booking_id=booking_id,
                bike_model=bike["model"],
                plate_number=bike["plate_number"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                total_price=row["total_price"],
                park_id=park_id,
                bot_token=park["bot_token"] if park else None,
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify client (accept)")

    return {"ok": True, "booking_id": booking_id}


async def reject_request(
    conn: asyncpg.Connection, park_id: int, booking_id: int, reason: str | None
) -> None:
    async with conn.transaction():
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1 AND park_id = $2",
            booking_id, park_id,
        )
        if not row:
            raise PermissionError("Request not found")
        await conn.execute("SELECT pg_advisory_xact_lock($1)", row["bike_id"])
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1 AND park_id = $2 FOR UPDATE",
            booking_id, park_id,
        )
        if not row:
            raise PermissionError("Request not found")
        if row["status"] != "pending":
            raise ValueError(f"Booking is {row['status']}, cannot reject")
        await conn.execute(
            "UPDATE bookings SET status = 'rejected' WHERE id = $1", booking_id
        )

    try:
        from app.bot.notifications import notify_client_rejected
        bike = await conn.fetchrow(
            "SELECT model, plate_number FROM bikes WHERE id = $1", row["bike_id"]
        )
        park = await conn.fetchrow("SELECT bot_token FROM parks WHERE id=$1", park_id)
        if bike:
            await notify_client_rejected(
                client_telegram_id=row["client_telegram_id"],
                booking_id=booking_id,
                bike_model=bike["model"],
                plate_number=bike["plate_number"],
                reason=reason,
                park_id=park_id,
                bot_token=park["bot_token"] if park else None,
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify client (reject)")


async def bookings_due_reminders(conn: asyncpg.Connection) -> list[dict]:
    """Active rentals due in 3 or 1 days (Vietnam local date), once per milestone."""
    rows = await conn.fetch(
        """
        SELECT bk.*, b.plate_number, b.model, p.name AS park_name,
               p.owner_telegram_id, p.bot_token,
               ((bk.end_date - (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date))::int AS days_left
        FROM bookings bk
        JOIN bikes b ON b.id = bk.bike_id
        JOIN parks p ON p.id = bk.park_id
        WHERE bk.status = 'active'
          AND (
            (bk.end_date = (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date + 3
             AND bk.reminder_3_sent_at IS NULL)
            OR
            (bk.end_date = (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date + 1
             AND bk.reminder_1_sent_at IS NULL)
          )
        ORDER BY bk.end_date
        """
    )
    return [dict(r) for r in rows]


async def claim_reminder(
    conn: asyncpg.Connection, booking_id: int, days_left: int
) -> bool:
    column = "reminder_3_sent_at" if days_left == 3 else "reminder_1_sent_at"
    value = await conn.fetchval(
        f"UPDATE bookings SET {column}=NOW() WHERE id=$1 AND {column} IS NULL RETURNING id",
        booking_id,
    )
    return value is not None


async def release_reminder_claim(
    conn: asyncpg.Connection, booking_id: int, days_left: int
) -> None:
    column = "reminder_3_sent_at" if days_left == 3 else "reminder_1_sent_at"
    await conn.execute(f"UPDATE bookings SET {column}=NULL WHERE id=$1", booking_id)



async def extend_booking(
    conn: asyncpg.Connection, park_id: int, booking_id: int, new_end_date: date
) -> dict:
    """Extend an active rental and preserve original/extension amounts separately."""
    async with conn.transaction():
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id=$1 AND park_id=$2",
            booking_id, park_id,
        )
        if row:
            await conn.execute("SELECT pg_advisory_xact_lock($1)", row["bike_id"])
            row = await conn.fetchrow(
                "SELECT * FROM bookings WHERE id=$1 AND park_id=$2 FOR UPDATE",
                booking_id, park_id,
            )
        if not row:
            raise PermissionError("Booking not found")
        if row["status"] != "active":
            raise ValueError("Only active rentals can be extended")
        old_end = row["end_date"]
        if new_end_date <= old_end:
            raise ValueError("New end date must be later than current end date")
        # The next booking can begin the day after the current end date.
        overlap = await conn.fetchval(
            """
            SELECT 1 FROM bookings
            WHERE bike_id=$1 AND id<>$2 AND status IN ('pending','active')
              AND NOT (end_date < $3 OR start_date > $4)
            LIMIT 1
            """,
            row["bike_id"], booking_id, old_end + timedelta(days=1),
            new_end_date,
        )
        if overlap:
            raise ValueError("The bike is already booked during the extension period")
        bike = await conn.fetchrow(
            "SELECT daily_price, price_3_days, price_7_days, price_14_days, price_30_days "
            "FROM bikes WHERE id=$1 AND park_id=$2",
            row["bike_id"], park_id,
        )
        days = (new_end_date - old_end).days
        daily = daily_rate_for_days(dict(bike), days)
        amount = daily * days
        await conn.execute(
            """
            INSERT INTO booking_extensions
              (booking_id, park_id, old_end_date, new_end_date, days_added, daily_price, amount)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
            booking_id, park_id, old_end, new_end_date, days, daily, amount,
        )
        await conn.execute(
            """
            UPDATE bookings
            SET end_date=$1,
                extension_total_price=COALESCE(extension_total_price,0)+$2,
                total_price=COALESCE(original_total_price,total_price)+COALESCE(extension_total_price,0)+$2,
                reminder_3_sent_at=NULL, reminder_1_sent_at=NULL
            WHERE id=$3 AND park_id=$4
            """,
            new_end_date, amount, booking_id, park_id,
        )
    return {
        "booking_id": booking_id, "old_end_date": old_end,
        "new_end_date": new_end_date, "days_added": days,
        "daily_price": daily, "extension_amount": amount,
        "original_total_price": row["original_total_price"] or row["total_price"],
        "extension_total_price": (row["extension_total_price"] or 0) + amount,
    }
