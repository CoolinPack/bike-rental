from datetime import datetime, timedelta, timezone
from decimal import Decimal

import asyncpg

from app.models.schemas import ParkCreate, ParkUpdate


PLAN_PRICES = {
    "start": Decimal("17.00"),
    "pro": Decimal("49.00"),
}

PLAN_LIMITS = {
    "start": 10,
    "pro": 20,
}


def compute_monthly_price(
    plan: str, custom_price: Decimal | None, discount: Decimal
) -> Decimal:
    base = custom_price if custom_price is not None else PLAN_PRICES.get(plan, Decimal("0"))
    if discount > 0:
        base = base * (Decimal("1") - discount / Decimal("100"))
    return base.quantize(Decimal("0.01"))


def add_months(dt: datetime, months: int) -> datetime:
    return dt + timedelta(days=30 * months)


async def create_park(conn: asyncpg.Connection, data: ParkCreate) -> int:
    now = datetime.now(timezone.utc)
    expires = add_months(now, data.subscription_months) if data.subscription_months > 0 else None
    park_id = await conn.fetchval(
        """
        INSERT INTO parks (
            name, owner_telegram_id, bot_token, subscription_plan,
            subscription_expires_at, custom_price_usd, discount_percent,
            referred_by_park_id, is_active, bikes_limit
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9)
        RETURNING id
        """,
        data.name,
        data.owner_telegram_id,
        data.bot_token,
        data.subscription_plan,
        expires,
        data.custom_price_usd,
        data.discount_percent,
        data.referred_by_park_id,
        PLAN_LIMITS.get(data.subscription_plan, 10),
    )
    return int(park_id)


async def update_park(conn: asyncpg.Connection, park_id: int, data: ParkUpdate) -> None:
    fields = []
    args: list = []
    idx = 1

    for field in ("name", "bot_token", "subscription_plan",
                  "custom_price_usd", "discount_percent", "is_active"):
        value = getattr(data, field)
        if value is not None:
            fields.append(f"{field} = ${idx}")
            args.append(value)
            idx += 1

    if data.subscription_plan is not None:
        fields.append(f"bikes_limit = ${idx}")
        args.append(PLAN_LIMITS.get(data.subscription_plan, 10))
        idx += 1

    if not fields:
        return

    args.append(park_id)
    query = f"UPDATE parks SET {', '.join(fields)} WHERE id = ${idx}"
    await conn.execute(query, *args)


async def list_parks(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
            p.id, p.name, p.owner_telegram_id, p.subscription_plan,
            p.subscription_expires_at, p.custom_price_usd, p.discount_percent,
            p.referred_by_park_id, p.is_active, p.created_at, p.bikes_limit,
            COALESCE(b.bikes_count, 0) AS bikes_count,
            COALESCE(bk.bookings_count, 0) AS bookings_count,
            COALESCE(bk.revenue_usd, 0) AS revenue_usd
        FROM parks p
        LEFT JOIN (
            SELECT park_id, COUNT(*) AS bikes_count
            FROM bikes GROUP BY park_id
        ) b ON b.park_id = p.id
        LEFT JOIN (
            SELECT park_id,
                   COUNT(*) AS bookings_count,
                   COALESCE(SUM(total_price), 0) AS revenue_usd
            FROM bookings WHERE status = 'completed'
            GROUP BY park_id
        ) bk ON bk.park_id = p.id
        ORDER BY p.id ASC
        """
    )
    return [dict(r) for r in rows]


async def get_park(conn: asyncpg.Connection, park_id: int) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM parks WHERE id = $1", park_id)
    return dict(row) if row else None


async def delete_park(conn: asyncpg.Connection, park_id: int) -> None:
    await conn.execute("DELETE FROM parks WHERE id = $1", park_id)


async def create_payment_request(
    conn: asyncpg.Connection, park_id: int, months: int
) -> int:
    park = await get_park(conn, park_id)
    if not park:
        raise ValueError("Park not found")
    monthly = compute_monthly_price(
        park["subscription_plan"],
        park["custom_price_usd"],
        park["discount_percent"],
    )
    amount = monthly * months
    req_id = await conn.fetchval(
        """
        INSERT INTO payment_requests (park_id, amount_usd, months)
        VALUES ($1, $2, $3) RETURNING id
        """,
        park_id, amount, months,
    )
    return int(req_id)


async def list_payment_requests(
    conn: asyncpg.Connection, status: str | None = None
) -> list[dict]:
    if status:
        rows = await conn.fetch(
            """
            SELECT pr.*, p.name AS park_name
            FROM payment_requests pr
            JOIN parks p ON p.id = pr.park_id
            WHERE pr.status = $1
            ORDER BY pr.requested_at DESC
            """,
            status,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT pr.*, p.name AS park_name
            FROM payment_requests pr
            JOIN parks p ON p.id = pr.park_id
            ORDER BY pr.requested_at DESC
            """
        )
    return [dict(r) for r in rows]


async def confirm_payment(
    conn: asyncpg.Connection,
    request_id: int,
    amount_override: Decimal | None = None,
) -> dict:
    req = await conn.fetchrow(
        "SELECT * FROM payment_requests WHERE id = $1", request_id
    )
    if not req:
        raise ValueError("Payment request not found")
    if req["status"] != "pending":
        raise ValueError(f"Payment request is {req['status']}")

    park = await get_park(conn, req["park_id"])
    if not park:
        raise ValueError("Park not found")

    now = datetime.now(timezone.utc)
    current_expires = park["subscription_expires_at"] or now
    if current_expires < now:
        current_expires = now
    new_expires = add_months(current_expires, req["months"])

    final_amount = amount_override if amount_override is not None else req["amount_usd"]

    await conn.execute(
        "UPDATE parks SET subscription_expires_at = $1 WHERE id = $2",
        new_expires, park["id"],
    )
    await conn.execute(
        """
        UPDATE payment_requests
        SET status = 'confirmed', confirmed_at = NOW(), amount_usd = $1
        WHERE id = $2
        """,
        final_amount, request_id,
    )
    return {
        "request_id": request_id,
        "park_id": park["id"],
        "amount_usd": final_amount,
        "new_expires_at": new_expires,
    }


