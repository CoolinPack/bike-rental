from decimal import Decimal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.models.schemas import (
    BookingItem,
    BookingListResponse,
    BookingRequestCreate,
    ClientBikeItem,
    ClientBikeListResponse,
    ClientCatalogFilters,
)
from app.security import UserContext, require_client
from app.services import bikes as bikes_service
from app.services import bookings as bookings_service

router = APIRouter(prefix="/client", tags=["client"])


def _ensure_park(ctx: UserContext, park_id: int | None) -> int:
    if ctx.is_super_admin:
        if park_id is None:
            raise HTTPException(400, "park_id is required for super admin")
        return park_id
    if ctx.park_id is None:
        raise HTTPException(
            400, "park_id is required (open the Mini App via a park deep link)"
        )
    return ctx.park_id


def _license_required(engine_cc: int | None) -> bool:
    return (engine_cc or 0) > bikes_service.LICENSE_CC_THRESHOLD


def _bike_item(r: dict) -> ClientBikeItem:
    return ClientBikeItem(
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
        license_required=_license_required(r["engine_cc"]),
    )


def _booking_item(r: dict) -> BookingItem:
    return BookingItem(
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
    )


# ============ CATALOG ============

@router.get("/bikes", response_model=ClientBikeListResponse)
async def catalog(
    park_id: int | None = Query(default=None),
    q: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    color: str | None = None,
    min_cc: int | None = None,
    max_cc: int | None = None,
    license_required: bool | None = None,
    include_unavailable: bool = True,
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    filters = ClientCatalogFilters(
        q=q,
        min_price=min_price,
        max_price=max_price,
        color=color,
        min_cc=min_cc,
        max_cc=max_cc,
        license_required=license_required,
        include_unavailable=include_unavailable,
    )
    rows = await bikes_service.client_catalog(db, pid, filters)
    items = [_bike_item(r) for r in rows]
    return ClientBikeListResponse(items=items, total=len(items))


# ============ BOOKING REQUESTS ============

@router.get("/bookings", response_model=BookingListResponse)
async def my_bookings(
    park_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    rows = await bookings_service.list_client_bookings(db, pid, ctx.telegram_id)
    items = [_booking_item(r) for r in rows]
    return BookingListResponse(items=items, total=len(items))


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
async def create_booking_request(
    data: BookingRequestCreate,
    park_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    username = ctx.user.get("username")
    try:
        booking_id = await bookings_service.create_request(
            db, pid, ctx.telegram_id, username, data
        )
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"id": booking_id, "status": "pending"}


@router.get("/bookings/{booking_id}", response_model=BookingItem)
async def get_booking(
    booking_id: int,
    park_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    try:
        row = await bookings_service.get_client_booking(
            db, pid, ctx.telegram_id, booking_id
        )
    except PermissionError as e:
        raise HTTPException(404, str(e))
    return _booking_item(row)


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    park_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    try:
        await bookings_service.cancel_booking(db, pid, ctx.telegram_id, booking_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/bookings/{booking_id}/complete")
async def complete_booking(
    booking_id: int,
    park_id: int | None = Query(default=None),
    ctx: UserContext = Depends(require_client),
    db: asyncpg.Connection = Depends(get_db),
):
    pid = _ensure_park(ctx, park_id)
    try:
        await bookings_service.complete_booking(db, pid, ctx.telegram_id, booking_id)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}