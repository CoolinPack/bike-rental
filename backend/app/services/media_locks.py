"""Concurrency helpers for media URLs shared by bikes and cleanup workers."""

from collections.abc import Iterable

import asyncpg


def normalize_media_urls(urls: Iterable[str | None]) -> list[str]:
    """Return non-empty unique URLs in a deterministic lock order."""
    return sorted({str(url) for url in urls if url})


async def lock_media_urls(
    conn: asyncpg.Connection, urls: Iterable[str | None]
) -> list[str]:
    """Acquire transaction-scoped advisory locks for all URLs."""
    normalized = normalize_media_urls(urls)
    for url in normalized:
        await conn.fetchval(
            "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", url
        )
    return normalized


async def ensure_media_attachable(
    conn: asyncpg.Connection, urls: Iterable[str | None]
) -> None:
    """Cancel pending cleanup before attaching a URL; reject active/deleted URLs."""
    for url in normalize_media_urls(urls):
        row = await conn.fetchrow(
            "SELECT status FROM media_cleanup_queue WHERE url = $1 FOR UPDATE",
            url,
        )
        if not row:
            continue

        if row["status"] in ("processing", "done"):
            # A worker may have marked a still-referenced URL as skipped.
            # Reuse is safe only while another bike still references the file.
            is_still_used = await conn.fetchval(
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
            if is_still_used:
                continue
            raise ValueError(
                "Этот медиафайл уже передан на удаление. Загрузите его заново."
            )

        await conn.execute(
            """
            UPDATE media_cleanup_queue
            SET status = 'done',
                last_error = 'Cancelled: media URL attached again',
                processed_at = NOW(),
                updated_at = NOW()
            WHERE url = $1 AND status = 'pending'
            """,
            url,
        )
