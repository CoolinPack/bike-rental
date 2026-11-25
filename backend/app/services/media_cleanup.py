import asyncio
import logging

from app.database import get_pool
from app.services import files as files_service
from app.services.media_locks import lock_media_urls

logger = logging.getLogger(__name__)

BATCH_SIZE = 25
STALE_AFTER_MINUTES = 10


async def _mark_retry(
    conn, task_id: int, message: str, delay_minutes: int
) -> None:
    await conn.execute(
        """
        UPDATE media_cleanup_queue
        SET status = 'pending',
            next_attempt_at = NOW() + ($2 * INTERVAL '1 minute'),
            last_error = $3,
            updated_at = NOW()
        WHERE id = $1 AND status = 'processing'
        """,
        task_id, delay_minutes, message[:1000],
    )


async def _process_one(pool, row) -> None:
    url = str(row["url"])
    task_id = int(row["id"])

    async with pool.acquire() as conn:
        try:
            # Transaction-scoped advisory lock works with both direct Neon
            # connections and transaction-pooling connection strings. It stays
            # held until storage deletion and queue status update are complete.
            async with conn.transaction():
                await lock_media_urls(conn, [url])

                current = await conn.fetchrow(
                    "SELECT status, attempts FROM media_cleanup_queue WHERE id = $1",
                    task_id,
                )
                # A different worker may have finished while this task waited.
                if not current or current["status"] != "processing":
                    return

                is_used = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM bikes
                        WHERE
                            COALESCE(photos, '[]'::jsonb)
                                @> jsonb_build_array($1::text)
                            OR COALESCE(videos, '[]'::jsonb)
                                @> jsonb_build_array($1::text)
                    )
                    """,
                    url,
                )

                if is_used:
                    await conn.execute(
                        """
                        UPDATE media_cleanup_queue
                        SET status = 'done',
                            last_error = 'Skipped: media URL is still in use',
                            processed_at = NOW(),
                            updated_at = NOW()
                        WHERE id = $1 AND status = 'processing'
                        """,
                        task_id,
                    )
                    return

                # Keep the transaction lock until the blocking storage call ends.
                delete_task = asyncio.create_task(
                    asyncio.to_thread(files_service.delete_upload, url)
                )
                try:
                    ok = await asyncio.shield(delete_task)
                except asyncio.CancelledError:
                    try:
                        await delete_task
                    finally:
                        raise

                if ok:
                    await conn.execute(
                        """
                        UPDATE media_cleanup_queue
                        SET status = 'done', last_error = NULL,
                            processed_at = NOW(), updated_at = NOW()
                        WHERE id = $1 AND status = 'processing'
                        """,
                        task_id,
                    )
                else:
                    attempts = int(current["attempts"])
                    delay = min(60, 2 ** min(attempts, 6))
                    await _mark_retry(
                        conn, task_id,
                        'Storage deletion failed; will retry', delay,
                    )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to process media cleanup task %s", task_id)
            # The transaction above is rolled back on a database error. Requeue
            # in a fresh transaction; if DB is unavailable, stale recovery below
            # will release the task after the configured timeout.
            try:
                async with conn.transaction():
                    await _mark_retry(
                        conn, task_id, 'Unexpected cleanup worker error', 5
                    )
            except Exception:
                logger.exception(
                    "Could not reschedule media cleanup task %s", task_id
                )


async def _process_batch() -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # A stale task may be reclaimed by another process. The advisory
            # lock and status re-check prevent duplicate deletion of one URL.
            await conn.execute(
                """
                UPDATE media_cleanup_queue
                SET status = 'pending', updated_at = NOW()
                WHERE status = 'processing'
                  AND updated_at < NOW() - ($1 * INTERVAL '1 minute')
                """,
                STALE_AFTER_MINUTES,
            )

            rows = await conn.fetch(
                """
                SELECT id, url
                FROM media_cleanup_queue
                WHERE status = 'pending'
                  AND next_attempt_at <= NOW()
                ORDER BY id
                LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                BATCH_SIZE,
            )

            ids = [row["id"] for row in rows]
            if ids:
                await conn.execute(
                    """
                    UPDATE media_cleanup_queue
                    SET status = 'processing',
                        attempts = attempts + 1,
                        updated_at = NOW()
                    WHERE id = ANY($1::bigint[])
                    """,
                    ids,
                )

    for row in rows:
        await _process_one(pool, row)


async def media_cleanup_worker() -> None:
    while True:
        try:
            await _process_batch()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Media cleanup worker failed")

        await asyncio.sleep(60)
