"""
Генератор валидного Telegram initData для тестов.

Использование:
    python -m scripts.make_init_data --user-id 123456789
    python -m scripts.make_init_data --user-id 999 --start-param park_1
"""
import argparse
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from app.config import settings


def make_init_data(
    user_id: int,
    first_name: str = "Test",
    username: str | None = "testuser",
    start_param: str | None = None,
) -> str:
    user = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "language_code": "ru",
    }
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "AAF03-test",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    if start_param:
        params["start_param"] = start_param

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    params["hash"] = calculated_hash
    return urlencode(params)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--first-name", default="Test")
    parser.add_argument("--username", default="testuser")
    parser.add_argument("--start-param", default=None)
    args = parser.parse_args()

    print(make_init_data(
        args.user_id,
        args.first_name,
        args.username,
        args.start_param,
    ))