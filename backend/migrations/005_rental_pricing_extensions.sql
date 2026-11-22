-- Safe additive migration: rental price tiers, extension history and separate reminder flags.
ALTER TABLE bikes
  ADD COLUMN IF NOT EXISTS price_3_days NUMERIC(10,2),
  ADD COLUMN IF NOT EXISTS price_7_days NUMERIC(10,2),
  ADD COLUMN IF NOT EXISTS price_14_days NUMERIC(10,2),
  ADD COLUMN IF NOT EXISTS price_30_days NUMERIC(10,2);

ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS original_total_price NUMERIC(10,2),
  ADD COLUMN IF NOT EXISTS extension_total_price NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS reminder_3_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS reminder_1_sent_at TIMESTAMPTZ;

UPDATE bookings
SET original_total_price = total_price
WHERE original_total_price IS NULL;

CREATE TABLE IF NOT EXISTS booking_extensions (
  id BIGSERIAL PRIMARY KEY,
  booking_id INT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
  old_end_date DATE NOT NULL,
  new_end_date DATE NOT NULL,
  days_added INT NOT NULL CHECK (days_added > 0),
  daily_price NUMERIC(10,2) NOT NULL CHECK (daily_price >= 0),
  amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_booking_extensions_booking
  ON booking_extensions(booking_id, created_at);
