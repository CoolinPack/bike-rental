import asyncpg

from app.models.schemas import BikeCreate, BikeUpdate, ClientCatalogFilters
from app.services import files as files_service


MAX_PHOTOS = 5
MAX_VIDEOS = 1
LICENSE_CC_THRESHOLD = 50


async def _assert_bike_in_park(
    conn: asyncpg.Connection, bike_id: int, park_id: int
) -> dict:
    row = await conn.fetchrow(
        "SELECT * FROM bikes WHERE id = $1 AND park_id = $2", bike_id, park_id
    )
    if not row:
        raise PermissionError("Bike not found in your park")
    return dict(row)


async def create_bike(
    conn: asyncpg.Connection,
    park_id: int,
    data: BikeCreate,
    photo_urls: list[str],
    video_urls: list[str],
) -> int:
    # Проверка лимита тарифа
    limit_row = await conn.fetchrow(
        "SELECT p.bikes_limit, "
        "(SELECT COUNT(*) FROM bikes WHERE park_id = p.id) AS cnt "
        "FROM parks p WHERE p.id = $1",
        park_id,
    )
    if limit_row and int(limit_row["cnt"]) >= int(limit_row["bikes_limit"]):
        raise ValueError(
            f"Достигнут лимит байков ({limit_row['bikes_limit']}). "
            "Перейдите на тариф Про."
        )

    if len(photo_urls) > MAX_PHOTOS:
        raise ValueError(f"Max {MAX_PHOTOS} photos")
    if len(video_urls) > MAX_VIDEOS:
        raise ValueError(f"Max {MAX_VIDEOS} videos")

    bike_id = await conn.fetchval(
        """
        INSERT INTO bikes (
            park_id, plate_number, model, engine_cc, daily_price,
            price_3_days, price_7_days, price_14_days, price_30_days,
            color, description, mileage_km, status, photos, videos
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        RETURNING id
        """,
        park_id,
        data.plate_number,
        data.model,
        data.engine_cc,
        data.daily_price,
        data.price_3_days,
        data.price_7_days,
        data.price_14_days,
        data.price_30_days,
        data.color,
        data.description,
        data.mileage_km,
        data.status,
        photo_urls,
        video_urls,
    )
    return int(bike_id)


async def list_bikes(
    conn: asyncpg.Connection, park_id: int, status_filter: str | None = None
) -> list[dict]:
    if status_filter:
        rows = await conn.fetch(
            """SELECT b.*,
               (SELECT MAX(end_date) FROM bookings bk
                WHERE bk.bike_id=b.id AND bk.park_id=b.park_id AND bk.status='active'
                  AND bk.start_date <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  AND bk.end_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) AS rented_until
               FROM bikes b WHERE b.park_id = $1 AND b.status = $2 ORDER BY b.id DESC""",
            park_id, status_filter,
        )
    else:
        rows = await conn.fetch(
            """SELECT b.*,
               (SELECT MAX(end_date) FROM bookings bk
                WHERE bk.bike_id=b.id AND bk.park_id=b.park_id AND bk.status='active'
                  AND bk.start_date <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  AND bk.end_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) AS rented_until
               FROM bikes b WHERE b.park_id = $1 ORDER BY b.id DESC""", park_id
        )
    return [dict(r) for r in rows]


async def client_catalog(
    conn: asyncpg.Connection, park_id: int, f: ClientCatalogFilters
) -> list[dict]:
    """
    Каталог для клиента с поиском/фильтрами.
    По умолчанию включает и available, и rented, и maintenance —
    чтобы клиент видел занятость.
    """
    where = ["park_id = $1"]
    args: list = [park_id]
    idx = 2

    if not f.include_unavailable:
        where.append("status = 'available'")

    if f.q:
        where.append(f"(model ILIKE ${idx} OR plate_number ILIKE ${idx})")
        args.append(f"%{f.q}%")
        idx += 1

    if f.min_price is not None:
        where.append(f"daily_price >= ${idx}")
        args.append(f.min_price)
        idx += 1

    if f.max_price is not None:
        where.append(f"daily_price <= ${idx}")
        args.append(f.max_price)
        idx += 1

    if f.color:
        where.append(f"color ILIKE ${idx}")
        args.append(f"%{f.color}%")
        idx += 1

    if f.min_cc is not None:
        where.append(f"COALESCE(engine_cc, 0) >= ${idx}")
        args.append(f.min_cc)
        idx += 1

    if f.max_cc is not None:
        where.append(f"COALESCE(engine_cc, 0) <= ${idx}")
        args.append(f.max_cc)
        idx += 1

    if f.license_required is True:
        where.append(f"COALESCE(engine_cc, 0) > {LICENSE_CC_THRESHOLD}")
    elif f.license_required is False:
        where.append(f"COALESCE(engine_cc, 0) <= {LICENSE_CC_THRESHOLD}")

    query = (
        "SELECT id, park_id, plate_number, model, engine_cc, daily_price, "
        "price_3_days, price_7_days, price_14_days, price_30_days, "
        "color, description, mileage_km, status, photos, videos, created_at, "
        "(SELECT MAX(end_date) FROM bookings bk WHERE bk.bike_id=bikes.id "
        "AND bk.park_id=bikes.park_id AND bk.status='active' "
        "AND bk.start_date <= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date "
        "AND bk.end_date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) AS rented_until "
        "FROM bikes WHERE "
        + " AND ".join(where)
        + " ORDER BY (status = 'available') DESC, id DESC"
    )
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


