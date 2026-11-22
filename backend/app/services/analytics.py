from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import asyncpg


def default_period(
    from_date: date | None, to_date: date | None
) -> tuple[date, date]:
    vietnam_today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    to_d = to_date or vietnam_today
    from_d = from_date or (to_d - timedelta(days=29))
    return from_d, to_d


async def summary(
    conn: asyncpg.Connection,
    park_id: int,
    from_date: date,
    to_date: date,
    bike_id: int | None = None,
) -> dict:
    bike_cond = " AND bike_id = $4" if bike_id else ""
    args = [park_id, from_date, to_date] + ([bike_id] if bike_id else [])

    row = await conn.fetchrow(
        f"""
        SELECT
            COALESCE(SUM(total_price), 0) AS revenue,
            COUNT(*) AS bookings_count
        FROM bookings
        WHERE park_id = $1
          AND status = 'completed'
          AND start_date BETWEEN $2 AND $3
          {bike_cond}
        """,
        *args,
    )
    expenses_row = await conn.fetchrow(
        f"""
        SELECT COALESCE(SUM(amount), 0) AS expenses
        FROM expenses
        WHERE park_id = $1
          AND expense_date BETWEEN $2 AND $3
          {bike_cond}
        """,
        *args,
    )
    revenue = Decimal(str(row["revenue"]))
    expenses = Decimal(str(expenses_row["expenses"]))
    profit = revenue - expenses
    bookings_count = int(row["bookings_count"])
    avg_ticket = (
        (revenue / bookings_count).quantize(Decimal("0.01"))
        if bookings_count > 0
        else Decimal("0")
    )
    return {
        "from_date": from_date,
        "to_date": to_date,
        "revenue": revenue,
        "expenses": expenses,
        "profit": profit,
        "bookings_count": bookings_count,
        "avg_ticket": avg_ticket,
    }


async def by_bikes(
    conn: asyncpg.Connection,
    park_id: int,
    from_date: date,
    to_date: date,
) -> list[dict]:
    rows = await conn.fetch(
        """
        WITH revenue AS (
            SELECT bike_id,
                   COALESCE(SUM(total_price), 0) AS revenue,
                   COUNT(*) AS bookings_count,
                   COALESCE(AVG(end_date - start_date + 1), 0) AS avg_rental_days
            FROM bookings
            WHERE park_id = $1
              AND status = 'completed'
              AND start_date BETWEEN $2 AND $3
            GROUP BY bike_id
        ),
        occupancy AS (
            SELECT bike_id,
                   COALESCE(SUM(
                       LEAST(end_date, $3) - GREATEST(start_date, $2) + 1
                   ), 0) AS rented_days
            FROM bookings
            WHERE park_id = $1
              AND status IN ('active', 'completed')
              AND NOT (end_date < $2 OR start_date > $3)
            GROUP BY bike_id
        ),
        expenses_agg AS (
            SELECT bike_id,
                   COALESCE(SUM(amount), 0) AS expenses
            FROM expenses
            WHERE park_id = $1
              AND expense_date BETWEEN $2 AND $3
            GROUP BY bike_id
        )
        SELECT
            b.id AS bike_id,
            b.plate_number,
            b.model,
            COALESCE(r.revenue, 0) AS revenue,
            COALESCE(e.expenses, 0) AS expenses,
            COALESCE(r.bookings_count, 0) AS bookings_count,
            COALESCE(o.rented_days, 0) AS rented_days,
            COALESCE(r.avg_rental_days, 0) AS avg_rental_days
        FROM bikes b
        LEFT JOIN revenue r ON r.bike_id = b.id
        LEFT JOIN occupancy o ON o.bike_id = b.id
        LEFT JOIN expenses_agg e ON e.bike_id = b.id
        WHERE b.park_id = $1
        ORDER BY revenue DESC, b.id ASC
        """,
        park_id, from_date, to_date,
    )

    period_days = (to_date - from_date).days + 1
    result = []
    for r in rows:
        revenue = Decimal(str(r["revenue"]))
        expenses = Decimal(str(r["expenses"]))
        profit = revenue - expenses
        profitability = (
            (profit / revenue * Decimal("100")).quantize(Decimal("0.01"))
            if revenue > 0
            else Decimal("0")
        )
        rented_days = int(r["rented_days"])
        utilization = (
            (Decimal(rented_days) / Decimal(period_days) * Decimal("100"))
            .quantize(Decimal("0.01"))
            if period_days > 0
            else Decimal("0")
        )
        revenue_per_day = (
            (revenue / Decimal(period_days)).quantize(Decimal("0.01"))
            if period_days > 0
            else Decimal("0")
        )
        idle_days = max(0, period_days - rented_days)
        avg_rental_days = Decimal(str(r["avg_rental_days"])).quantize(
            Decimal("0.01")
        )
        result.append({
            "bike_id": r["bike_id"],
            "plate_number": r["plate_number"],
            "model": r["model"],
            "revenue": revenue,
            "expenses": expenses,
            "profit": profit,
            "profitability_percent": profitability,
            "bookings_count": int(r["bookings_count"]),
            "rented_days": rented_days,
            "idle_days": idle_days,
            "utilization_percent": utilization,
            "revenue_per_day": revenue_per_day,
            "avg_rental_days": avg_rental_days,
        })
    return result


