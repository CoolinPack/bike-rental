from fastapi import APIRouter, Depends

from app.models.schemas import MeResponse, TelegramUser
from app.security import UserContext, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def me(ctx: UserContext = Depends(get_current_user)):
    return MeResponse(
        telegram_id=ctx.telegram_id,
        role=ctx.role,
        is_super_admin=ctx.is_super_admin,
        park_id=ctx.park_id,
        user=TelegramUser(**{
            k: ctx.user.get(k)
            for k in ("id", "first_name", "last_name", "username", "language_code")
        }),
    )