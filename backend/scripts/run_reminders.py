import asyncio
from app.database import init_pool, close_pool
from app.bot.reminders import _process_reminders


async def main():
    await init_pool()
    try:
        await _process_reminders()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
