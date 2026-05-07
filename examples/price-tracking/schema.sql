CREATE TABLE IF NOT EXISTS products (
    asin TEXT PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_points (
    id UUID PRIMARY KEY,
    asin TEXT NOT NULL REFERENCES products(asin) ON DELETE CASCADE,
    price NUMERIC(12, 2) NOT NULL,
    source TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_points_asin_observed ON price_points (asin, observed_at);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    asin TEXT NOT NULL REFERENCES products(asin) ON DELETE CASCADE,
    threshold_price NUMERIC(12, 2) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_asin_threshold ON subscriptions (asin, threshold_price) WHERE active = true;

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    asin TEXT NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subscription_id, asin, price)
);
CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications (user_id, created_at DESC);

INSERT INTO products (asin, title) VALUES ('B000DEMO', 'Demo headphones') ON CONFLICT DO NOTHING;
INSERT INTO price_points (id, asin, price, source, observed_at) VALUES
    ('00000000-0000-0000-0000-000000000001', 'B000DEMO', 129.99, 'seed', now() - interval '2 days'),
    ('00000000-0000-0000-0000-000000000002', 'B000DEMO', 119.99, 'seed', now() - interval '1 day')
ON CONFLICT DO NOTHING;
