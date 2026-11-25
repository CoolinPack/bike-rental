-- 006_tenant_integrity.sql
-- Strengthen tenant isolation with composite foreign keys.
-- This migration intentionally aborts if legacy rows already cross park boundaries.
-- Run a database backup before applying it.

DO $$
DECLARE
  bad_bookings BIGINT;
  bad_expenses BIGINT;
  bad_extensions BIGINT;
BEGIN
  SELECT COUNT(*) INTO bad_bookings
  FROM bookings bk JOIN bikes b ON b.id = bk.bike_id
  WHERE bk.park_id <> b.park_id;

  SELECT COUNT(*) INTO bad_expenses
  FROM expenses e JOIN bikes b ON b.id = e.bike_id
  WHERE e.park_id <> b.park_id;

  SELECT COUNT(*) INTO bad_extensions
  FROM booking_extensions be JOIN bookings bk ON bk.id = be.booking_id
  WHERE be.park_id <> bk.park_id;

  IF bad_bookings > 0 OR bad_expenses > 0 OR bad_extensions > 0 THEN
    RAISE EXCEPTION
      'Tenant integrity migration stopped: mismatched rows found (bookings=%, expenses=%, booking_extensions=%). Correct these rows before retrying.',
      bad_bookings, bad_expenses, bad_extensions;
  END IF;
END $$;

-- PostgreSQL requires a unique key matching the referenced composite columns.
CREATE UNIQUE INDEX IF NOT EXISTS uq_bikes_id_park_id
  ON bikes(id, park_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_id_park_id
  ON bookings(id, park_id);

-- A booking may only reference a bike belonging to the same park.
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fk_bookings_bike_same_park'
      AND conrelid = 'bookings'::regclass
  ) THEN
    ALTER TABLE bookings
      ADD CONSTRAINT fk_bookings_bike_same_park
      FOREIGN KEY (bike_id, park_id)
      REFERENCES bikes(id, park_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
END $$;
ALTER TABLE bookings VALIDATE CONSTRAINT fk_bookings_bike_same_park;

-- An expense may only reference a bike belonging to the same park.
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fk_expenses_bike_same_park'
      AND conrelid = 'expenses'::regclass
  ) THEN
    ALTER TABLE expenses
      ADD CONSTRAINT fk_expenses_bike_same_park
      FOREIGN KEY (bike_id, park_id)
      REFERENCES bikes(id, park_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
END $$;
ALTER TABLE expenses VALIDATE CONSTRAINT fk_expenses_bike_same_park;

-- An extension record may only reference a booking belonging to the same park.
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fk_booking_extensions_booking_same_park'
      AND conrelid = 'booking_extensions'::regclass
  ) THEN
    ALTER TABLE booking_extensions
      ADD CONSTRAINT fk_booking_extensions_booking_same_park
      FOREIGN KEY (booking_id, park_id)
      REFERENCES bookings(id, park_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
END $$;
ALTER TABLE booking_extensions VALIDATE CONSTRAINT fk_booking_extensions_booking_same_park;


-- Durable retry queue for object deletion. It deliberately has no FK to parks,
-- because the queue must survive deleting a park.
CREATE TABLE IF NOT EXISTS media_cleanup_queue (
  id BIGSERIAL PRIMARY KEY,
  source_park_id INT,
  url TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'done')),
  attempts INT NOT NULL DEFAULT 0,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_media_cleanup_pending
  ON media_cleanup_queue(status, next_attempt_at, id);
