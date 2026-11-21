import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl

import asyncpg
from fastapi import Depends, Header, HTTPException, Request, status

from app.config import settings
from app.database import get_db

Role = Literal["client", "owner", "super_admin"]


@dataclass
class UserContext:
    telegram_id: int
    role: Role
    is_super_admin: bool
    park_id: int | None
    user: dict


def _validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Проверяет подпись initData. Возвращает распарсенные параметры или None."""
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None

    received_hash = params.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    return params


async def _upsert_user(conn: asyncpg.Connection, user: dict) -> None:
    await conn.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (telegram_id) DO UPDATE
        SET username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name
        """,
        user["id"],
        user.get("username"),
        user.get("first_name"),
        user.get("last_name"),
    )


async def get_current_user(
    request: Request,
    x_mode: str | None = Header(default=None, alias="X-Mode"),
    db: asyncpg.Connection = Depends(get_db),
) -> UserContext:
    """
    Читает initData из заголовка X-Init-Data, валидирует подпись,
    определяет роль. Для супер-админа учитывает X-Mode.
    """
    init_data = request.headers.get("X-Init-Data")
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Init-Data header",
        )

    # WebApp initData подписывается токеном того бота, который открыл Mini App.
    # Для tenant-ботов проверяем токен соответствующего парка, а не только
    # глобальный токен супер-админа. Если park_id/start_param отсутствует
    # (например, приложение открыто через Menu Button), перебираем активные
    # tenant-токены и определяем парк по успешно проверенной подписи.
    raw_params = dict(parse_qsl(init_data, keep_blank_values=True))
    start_param = raw_params.get("start_param") or request.query_params.get("startapp")
    requested_park_id: int | None = None
    if start_param and start_param.startswith("park_"):
        try:
            requested_park_id = int(start_param.removeprefix("park_"))
        except ValueError:
            requested_park_id = None
    if requested_park_id is None:
        try:
            requested_park_id = int(request.query_params.get("park_id", "")) or None
        except ValueError:
            requested_park_id = None

    params = None
    verified_park_id: int | None = None

    if requested_park_id is not None:
        park_auth = await db.fetchrow(
            "SELECT id, bot_token FROM parks WHERE id = $1 AND is_active = TRUE",
            requested_park_id,
        )
        if park_auth and park_auth["bot_token"]:
            params = _validate_init_data(init_data, park_auth["bot_token"])
            if params is not None:
                verified_park_id = int(park_auth["id"])
    else:
        # Menu Button часто открывает URL без start_param/park_id.
        # В таком случае парк надёжно определяется проверкой подписи.
        park_tokens = await db.fetch(
            "SELECT id, bot_token FROM parks WHERE is_active = TRUE AND bot_token IS NOT NULL"
        )
        for park_auth in park_tokens:
            candidate = _validate_init_data(init_data, park_auth["bot_token"])
            if candidate is not None:
                params = candidate
                verified_park_id = int(park_auth["id"])
                break

    # Сохраняем совместимость с главным ботом. Если явно указан park_id,
    # но его токен не подтвердил подпись, не принимаем данные главным токеном.
    if params is None and requested_park_id is None:
        params = _validate_init_data(init_data, settings.bot_token)

    if params is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData signature",
        )

    user_raw = params.get("user")
    if not user_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData has no user",
        )

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user in initData",
        )

    telegram_id = int(user["id"])
    is_super_admin = telegram_id == settings.super_admin_id

    await _upsert_user(db, user)

    # Супер-админ: режим из X-Mode (по умолчанию super_admin)
    # Если initData подтверждён токеном конкретного tenant-бота,
    # сначала применяем роль внутри этого парка. Один Telegram ID может
    # одновременно быть супер-админом платформы и владельцем парка.
    # Супер-админка доступна только при входе через главный бот.
    if is_super_admin and verified_park_id is None:
        mode: Role = "super_admin"
        if x_mode in ("client", "owner", "super_admin"):
            mode = x_mode  # type: ignore[assignment]

        park_id: int | None = None
        if mode == "owner":
            # для супер-админа в режиме owner парк обязателен — берём из query
            park_id_str = request.query_params.get("park_id")
            if park_id_str is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="X-Mode=owner requires ?park_id= query parameter",
                )
            try:
                park_id = int(park_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid park_id",
                )
            exists = await db.fetchval("SELECT 1 FROM parks WHERE id = $1", park_id)
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Park not found",
                )

        return UserContext(
            telegram_id=telegram_id,
            role=mode,
            is_super_admin=True,
            park_id=park_id,
            user=user,
        )

    # Обычный пользователь: ищем, владелец ли он парка
    park_row = None
    if verified_park_id is not None:
        park_row = await db.fetchrow(
            "SELECT id FROM parks WHERE id = $1 AND owner_telegram_id = $2 AND is_active = TRUE",
            verified_park_id,
            telegram_id,
        )
    if park_row is None and verified_park_id is None:
        park_row = await db.fetchrow(
            "SELECT id FROM parks WHERE owner_telegram_id = $1 AND is_active = TRUE",
            telegram_id,
        )
    if park_row:
        return UserContext(
            telegram_id=telegram_id,
            role="owner",
            is_super_admin=False,
            park_id=park_row["id"],
            user=user,
        )

    # Клиент. Парк берём из start_param (?startapp=park_5) или query.
    park_id = verified_park_id
    start_param = params.get("start_param") or request.query_params.get("startapp")
    if park_id is None and start_param and start_param.startswith("park_"):
        try:
            park_id = int(start_param.removeprefix("park_"))
        except ValueError:
            park_id = None
    if park_id is None:
        try:
            park_id = int(request.query_params.get("park_id", "")) or None
        except ValueError:
            park_id = None

    return UserContext(
        telegram_id=telegram_id,
        role="client",
        is_super_admin=False,
        park_id=park_id,
        user=user,
    )


# ============ Зависимости ролей ============

async def require_owner(
    ctx: UserContext = Depends(get_current_user),
) -> UserContext:
    if ctx.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required"
        )
    if ctx.park_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No park bound to user"
        )
    return ctx


async def require_super_admin(
    ctx: UserContext = Depends(get_current_user),
) -> UserContext:
    if not ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super admin only"
        )
    return ctx


async def require_client(
    ctx: UserContext = Depends(get_current_user),
) -> UserContext:
    if ctx.role != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Client access required"
        )
    return ctx