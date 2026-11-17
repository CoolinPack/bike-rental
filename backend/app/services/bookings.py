from datetime import date

import asyncpg

from app.models.schemas import BookingRequestCreate


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
    if data.start_date < date.today():
        raise ValueError("start_date cannot be in the past")

    bike = await _get_bike_in_park(conn, data.bike_id, park_id)
    if not bike:
        raise PermissionError("Bike not found in this park")
    if bike["status"] == "maintenance":
        raise ValueError("Bike is under maintenance")

    if await has_overlap(conn, data.bike_id, data.start_date, data.end_date):
        raise ValueError("Bike is already booked or requested for these dates")

    days = (data.end_date - data.start_date).days + 1
    total = bike["daily_price"] * days

    booking_id = await conn.fetchval(
        """
        INSERT INTO bookings (
            park_id, client_telegram_id, bike_id,
            start_date, end_date, total_price, status,
            client_name, client_phone, client_username, deposit_comment
        ) VALUES ($1,$2,$3,$4,$5,$6,'pending',$7,$8,$9,$10)
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
            "SELECT name, owner_telegram_id FROM parks WHERE id = $1", park_id
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
    row = await conn.fetchrow(
        "SELECT * FROM bookings WHERE id = $1 AND park_id = $2",
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
        raise ValueError("Dates already booked by another active booking")

    await conn.execute(
        "UPDATE bookings SET status = 'active', accepted_at = NOW() "
        "WHERE id = $1",
        booking_id,
    )
    await conn.execute(
        "UPDATE bikes SET status = 'rented' WHERE id = $1 AND park_id = $2",
        row["bike_id"], park_id,
    )

    # Уведомление клиенту
    try:
        from app.bot.notifications import notify_client_accepted
        bike = await conn.fetchrow(
            "SELECT model, plate_number FROM bikes WHERE id = $1", row["bike_id"]
        )
        if bike:
            await notify_client_accepted(
                client_telegram_id=row["client_telegram_id"],
                booking_id=booking_id,
                bike_model=bike["model"],
                plate_number=bike["plate_number"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                total_price=row["total_price"],
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify client (accept)")

    return {"ok": True, "booking_id": booking_id}


async def reject_request(
    conn: asyncpg.Connection, park_id: int, booking_id: int, reason: str | None
) -> None:
    row = await conn.fetchrow(
        "SELECT * FROM bookings WHERE id = $1 AND park_id = $2",
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
        if bike:
            await notify_client_rejected(
                client_telegram_id=row["client_telegram_id"],
                booking_id=booking_id,
                bike_model=bike["model"],
                plate_number=bike["plate_number"],
                reason=reason,
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify client (reject)")


async def bookings_due_tomorrow(conn: asyncpg.Connection) -> list[dict]:
    """Активные брони, у которых end_date = завтра и reminder ещё не отправлен."""
    rows = await conn.fetch(
        """
        SELECT bk.*, b.plate_number, b.model, p.name AS park_name,
               p.owner_telegram_id
        FROM bookings bk
        JOIN bikes b ON b.id = bk.bike_id
        JOIN parks p ON p.id = bk.park_id
        WHERE bk.status = 'active'
          AND bk.end_date = CURRENT_DATE + 1
          AND bk.reminder_sent_at IS NULL
        """
    )
    return [dict(r) for r in rows]


async def mark_reminder_sent(conn: asyncpg.Connection, booking_id: int) -> None:
    await conn.execute(
        "UPDATE bookings SET reminder_sent_at = NOW() WHERE id = $1",
        booking_id,
    )