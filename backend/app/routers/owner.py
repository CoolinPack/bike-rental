
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import asyncpg
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.database import get_db
from app.models.schemas import (
    ReorderPhotosRequest,
    OwnerProfile,
    AnalyticsSummary,
    BikeAnalyticsItem,
    BikeAnalyticsListResponse,
    BikeCreate,
    BikeItem,
    BikeListResponse,
    BikeUpdate,
    BookingRejectRequest,
    BookingExtendRequest,
    CategoryAnalyticsItem,
    CategoryAnalyticsListResponse,
    ExpenseCreate,
    ExpenseItem,
    ExpenseListResponse,
    OwnerBookingItem,
    OwnerBookingListResponse,
    TimelineItem,
    TimelineResponse,
)
from app.security import UserContext, require_owner
from app.services import analytics as analytics_service
from app.services import bikes as bikes_service
from app.services import bookings as bookings_service
from app.services import expenses as expenses_service
from app.services import files as files_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/owner", tags=["owner"])


def _park(ctx: UserContext) -> int:
    assert ctx.park_id is not None
    return ctx.park_id


async def _queue_uploaded_media(
    db: asyncpg.Connection,
    park_id: int,
    urls: list[str],
) -> None:
    """
    Ставит загруженные, но не прикреплённые к байку файлы
    в очередь фоновой очистки.
    """
    for url in urls:
        try:
            await bikes_service.queue_media_cleanup(db, park_id, url)
        except Exception:
            logger.exception(
                "Failed to queue uploaded media cleanup for park_id=%s",
                park_id,
            )


def _bike_item(r: dict) -> BikeItem:
    return BikeItem(
        id=r["id"],
        park_id=r["park_id"],
        plate_number=r["plate_number"],
        model=r["model"],
        engine_cc=r["engine_cc"],
        daily_price=r["daily_price"],
        price_3_days=r.get("price_3_days"),
        price_7_days=r.get("price_7_days"),
        price_14_days=r.get("price_14_days"),
        price_30_days=r.get("price_30_days"),
        color=r["color"],
        description=r["description"],
        mileage_km=r["mileage_km"],
        status=r["status"],
        rented_until=r.get("rented_until"),
        photos=list(r["photos"] or []),
        videos=list(r["videos"] or []),
        created_at=r["created_at"],
    )


def _owner_booking_item(r: dict) -> OwnerBookingItem:
    return OwnerBookingItem(
        id=r["id"],
        park_id=r["park_id"],
        bike_id=r["bike_id"],
        plate_number=r["plate_number"],
        model=r["model"],
        photos=list(r["photos"] or []),
        start_date=r["start_date"],
        end_date=r["end_date"],
        total_price=r["total_price"],
        original_total_price=r.get("original_total_price") or r["total_price"],
        extension_total_price=r.get("extension_total_price") or 0,
        status=r["status"],
        created_at=r["created_at"],
        client_name=r.get("client_name"),
        client_phone=r.get("client_phone"),
        client_username=r.get("client_username"),
        deposit_comment=r.get("deposit_comment"),
        client_telegram_id=r["client_telegram_id"],
    )


# ============ BIKES ============

