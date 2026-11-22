from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["client", "owner", "super_admin"]
BikeStatus = Literal["available", "rented", "maintenance"]
BookingStatus = Literal["pending", "active", "completed", "cancelled", "rejected"]


# ============ AUTH ============

class TelegramUser(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class MeResponse(BaseModel):
    telegram_id: int
    role: Role
    is_super_admin: bool
    park_id: int | None = None
    park_name: str | None = None
    user: TelegramUser


# ============ PARKS ============

class ParkCreate(BaseModel):
    name: str
    owner_telegram_id: int
    bot_token: str | None = None
    subscription_plan: Literal["start", "pro"] = "start"
    subscription_months: int = 1
    custom_price_usd: Decimal | None = None
    discount_percent: Decimal = Decimal("0")
    referred_by_park_id: int | None = None


class ParkUpdate(BaseModel):
    name: str | None = None
    owner_telegram_id: int | None = None
    bot_token: str | None = None
    subscription_plan: Literal["start", "pro"] | None = None
    custom_price_usd: Decimal | None = None
    discount_percent: Decimal | None = None
    is_active: bool | None = None


class ParkItem(BaseModel):
    id: int
    name: str
    owner_telegram_id: int
    subscription_plan: str
    subscription_expires_at: datetime | None
    custom_price_usd: Decimal | None
    discount_percent: Decimal
    referred_by_park_id: int | None
    is_active: bool
    created_at: datetime
    bikes_count: int
    bookings_count: int
    revenue_usd: Decimal
    bot_token_configured: bool = False


class ParkListResponse(BaseModel):
    items: list[ParkItem]
    total: int


# ============ PAYMENT REQUESTS ============

class PaymentRequestCreate(BaseModel):
    months: int


class PaymentRequestItem(BaseModel):
    id: int
    park_id: int
    park_name: str
    amount_usd: Decimal
    months: int
    status: str
    requested_at: datetime
    confirmed_at: datetime | None


class PaymentConfirmRequest(BaseModel):
    amount_usd: Decimal | None = None


# ============ SUPER ADMIN ANALYTICS ============

class SuperAdminSummary(BaseModel):
    parks_total: int
    parks_active: int
    bikes_total: int
    bookings_total: int
    revenue_total_usd: Decimal
    pending_payments: int


# ============ BIKES ============

class BikeCreate(BaseModel):
    plate_number: str
    model: str
    engine_cc: int | None = None
    daily_price: Decimal
    price_3_days: Decimal | None = None
    price_7_days: Decimal | None = None
    price_14_days: Decimal | None = None
    price_30_days: Decimal | None = None
    color: str | None = None
    description: str | None = None
    mileage_km: int = 0
    status: BikeStatus = "available"


class BikeUpdate(BaseModel):
    plate_number: str | None = None
    model: str | None = None
    engine_cc: int | None = None
    daily_price: Decimal | None = None
    price_3_days: Decimal | None = None
    price_7_days: Decimal | None = None
    price_14_days: Decimal | None = None
    price_30_days: Decimal | None = None
    color: str | None = None
    description: str | None = None
    mileage_km: int | None = None
    status: BikeStatus | None = None


class BikeItem(BaseModel):
    id: int
    park_id: int
    plate_number: str
    model: str
    engine_cc: int | None
    daily_price: Decimal
    price_3_days: Decimal | None = None
    price_7_days: Decimal | None = None
    price_14_days: Decimal | None = None
    price_30_days: Decimal | None = None
    color: str | None
    description: str | None
    mileage_km: int
    status: str
    rented_until: date | None = None
    photos: list[str]
    videos: list[str]
    created_at: datetime


class BikeListResponse(BaseModel):
    items: list[BikeItem]
    total: int


# ============ EXPENSES ============

class ExpenseCreate(BaseModel):
    bike_id: int
    category: str
    amount: Decimal
    description: str | None = None
    expense_date: date


class ExpenseItem(BaseModel):
    id: int
    park_id: int
    bike_id: int
    plate_number: str
    model: str
    category: str
    amount: Decimal
    description: str | None
    expense_date: date
    created_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseItem]
    total: int


# ============ CLIENT CATALOG ============

