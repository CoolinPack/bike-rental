-- Новые поля в bookings
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS client_name TEXT,
    ADD COLUMN IF NOT EXISTS client_phone TEXT,
    ADD COLUMN IF NOT EXISTS client_username TEXT,
    ADD COLUMN IF NOT EXISTS deposit_comment TEXT,
    ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;

-- Статусная модель броней расширяется
ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_status_check;
ALTER TABLE bookings
    ADD CONSTRAINT bookings_status_check
    CHECK (status IN ('pending', 'active', 'completed', 'cancelled', 'rejected'));

-- Дедлайн уведомления (чтобы не отправлять повторно)
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_bookings_pending_park
    ON bookings(park_id, status, created_at DESC);

-- Индекс для быстрого поиска пересечений заявок
CREATE INDEX IF NOT EXISTS idx_bookings_bike_dates_status
    ON bookings(bike_id, start_date, end_date, status);