async def by_categories(
    conn: asyncpg.Connection,
    park_id: int,
    from_date: date,
    to_date: date,
    bike_id: int | None = None,
) -> list[dict]:
    bike_cond = " AND bike_id = $4" if bike_id else ""
    args = [park_id, from_date, to_date] + ([bike_id] if bike_id else [])
    rows = await conn.fetch(
        f"""
        SELECT category, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt
        FROM expenses
        WHERE park_id = $1
          AND expense_date BETWEEN $2 AND $3
          {bike_cond}
        GROUP BY category
        ORDER BY total DESC
        """,
        *args,
    )
    return [
        {
            "category": r["category"],
            "total": Decimal(str(r["total"])),
            "count": int(r["cnt"]),
        }
        for r in rows
    ]


async def timeline(
    conn: asyncpg.Connection,
    park_id: int,
    from_date: date,
    to_date: date,
    granularity: str = "day",
    bike_id: int | None = None,
) -> list[dict]:
    if granularity == "month":
        bucket = "date_trunc('month', start_date)::date"
        exp_bucket = "date_trunc('month', expense_date)::date"
    else:
        bucket = "start_date"
        exp_bucket = "expense_date"

    bike_cond = " AND bike_id = $4" if bike_id else ""
    args = [park_id, from_date, to_date] + ([bike_id] if bike_id else [])

    revenue_rows = await conn.fetch(
        f"""
        SELECT {bucket} AS period,
               COALESCE(SUM(total_price), 0) AS revenue,
               COUNT(*) AS bookings_count
        FROM bookings
        WHERE park_id = $1
          AND status = 'completed'
          AND start_date BETWEEN $2 AND $3
          {bike_cond}
        GROUP BY period
        ORDER BY period ASC
        """,
        *args,
    )

    expense_rows = await conn.fetch(
        f"""
        SELECT {exp_bucket} AS period,
               COALESCE(SUM(amount), 0) AS expenses
        FROM expenses
        WHERE park_id = $1
          AND expense_date BETWEEN $2 AND $3
          {bike_cond}
        GROUP BY period
        ORDER BY period ASC
        """,
        *args,
    )

    merged: dict[date, dict] = {}
    for r in revenue_rows:
        merged[r["period"]] = {
            "period": r["period"],
            "revenue": Decimal(str(r["revenue"])),
            "bookings_count": int(r["bookings_count"]),
            "expenses": Decimal("0"),
        }
    for r in expense_rows:
        d = r["period"]
        if d not in merged:
            merged[d] = {
                "period": d,
                "revenue": Decimal("0"),
                "bookings_count": 0,
                "expenses": Decimal("0"),
            }
        merged[d]["expenses"] = Decimal(str(r["expenses"]))

    return sorted(merged.values(), key=lambda x: x["period"])


async def suspicious_expenses(
    conn: asyncpg.Connection, park_id: int
) -> list[dict]:
    """
    Находит байки, у которых за последние 30 дней было >=2 расходов
    одной категории, при этом за предыдущие 60 дней — <=1.
    Возвращает список {bike_id, model, plate_number, category,
    recent_count, prev_count, message}.
    """
    rows = await conn.fetch(
        """
        WITH recent AS (
            SELECT bike_id, category, COUNT(*) AS cnt
            FROM expenses
            WHERE park_id = $1
              AND expense_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - 30
              AND category NOT ILIKE '%топлив%'
              AND category NOT ILIKE '%бензин%'
              AND category NOT ILIKE '%fuel%'
            GROUP BY bike_id, category
            HAVING COUNT(*) >= 2
        ),
        prev AS (
            SELECT bike_id, category, COUNT(*) AS cnt
            FROM expenses
            WHERE park_id = $1
              AND expense_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - 90
              AND expense_date < (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - 30
            GROUP BY bike_id, category
        )
        SELECT r.bike_id, r.category, r.cnt AS recent_count,
               COALESCE(p.cnt, 0) AS prev_count,
               b.model, b.plate_number
        FROM recent r
        LEFT JOIN prev p ON p.bike_id = r.bike_id AND p.category = r.category
        JOIN bikes b ON b.id = r.bike_id
        WHERE COALESCE(p.cnt, 0) <= 1
        """,
        park_id,
    )
    result = []
    for r in rows:
        result.append({
            "bike_id": r["bike_id"],
            "model": r["model"],
            "plate_number": r["plate_number"],
            "category": r["category"],
            "recent_count": int(r["recent_count"]),
            "prev_count": int(r["prev_count"]),
            "message": (
                f"За последние 30 дней '{r['category']}' для {r['model']} "
                f"встречалось {r['recent_count']} раз, а за предыдущие "
                f"60 дней — всего {r['prev_count']}. Возможно, стоит "
                "проверить байк в мастерской."
            ),
        })
    return result