class ClientBikeItem(BaseModel):
    id: int
    park_id: int
    plate_number: str
    model: str
    engine_cc: int | None
    daily_price: Decimal
    price_3_days: Decimal | None = None
    price_7_days: Decimal | None = None
    price_14_days: Decimal | None = None
    price_30_days: Decimal | None = None
    color: str | None
    description: str | None
    mileage_km: int
    status: str
    rented_until: date | None = None
    photos: list[str]
    videos: list[str]
    license_required: bool


class ClientBikeListResponse(BaseModel):
    items: list[ClientBikeItem]
    total: int


class ClientCatalogFilters(BaseModel):
    q: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    color: str | None = None
    min_cc: int | None = None
    max_cc: int | None = None
    license_required: bool | None = None
    include_unavailable: bool = True


# ============ CLIENT BOOKINGS ============

class BookingRequestCreate(BaseModel):
    bike_id: int
    start_date: date
    end_date: date
    client_name: str = Field(min_length=1, max_length=100)
    client_phone: str = Field(min_length=3, max_length=30)
    deposit_comment: str = Field(min_length=1, max_length=500)


class BookingItem(BaseModel):
    id: int
    park_id: int
    bike_id: int
    plate_number: str
    model: str
    photos: list[str]
    start_date: date
    end_date: date
    total_price: Decimal
    original_total_price: Decimal | None = None
    extension_total_price: Decimal = Decimal("0")
    status: str
    created_at: datetime
    client_name: str | None = None
    client_phone: str | None = None
    client_username: str | None = None
    deposit_comment: str | None = None


class BookingListResponse(BaseModel):
    items: list[BookingItem]
    total: int


# ============ OWNER: BOOKING REQUESTS ============

class OwnerBookingItem(BookingItem):
    client_telegram_id: int


class OwnerBookingListResponse(BaseModel):
    items: list[OwnerBookingItem]
    total: int


class BookingRejectRequest(BaseModel):
    reason: str | None = None


class BookingExtendRequest(BaseModel):
    new_end_date: date

# ============ OWNER ANALYTICS ============

class AnalyticsSummary(BaseModel):
    from_date: date
    to_date: date
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    bookings_count: int
    avg_ticket: Decimal


class BikeAnalyticsItem(BaseModel):
    bike_id: int
    plate_number: str
    model: str
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    profitability_percent: Decimal
    bookings_count: int
    rented_days: int
    idle_days: int
    utilization_percent: Decimal
    revenue_per_day: Decimal
    avg_rental_days: Decimal


class BikeAnalyticsListResponse(BaseModel):
    items: list[BikeAnalyticsItem]
    total: int


class CategoryAnalyticsItem(BaseModel):
    category: str
    total: Decimal
    count: int


class CategoryAnalyticsListResponse(BaseModel):
    items: list[CategoryAnalyticsItem]
    total: int


class TimelineItem(BaseModel):
    period: date
    revenue: Decimal
    expenses: Decimal
    bookings_count: int


class TimelineResponse(BaseModel):
    items: list[TimelineItem]
    total: int
    granularity: str


# ============ SUPER ADMIN SaaS ============

class ChangePlanRequest(BaseModel):
    new_plan: Literal["start", "pro"]


class ExtendSubscriptionRequest(BaseModel):
    months: int


class ParkRevenueItem(BaseModel):
    park_id: int
    name: str
    total_paid: Decimal
    last_paid_at: datetime | None
    subscription_expires_at: datetime | None
    is_active: bool
    subscription_plan: str
    bikes_limit: int
    is_expired: bool
    days_left: int


class MyRevenueSummary(BaseModel):
    total_confirmed_revenue: Decimal
    this_month_revenue: Decimal
    parks_total: int
    parks_active: int
    parks_expired: int
    parks_disabled: int
    parks: list[ParkRevenueItem]


# ============ OWNER PROFILE ============

class OwnerProfile(BaseModel):
    park_id: int
    name: str
    owner_telegram_id: int
    subscription_plan: str
    subscription_expires_at: datetime | None
    days_left: int
    is_expired: bool
    bikes_limit: int
    bikes_count: int
    is_active: bool


# ============ PHOTO REORDER ============

class ReorderPhotosRequest(BaseModel):
    photos: list[str]