@router.get("/bikes", response_model=BikeListResponse)
async def list_bikes(
    status_filter: str | None = Query(default=None, alias="status"),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await bikes_service.list_bikes(db, _park(ctx), status_filter)
    return BikeListResponse(items=[_bike_item(r) for r in rows], total=len(rows))


@router.post("/bikes", status_code=status.HTTP_201_CREATED)
async def create_bike(
    plate_number: str = Form(...),
    model: str = Form(...),
    engine_cc: int | None = Form(default=None),
    daily_price: str = Form(...),
    price_3_days: str | None = Form(default=None),
    price_7_days: str | None = Form(default=None),
    price_14_days: str | None = Form(default=None),
    price_30_days: str | None = Form(default=None),
    color: str | None = Form(default=None),
    description: str | None = Form(default=None),
    mileage_km: int = Form(default=0),
    bike_status: str = Form(default="available", alias="status"),
    photos: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        price = Decimal(daily_price)
    except InvalidOperation:
        raise HTTPException(400, "daily_price must be a number")

    if bike_status not in ("available", "rented", "maintenance"):
        raise HTTPException(400, "Invalid status")

    if len(photos) > bikes_service.MAX_PHOTOS:
        raise HTTPException(400, f"Max {bikes_service.MAX_PHOTOS} photos")

    if len(videos) > bikes_service.MAX_VIDEOS:
        raise HTTPException(400, f"Max {bikes_service.MAX_VIDEOS} videos")

    photo_urls: list[str] = []
    video_urls: list[str] = []

    try:
        for photo in photos:
            photo_urls.append(
                await files_service.save_upload(
                    photo, "image", _park(ctx)
                )
            )

        for video in videos:
            video_urls.append(
                await files_service.save_upload(
                    video, "video", _park(ctx)
                )
            )

        data = BikeCreate(
            plate_number=plate_number,
            model=model,
            engine_cc=engine_cc,
            daily_price=price,
            price_3_days=Decimal(price_3_days) if price_3_days else None,
            price_7_days=Decimal(price_7_days) if price_7_days else None,
            price_14_days=Decimal(price_14_days) if price_14_days else None,
            price_30_days=Decimal(price_30_days) if price_30_days else None,
            color=color,
            description=description,
            mileage_km=mileage_km,
            status=bike_status,  # type: ignore[arg-type]
        )

        bike_id = await bikes_service.create_bike(
            db, _park(ctx), data, photo_urls, video_urls
        )

    except (ValueError, PermissionError, InvalidOperation) as e:
        await _queue_uploaded_media(
            db, _park(ctx), photo_urls + video_urls
        )
        raise HTTPException(400, str(e))

    except asyncpg.UniqueViolationError:
        await _queue_uploaded_media(
            db, _park(ctx), photo_urls + video_urls
        )
        raise HTTPException(
            409,
            "Bike with this plate_number already exists in your park",
        )

    except Exception:
        await _queue_uploaded_media(
            db, _park(ctx), photo_urls + video_urls
        )
        raise

    return {"id": bike_id}


@router.get("/bikes/{bike_id}", response_model=BikeItem)
async def get_bike(
    bike_id: int,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        row = await bikes_service.get_bike(db, _park(ctx), bike_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    return _bike_item(row)


@router.patch("/bikes/{bike_id}")
async def update_bike(
    bike_id: int,
    data: BikeUpdate,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        await bikes_service.update_bike(db, _park(ctx), bike_id, data)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Bike with this plate_number already exists")
    return {"ok": True}


@router.delete("/bikes/{bike_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bike(
    bike_id: int,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        await bikes_service.delete_bike(db, _park(ctx), bike_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))


# ============ MEDIA ============

@router.post("/bikes/{bike_id}/photos")
async def upload_photo(
    bike_id: int,
    file: UploadFile = File(...),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    url: str | None = None

    try:
        url = await files_service.save_upload(
            file, "image", _park(ctx)
        )

        photos = await bikes_service.add_photo(
            db, _park(ctx), bike_id, url
        )

    except PermissionError as e:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise HTTPException(404, str(e))

    except ValueError as e:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise HTTPException(400, str(e))

    except Exception:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise

    return {"photos": photos}


@router.delete("/bikes/{bike_id}/photos")
async def delete_photo(
    bike_id: int,
    url: str,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        photos = await bikes_service.remove_photo(db, _park(ctx), bike_id, url)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    return {"photos": photos}


@router.post("/bikes/{bike_id}/videos")
async def upload_video(
    bike_id: int,
    file: UploadFile = File(...),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    url: str | None = None

    try:
        url = await files_service.save_upload(
            file, "video", _park(ctx)
        )

        videos = await bikes_service.add_video(
            db, _park(ctx), bike_id, url
        )

    except PermissionError as e:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise HTTPException(404, str(e))

    except ValueError as e:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise HTTPException(400, str(e))

    except Exception:
        if url:
            await _queue_uploaded_media(db, _park(ctx), [url])
        raise

    return {"videos": videos}


@router.delete("/bikes/{bike_id}/videos")
async def delete_video(
    bike_id: int,
    url: str,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        videos = await bikes_service.remove_video(db, _park(ctx), bike_id, url)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    return {"videos": videos}


# ============ EXPENSES ============

@router.get("/expenses", response_model=ExpenseListResponse)
async def list_expenses(
    bike_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await expenses_service.list_expenses(db, _park(ctx), bike_id)
    items = [
        ExpenseItem(
            id=r["id"],
            park_id=r["park_id"],
            bike_id=r["bike_id"],
            plate_number=r["plate_number"],
            model=r["model"],
            category=r["category"],
            amount=r["amount"],
            description=r["description"],
            expense_date=r["expense_date"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return ExpenseListResponse(items=items, total=len(items))


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def add_expense(
    data: ExpenseCreate,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        expense_id = await expenses_service.add_expense(db, _park(ctx), data)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    return {"id": expense_id}


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        await expenses_service.delete_expense(db, _park(ctx), expense_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))


# ============ BOOKING REQUESTS ============

@router.get("/requests", response_model=OwnerBookingListResponse)
async def list_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await bookings_service.list_owner_requests(
        db, _park(ctx), status_filter
    )
    items = [_owner_booking_item(r) for r in rows]
    return OwnerBookingListResponse(items=items, total=len(items))


@router.post("/requests/{booking_id}/accept")
async def accept_request(
    booking_id: int,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        result = await bookings_service.accept_request(db, _park(ctx), booking_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except bookings_service.BookingConflictError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.post("/requests/{booking_id}/reject")
async def reject_request(
    booking_id: int,
    data: BookingRejectRequest,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        await bookings_service.reject_request(
            db, _park(ctx), booking_id, data.reason
        )
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


# ============ ANALYTICS ============

@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    bike_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    f, t = analytics_service.default_period(from_date, to_date)
    data = await analytics_service.summary(db, _park(ctx), f, t, bike_id)
    return AnalyticsSummary(**data)


@router.get("/analytics/bikes", response_model=BikeAnalyticsListResponse)
async def analytics_bikes(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    f, t = analytics_service.default_period(from_date, to_date)
    rows = await analytics_service.by_bikes(db, _park(ctx), f, t)
    items = [BikeAnalyticsItem(**r) for r in rows]
    return BikeAnalyticsListResponse(items=items, total=len(items))


@router.get("/analytics/categories", response_model=CategoryAnalyticsListResponse)
async def analytics_categories(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    bike_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    f, t = analytics_service.default_period(from_date, to_date)
    rows = await analytics_service.by_categories(db, _park(ctx), f, t, bike_id)
    items = [CategoryAnalyticsItem(**r) for r in rows]
    return CategoryAnalyticsListResponse(items=items, total=len(items))


@router.get("/analytics/timeline", response_model=TimelineResponse)
async def analytics_timeline(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    granularity: str = Query(default="day", pattern="^(day|month)$"),
    bike_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    f, t = analytics_service.default_period(from_date, to_date)
    rows = await analytics_service.timeline(
        db, _park(ctx), f, t, granularity, bike_id
    )
    items = [TimelineItem(**r) for r in rows]
    return TimelineResponse(
        items=items, total=len(items), granularity=granularity
    )


# ============ PROFILE ============

@router.get("/me", response_model=OwnerProfile)
async def get_owner_profile(
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    from datetime import datetime as _dt, timezone as _tz

    row = await db.fetchrow(
        """
        SELECT p.id, p.name, p.owner_telegram_id, p.subscription_plan,
               p.subscription_expires_at, p.bikes_limit, p.is_active,
               (SELECT COUNT(*) FROM bikes WHERE park_id = p.id) AS bikes_count
        FROM parks p WHERE p.id = $1
        """,
        _park(ctx),
    )
    if not row:
        raise HTTPException(404, "Park not found")

    now = _dt.now(_tz.utc)
    expires = row["subscription_expires_at"]

    if expires is None:
        is_expired = True
        days_left = 0
    else:
        is_expired = expires < now
        days_left = max(0, (expires - now).days)

    return OwnerProfile(
        park_id=row["id"],
        name=row["name"],
        owner_telegram_id=row["owner_telegram_id"],
        subscription_plan=row["subscription_plan"],
        subscription_expires_at=expires,
        days_left=days_left,
        is_expired=is_expired,
        bikes_limit=row["bikes_limit"],
        bikes_count=int(row["bikes_count"]),
        is_active=row["is_active"],
    )


@router.get("/analytics/suspicious")
async def analytics_suspicious(
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await analytics_service.suspicious_expenses(db, _park(ctx))
    return {"items": rows}


@router.post("/bikes/{bike_id}/photos/reorder")
async def reorder_photos(
    bike_id: int,
    data: ReorderPhotosRequest,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        photos = await bikes_service.reorder_photos(
            db, _park(ctx), bike_id, data.photos
        )
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"photos": photos}


@router.post("/requests/{booking_id}/extend")
async def extend_rental(
    booking_id: int,
    data: BookingExtendRequest,
    ctx: UserContext = Depends(require_owner),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        result = await bookings_service.extend_booking(
            db, _park(ctx), booking_id, data.new_end_date
        )
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result
