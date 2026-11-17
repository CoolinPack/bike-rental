import asyncpg

from app.models.schemas import ExpenseCreate


async def add_expense(
    conn: asyncpg.Connection, park_id: int, data: ExpenseCreate
) -> int:
    ok = await conn.fetchval(
        "SELECT 1 FROM bikes WHERE id = $1 AND park_id = $2",
        data.bike_id, park_id,
    )
    if not ok:
        raise PermissionError("Bike not found in your park")

    expense_id = await conn.fetchval(
        """
        INSERT INTO expenses (
            park_id, bike_id, category, amount, description, expense_date
        ) VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        park_id,
        data.bike_id,
        data.category,
        data.amount,
        data.description,
        data.expense_date,
    )
    return int(expense_id)


async def list_expenses(
    conn: asyncpg.Connection,
    park_id: int,
    bike_id: int | None = None,
) -> list[dict]:
    if bike_id is not None:
        rows = await conn.fetch(
            """
            SELECT e.*, b.plate_number, b.model
            FROM expenses e
            JOIN bikes b ON b.id = e.bike_id
            WHERE e.park_id = $1 AND e.bike_id = $2
            ORDER BY e.expense_date DESC, e.id DESC
            """,
            park_id, bike_id,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT e.*, b.plate_number, b.model
            FROM expenses e
            JOIN bikes b ON b.id = e.bike_id
            WHERE e.park_id = $1
            ORDER BY e.expense_date DESC, e.id DESC
            """,
            park_id,
        )
    return [dict(r) for r in rows]


async def delete_expense(
    conn: asyncpg.Connection, park_id: int, expense_id: int
) -> None:
    result = await conn.execute(
        "DELETE FROM expenses WHERE id = $1 AND park_id = $2",
        expense_id, park_id,
    )
    if result == "DELETE 0":
        raise PermissionError("Expense not found in your park")