async def super_admin_summary(conn: asyncpg.Connection) -> dict:
    parks_total = await conn.fetchval("SELECT COUNT(*) FROM parks")
    parks_active = await conn.fetchval("SELECT COUNT(*) FROM parks WHERE is_active = TRUE")
    bikes_total = await conn.fetchval("SELECT COUNT(*) FROM bikes")
    bookings_total = await conn.fetchval(
        "SELECT COUNT(*) FROM bookings WHERE status = 'completed'"
    )
    revenue_total = await conn.fetchval(
        "SELECT COALESCE(SUM(total_price), 0) FROM bookings WHERE status = 'completed'"
    )
    pending = await conn.fetchval(
        "SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"
    )
    return {
        "parks_total": int(parks_total),
        "parks_active": int(parks_active),
        "bikes_total": int(bikes_total),
        "bookings_total": int(bookings_total),
        "revenue_total_usd": Decimal(str(revenue_total)),
        "pending_payments": int(pending),
    }


async def check_park_access(conn: asyncpg.Connection, park_id: int) -> dict:
    """Проверяет, активна ли подписка. Возвращает park + is_expired, days_left."""
    park = await get_park(conn, park_id)
    if not park:
        raise PermissionError("Park not found")
    now = datetime.now(timezone.utc)
    expires = park["subscription_expires_at"]
    if expires is None:
        is_expired = True
        days_left = 0
    else:
        is_expired = expires < now
        days_left = max(0, (expires - now).days)
    return {**park, "is_expired": is_expired, "days_left": days_left}


async def change_plan(
    conn: asyncpg.Connection, park_id: int, new_plan: str
) -> dict:
    """Смена тарифа без потери данных. Дата окончания не меняется."""
    if new_plan not in ("start", "pro"):
        raise ValueError("Plan must be start or pro")
    park = await get_park(conn, park_id)
    if not park:
        raise PermissionError("Park not found")
    limit = PLAN_LIMITS[new_plan]
    await conn.execute(
        "UPDATE parks SET subscription_plan = $1, bikes_limit = $2 WHERE id = $3",
        new_plan, limit, park_id,
    )
    return {"ok": True, "new_plan": new_plan, "bikes_limit": limit}


async def extend_subscription(
    conn: asyncpg.Connection, park_id: int, months: int
) -> dict:
    """Продление подписки на N месяцев (1 или 3)."""
    if months not in (1, 3):
        raise ValueError("months must be 1 or 3")
    park = await get_park(conn, park_id)
    if not park:
        raise PermissionError("Park not found")
    now = datetime.now(timezone.utc)
    current = park["subscription_expires_at"] or now
    if current < now:
        current = now
    new_expires = add_months(current, months)
    await conn.execute(
        "UPDATE parks SET subscription_expires_at = $1 WHERE id = $2",
        new_expires, park_id,
    )
    return {"ok": True, "new_expires_at": new_expires}


async def my_revenue_summary(conn: asyncpg.Connection) -> dict:
    """Сводка подписочной выручки для супер-админа."""
    total_confirmed = await conn.fetchval(
        "SELECT COALESCE(SUM(amount_usd), 0) FROM payment_requests WHERE status = 'confirmed'"
    )
    now = datetime.now(timezone.utc)

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = await conn.fetchval(
        """
        SELECT COALESCE(SUM(amount_usd), 0) FROM payment_requests
        WHERE status = 'confirmed' AND confirmed_at >= $1
        """,
        month_start,
    )

    by_park = await conn.fetch(
        """
        SELECT p.id AS park_id, p.name,
               COALESCE(SUM(pr.amount_usd), 0) AS total_paid,
               MAX(pr.confirmed_at) AS last_paid_at,
               p.subscription_expires_at, p.is_active, p.subscription_plan,
               p.bikes_limit
        FROM parks p
        LEFT JOIN payment_requests pr
          ON pr.park_id = p.id AND pr.status = 'confirmed'
        GROUP BY p.id
        ORDER BY p.id
        """
    )

    parks_list = []
    for r in by_park:
        expires = r["subscription_expires_at"]
        if expires is None:
            is_expired = True
            days_left = 0
        else:
            is_expired = expires < now
            days_left = max(0, (expires - now).days)
        parks_list.append({
            "park_id": r["park_id"],
            "name": r["name"],
            "total_paid": Decimal(str(r["total_paid"])),
            "last_paid_at": r["last_paid_at"],
            "subscription_expires_at": expires,
            "is_active": r["is_active"],
            "subscription_plan": r["subscription_plan"],
            "bikes_limit": r["bikes_limit"],
            "is_expired": is_expired,
            "days_left": days_left,
        })

    parks_active = sum(1 for p in parks_list if not p["is_expired"] and p["is_active"])
    parks_expired = sum(1 for p in parks_list if p["is_expired"])
    parks_disabled = sum(1 for p in parks_list if not p["is_active"])

    return {
        "total_confirmed_revenue": Decimal(str(total_confirmed)),
        "this_month_revenue": Decimal(str(this_month)),
        "parks_total": len(parks_list),
        "parks_active": parks_active,
        "parks_expired": parks_expired,
        "parks_disabled": parks_disabled,
        "parks": parks_list,
    }
