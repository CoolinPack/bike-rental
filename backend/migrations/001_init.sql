-- ============ USERS ============
CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============ PARKS ============
CREATE TABLE parks (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    owner_telegram_id BIGINT NOT NULL UNIQUE,
    bot_token TEXT,
    subscription_plan TEXT NOT NULL DEFAULT 'start'
        CHECK (subscription_plan IN ('start', 'pro')),
    subscription_expires_at TIMESTAMPTZ,
    custom_price_usd NUMERIC(10, 2),
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    referred_by_park_id INT REFERENCES parks(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_parks_owner ON parks(owner_telegram_id);

-- ============ BIKES ============
CREATE TABLE bikes (
    id SERIAL PRIMARY KEY,
    park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
    plate_number TEXT NOT NULL,
    model TEXT NOT NULL,
    engine_cc INT,
    daily_price NUMERIC(10, 2) NOT NULL CHECK (daily_price >= 0),
    color TEXT,
    mileage_km INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'rented', 'maintenance')),
    photos JSONB NOT NULL DEFAULT '[]'::jsonb,
    videos JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (park_id, plate_number)
);

CREATE INDEX idx_bikes_park ON bikes(park_id);
CREATE INDEX idx_bikes_park_status ON bikes(park_id, status);

-- ============ BOOKINGS ============
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
    client_telegram_id BIGINT NOT NULL,
    bike_id INT NOT NULL REFERENCES bikes(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_price NUMERIC(10, 2) NOT NULL CHECK (total_price >= 0),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date >= start_date)
);

CREATE INDEX idx_bookings_park_client ON bookings(park_id, client_telegram_id);
CREATE INDEX idx_bookings_bike_dates ON bookings(bike_id, start_date, end_date);
CREATE INDEX idx_bookings_status ON bookings(status);

-- ============ EXPENSES ============
CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
    bike_id INT NOT NULL REFERENCES bikes(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    description TEXT,
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expenses_park_bike ON expenses(park_id, bike_id);
CREATE INDEX idx_expenses_date ON expenses(park_id, expense_date);

-- ============ MAP POINTS ============
CREATE TABLE map_points (
    id SERIAL PRIMARY KEY,
    park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    lat NUMERIC(10, 7) NOT NULL,
    lng NUMERIC(10, 7) NOT NULL,
    type TEXT NOT NULL DEFAULT 'guide'
        CHECK (type IN ('guide', 'pickup', 'dropoff')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_map_points_park ON map_points(park_id);

-- ============ PAYMENT REQUESTS ============
CREATE TABLE payment_requests (
    id SERIAL PRIMARY KEY,
    park_id INT NOT NULL REFERENCES parks(id) ON DELETE CASCADE,
    amount_usd NUMERIC(10, 2) NOT NULL CHECK (amount_usd >= 0),
    months INT NOT NULL CHECK (months IN (1, 3)),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'rejected')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);

CREATE INDEX idx_payment_requests_status ON payment_requests(status);
CREATE INDEX idx_payment_requests_park ON payment_requests(park_id);