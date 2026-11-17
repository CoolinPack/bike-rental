from decimal import Decimal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.models.schemas import (
    ChangePlanRequest,
    ExtendSubscriptionRequest,
    MyRevenueSummary,
    ParkCreate,
    ParkItem,
    ParkListResponse,
    ParkRevenueItem,
    ParkUpdate,
    PaymentConfirmRequest,
    PaymentRequestCreate,
    PaymentRequestItem,
    SuperAdminSummary,
)
from app.security import UserContext, require_super_admin
from app.services import parks as parks_service

router = APIRouter(prefix="/super", tags=["super_admin"])


# ============ PARKS ============

@router.get("/parks", response_model=ParkListResponse)
async def list_parks(
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await parks_service.list_parks(db)
    items = [
        ParkItem(
            id=r["id"],
            name=r["name"],
            owner_telegram_id=r["owner_telegram_id"],
            subscription_plan=r["subscription_plan"],
            subscription_expires_at=r["subscription_expires_at"],
            custom_price_usd=r["custom_price_usd"],
            discount_percent=r["discount_percent"],
            referred_by_park_id=r["referred_by_park_id"],
            is_active=r["is_active"],
            created_at=r["created_at"],
            bikes_count=int(r["bikes_count"]),
            bookings_count=int(r["bookings_count"]),
            revenue_usd=Decimal(str(r["revenue_usd"])),
        )
        for r in rows
    ]
    return ParkListResponse(items=items, total=len(items))


@router.post("/parks", status_code=status.HTTP_201_CREATED)
async def create_park(
    data: ParkCreate,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    if data.subscription_months not in (1, 3):
        raise HTTPException(400, "subscription_months must be 1 or 3")
    try:
        park_id = await parks_service.create_park(db, data)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Park with this owner_telegram_id already exists")
    return {"id": park_id}


@router.get("/parks/{park_id}")
async def get_park(
    park_id: int,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    park = await parks_service.get_park(db, park_id)
    if not park:
        raise HTTPException(404, "Park not found")
    return park


@router.patch("/parks/{park_id}")
async def update_park(
    park_id: int,
    data: ParkUpdate,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    park = await parks_service.get_park(db, park_id)
    if not park:
        raise HTTPException(404, "Park not found")
    await parks_service.update_park(db, park_id, data)
    return {"ok": True}


@router.delete("/parks/{park_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_park(
    park_id: int,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    park = await parks_service.get_park(db, park_id)
    if not park:
        raise HTTPException(404, "Park not found")
    await parks_service.delete_park(db, park_id)


# ============ PAYMENTS ============

@router.post("/parks/{park_id}/payments", status_code=status.HTTP_201_CREATED)
async def create_payment_request(
    park_id: int,
    data: PaymentRequestCreate,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    if data.months not in (1, 3):
        raise HTTPException(400, "months must be 1 or 3")
    try:
        req_id = await parks_service.create_payment_request(db, park_id, data.months)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"id": req_id}


@router.get("/payments", response_model=list[PaymentRequestItem])
async def list_payments(
    status_filter: str | None = Query(default=None, alias="status"),
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    rows = await parks_service.list_payment_requests(db, status_filter)
    return [
        PaymentRequestItem(
            id=r["id"],
            park_id=r["park_id"],
            park_name=r["park_name"],
            amount_usd=Decimal(str(r["amount_usd"])),
            months=r["months"],
            status=r["status"],
            requested_at=r["requested_at"],
            confirmed_at=r["confirmed_at"],
        )
        for r in rows
    ]


@router.post("/payments/{request_id}/confirm")
async def confirm_payment(
    request_id: int,
    data: PaymentConfirmRequest,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        result = await parks_service.confirm_payment(db, request_id, data.amount_usd)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.post("/payments/{request_id}/reject")
async def reject_payment(
    request_id: int,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    row = await db.fetchrow(
        "SELECT status FROM payment_requests WHERE id = $1", request_id
    )
    if not row:
        raise HTTPException(404, "Payment request not found")
    if row["status"] != "pending":
        raise HTTPException(400, f"Payment request is {row['status']}")
    await db.execute(
        "UPDATE payment_requests SET status = 'rejected' WHERE id = $1", request_id
    )
    return {"ok": True}


# ============ ANALYTICS ============

@router.get("/summary", response_model=SuperAdminSummary)
async def summary(
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    data = await parks_service.super_admin_summary(db)
    return SuperAdminSummary(**data)


# ============ SaaS MANAGEMENT ============

@router.post("/parks/{park_id}/change-plan")
async def change_plan(
    park_id: int,
    data: ChangePlanRequest,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    try:
        result = await parks_service.change_plan(db, park_id, data.new_plan)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.post("/parks/{park_id}/extend")
async def extend_subscription(
    park_id: int,
    data: ExtendSubscriptionRequest,
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    if data.months not in (1, 3):
        raise HTTPException(400, "months must be 1 or 3")
    try:
        result = await parks_service.extend_subscription(db, park_id, data.months)
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.get("/my-revenue", response_model=MyRevenueSummary)
async def my_revenue(
    ctx: UserContext = Depends(require_super_admin),
    db: asyncpg.Connection = Depends(get_db),
):
    data = await parks_service.my_revenue_summary(db)
    return MyRevenueSummary(
        total_confirmed_revenue=data["total_confirmed_revenue"],
        this_month_revenue=data["this_month_revenue"],
        parks_total=data["parks_total"],
        parks_active=data["parks_active"],
        parks_expired=data["parks_expired"],
        parks_disabled=data["parks_disabled"],
        parks=[ParkRevenueItem(**p) for p in data["parks"]],
    )