async def get_bike(conn: asyncpg.Connection, park_id: int, bike_id: int) -> dict:
    return await _assert_bike_in_park(conn, bike_id, park_id)


async def update_bike(
    conn: asyncpg.Connection, park_id: int, bike_id: int, data: BikeUpdate
) -> None:
    await _assert_bike_in_park(conn, bike_id, park_id)

    fields = []
    args: list = []
    idx = 1
    provided = getattr(data, "model_fields_set", getattr(data, "__fields_set__", set()))
    tier_fields = {"price_3_days", "price_7_days", "price_14_days", "price_30_days"}
    for field in ("plate_number", "model", "engine_cc", "daily_price",
                  "price_3_days", "price_7_days", "price_14_days", "price_30_days",
                  "color", "description", "mileage_km", "status"):
        value = getattr(data, field)
        if value is not None or (field in tier_fields and field in provided):
            fields.append(f"{field} = ${idx}")
            args.append(value)
            idx += 1

    if not fields:
        return
    args.extend([bike_id, park_id])
    query = (
        f"UPDATE bikes SET {', '.join(fields)} "
        f"WHERE id = ${idx} AND park_id = ${idx + 1}"
    )
    await conn.execute(query, *args)


async def delete_bike(
    conn: asyncpg.Connection, park_id: int, bike_id: int
) -> None:
    bike = await _assert_bike_in_park(conn, bike_id, park_id)
    await conn.execute(
        "DELETE FROM bikes WHERE id = $1 AND park_id = $2", bike_id, park_id
    )
    for url in (bike.get("photos") or []):
        files_service.delete_upload(url)
    for url in (bike.get("videos") or []):
        files_service.delete_upload(url)


async def add_photo(
    conn: asyncpg.Connection, park_id: int, bike_id: int, url: str
) -> list[str]:
    row = await conn.fetchrow(
        """
        UPDATE bikes
        SET photos = photos || to_jsonb($1::text)
        WHERE id = $2 AND park_id = $3
          AND jsonb_array_length(photos) < $4
        RETURNING photos
        """,
        url, bike_id, park_id, MAX_PHOTOS,
    )
    if row:
        return list(row["photos"] or [])
    exists = await conn.fetchval(
        "SELECT 1 FROM bikes WHERE id=$1 AND park_id=$2", bike_id, park_id
    )
    if not exists:
        raise PermissionError("Bike not found in your park")
    raise ValueError(f"Max {MAX_PHOTOS} photos per bike")


async def remove_photo(
    conn: asyncpg.Connection, park_id: int, bike_id: int, url: str
) -> list[str]:
    bike = await _assert_bike_in_park(conn, bike_id, park_id)
    photos = list(bike.get("photos") or [])
    removed = url in photos
    if removed:
        photos.remove(url)
    await conn.execute(
        "UPDATE bikes SET photos = $1 WHERE id = $2 AND park_id = $3",
        photos, bike_id, park_id,
    )
    if removed:
        files_service.delete_upload(url)
    return photos


async def add_video(
    conn: asyncpg.Connection, park_id: int, bike_id: int, url: str
) -> list[str]:
    row = await conn.fetchrow(
        """
        UPDATE bikes
        SET videos = videos || to_jsonb($1::text)
        WHERE id = $2 AND park_id = $3
          AND jsonb_array_length(videos) < $4
        RETURNING videos
        """,
        url, bike_id, park_id, MAX_VIDEOS,
    )
    if row:
        return list(row["videos"] or [])
    exists = await conn.fetchval(
        "SELECT 1 FROM bikes WHERE id=$1 AND park_id=$2", bike_id, park_id
    )
    if not exists:
        raise PermissionError("Bike not found in your park")
    raise ValueError(f"Max {MAX_VIDEOS} videos per bike")


async def remove_video(
    conn: asyncpg.Connection, park_id: int, bike_id: int, url: str
) -> list[str]:
    bike = await _assert_bike_in_park(conn, bike_id, park_id)
    videos = list(bike.get("videos") or [])
    removed = url in videos
    if removed:
        videos.remove(url)
    await conn.execute(
        "UPDATE bikes SET videos = $1 WHERE id = $2 AND park_id = $3",
        videos, bike_id, park_id,
    )
    if removed:
        files_service.delete_upload(url)
    return videos


async def reorder_photos(
    conn: asyncpg.Connection,
    park_id: int,
    bike_id: int,
    new_order: list[str],
) -> list[str]:
    """Переставить фото в нужном порядке. Все URL должны быть из текущего списка."""
    bike = await _assert_bike_in_park(conn, bike_id, park_id)
    current = list(bike.get("photos") or [])

    if set(new_order) != set(current):
        raise ValueError("Новый порядок должен содержать те же фото")

    await conn.execute(
        "UPDATE bikes SET photos = $1 WHERE id = $2 AND park_id = $3",
        new_order, bike_id, park_id,
    )
    return new_order
