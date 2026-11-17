
ALTER TABLE parks ADD COLUMN IF NOT EXISTS bikes_limit INT NOT NULL DEFAULT 10;
UPDATE parks SET bikes_limit = CASE
  WHEN subscription_plan = 'pro' THEN 20
  ELSE 10
END;
